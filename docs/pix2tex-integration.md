# Pix2Tex 与 Backend 集成设计

日期：2026-09-08。状态：Phase 3.1 设计方案，尚未实现。

## 1. 范围与结论

推荐采用**同机独立 Pix2Tex 推理服务 + Backend 项目自有 Pix2TexAdapter**。推理服务使用现有独立 AI 环境，Backend 通过内部 HTTP 调用它，对外保持当前识别接口及响应结构。

该选择基于当前仓库已建立独立环境，以及本地 Pix2Tex 存在进程级副作用；并非基于已完成的性能对比。代价是需要管理两个进程、内部协议和服务不可用状态。

本次仅新增此设计文档。后续实现分开执行，不在本次修改代码、安装依赖、启动推理服务或接入 API。MathML、前端、AI 解释、数据库均不属于此次集成范围。

## 2. 当前仓库分析

### 2.1 Backend 调用链

```text
POST /api/v1/recognize
  -> routes/recognize.py
  -> RecognitionService.recognize(UploadFile)
  -> _validate_upload(file, contents)
  -> MockRecognitionAdapter.recognize(UploadedImageRequest)
  -> RecognitionResponse
```

| 当前文件 | 实际职责与接入影响 |
| --- | --- |
| `backend/app/recognition/__init__.py` | 识别模块包入口，目前没有模型生命周期管理。 |
| `backend/app/recognition/adapter.py` | 仅定义 `MockRecognitionAdapter` 和固定 `MOCK_LATEX`；同步 `recognize(image) -> str`，没有通用接口。 |
| `backend/app/services/recognition_service.py` | 读取全部上传字节后校验类型、空文件、5 MiB 上限和 Pillow 可读性；直接同步调用 adapter。构造参数绑定 Mock 类型，文件末尾创建全局 service 实例。 |
| `backend/app/schemas/recognition.py` | `UploadedImageRequest` 只有文件名、MIME、字节数、宽高，**不包含图片内容**。响应只包含 LaTeX 与秒单位处理时间。 |
| `backend/app/core/config.py` | 冻结 dataclass，保存固定默认值；当前没有环境变量加载逻辑或识别引擎选项。 |
| `backend/app/main.py` | 创建应用、注册路由与 `ApiError` 处理；目前无模型或客户端启动/关闭钩子。 |
| `backend/app/api/routes/recognize.py` | 薄路由，委托 service；不应加入模型初始化、HTTP 客户端或预处理逻辑。 |
| `backend/tests/test_recognize.py` | 有 Mock 成功及类型、空文件、超限、不可读失败测试，未覆盖真实推理、生命周期、并发或超时。 |

关键缺口：仅把 Mock 类替换成 Pix2Tex 类不能完成接入。需要保留实际图片字节，并建立异步调用、生命周期、错误转换和可注入的 adapter 边界。

当前上传实现还未核验实际解码格式与声明 MIME 是否匹配，也未实现文档中的尺寸和动画限制。5 MiB 校验发生在完整读取之后。上述问题应在后续明确的上传校验任务中处理，不能描述成已具备的保护。

### 2.2 独立推理现状

本次只读核验的 `ai_runtime/.venv` 软件版本：

| 项目 | 当前值 |
| --- | --- |
| Python | 3.11.6 |
| pix2tex | 0.1.4 |
| torch | 2.14.0+cpu |
| torchvision | 0.29.0+cpu |
| Pillow | 12.3.0 |

这些是本地包元数据的观测值，不代表已验证的通用依赖锁定组合。Backend 的声明是 Python >=3.9，本次未重新探测其运行解释器，不假设两者共享环境。

现有 `ai_runtime/scripts/run_pix2tex_once.py` 接受路径、读取图片、每次创建一个 `LatexOCR()` 并输出 LaTeX。它适用于单次验证，不应由每个 Backend 请求启动一次。四类测试图片与预期文档已经存在，但不代表四类真实识别全部通过。本次未重跑模型或性能测试。

本地第三方源码的只读检查发现：

- `pix2tex/cli.py` 的 `LatexOCR.__init__` 默认 `no_cuda=True`，会调整根日志级别及环境变量；缺少权重时可能触发下载。
- 初始化和识别均使用 `pix2tex/utils/utils.py` 的 `in_model_path()`，期间调用 `os.chdir()`，影响整个进程。
- 模型实例保存 `last_pic`，并非无状态函数；不能假设共享实例可并发调用。

这些行为是选择进程隔离的具体依据。仅将调用放在线程中或给模型加锁，不能隔离它对 Backend 其他线程的工作目录和日志影响。

### 2.3 与既有文档的关系

- [architecture.md](architecture.md) 原先倾向 MVP 进程内接入，并预留独立服务。本设计基于上述本地证据，推荐提前使用独立服务；这是待实施的新决策，原文档本次保持原样。
- [api-design.md](api-design.md) 规划 `/api/v1/formulas/recognize`、MathML、meta 与模型状态接口；当前实际只有 `/api/v1/recognize` 的简化识别响应。本次集成设计以现有实现为兼容基线，不顺带迁移公共 API。
- [development_plan.md](development_plan.md) 的原始阶段编号与当前任务编号不同。这里的 Phase 3.1 指本次集成设计，对应原计划的模型集成设计内容，不表示原计划其他任务已完成。文件名按当前任务使用 `pix2tex-integration.md`。

## 3. 两种接入方式比较

| 维度 | Backend 进程内直接调用 | Pix2Tex 独立推理服务 |
| --- | --- | --- |
| 调用方式 | 本地 adapter 调用 `LatexOCR` | 后端 adapter 发送图片字节，推理进程调用模型 |
| 依赖环境 | 后端需安装兼容的 Pix2Tex/PyTorch 依赖；不能靠导入另一个 venv 解决 | 保留 AI venv，Backend 仅增加内部 HTTP 客户端运行依赖 |
| 启动部署 | 一个服务，初期代码较少 | 两个进程，需要启动顺序、探活和故障处理 |
| 进程副作用 | 模型影响后端工作目录、日志和内存 | 影响限制在 AI 进程；AI 进程仍需使用绝对路径和串行推理 |
| 异步请求 | 必须把同步推理移出事件循环 | Backend 异步等待 HTTP；AI 端也必须移出事件循环执行推理 |
| 模型复用 | 每个 Backend worker 一份，增加 worker 会重复加载 | 一个 AI worker 常驻一份，可独立于 Backend worker 数量 |
| 超时恢复 | 线程等待超时无法可靠停止底层推理；重启会影响 Backend | HTTP 超时也不会停止推理，但可以单独重启 AI 进程 |
| 传输成本 | 无额外 HTTP 编码及图片传输 | 有本机 HTTP 和字节复制成本，实际耗时待测 |
| 测试与扩展 | 接口可 Mock，但真实模型依赖进入 Backend 环境 | 后端契约测试与模型测试分离，后续可迁移推理主机 |

选择独立服务作为当前实施目标。进程内方案保留为备选设计，不同时实现两套真实 adapter。MVP 仅需同机服务，不引入 Redis、消息队列、容器集群或批处理系统。

## 4. 推荐架构与职责

```text
现有客户端
  -> Backend /api/v1/recognize
  -> RecognitionService：上传校验、计时、响应、错误映射
  -> Pix2TexAdapter：内部 HTTP、超时、响应校验
       |
       | 同机回环 HTTP，传图片内容，不传本地路径
       v
独立 AI 服务：容量限制、内部请求校验、就绪状态
  -> LatexOCRRunner：解码、预处理、模型加载/复用、推理、结果检查
  -> pix2tex.cli.LatexOCR
       |
       v
LaTeX -> Backend 现有响应
```

`Pix2TexAdapter` 是 Backend 侧的远程适配器，不直接导入 `pix2tex`。`LatexOCRRunner` 是 AI 侧自有封装，独占第三方模型调用。两边不互相导入源码；Backend 不导入独立 CLI 脚本，也不读取 AI venv 的 site-packages。

未来 MathML 转换仍由 Backend 的独立转换模块接收 LaTeX；AI 解释接收 LaTeX 及可选 MathML，不进入本次识别 adapter。

## 5. Adapter 接口设计

以下是接口契约说明，不是实现代码。Backend 定义 `RecognitionAdapter` 协议，Mock 与 Pix2TexAdapter 均实现它。

| 方法 | 输入 | 输出与语义 |
| --- | --- | --- |
| `async start()` | 无 | 建立可复用客户端资源；Mock 无操作；不在 Backend 加载模型。 |
| `async recognize(image)` | `RecognitionInput` | 返回非空 LaTeX 字符串；发生故障时抛项目自有识别异常。 |
| `async aclose()` | 无 | 关闭本适配器拥有的客户端，支持重复关闭；不终止独立部署的 AI 服务。 |

内部 `RecognitionInput` 使用项目自有 Pydantic 模型：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `content` | bytes | 经过上传校验的真实图片内容，非空，不进入日志或公开 JSON |
| `metadata` | `UploadedImageRequest` | 复用现有文件名、MIME、大小、宽高信息；不能替代内容 |

service 保存读取所得 `contents` 并构造输入；后续实例注入改用协议类型。由于 HTTP 调用是异步，service 调用也改为等待 adapter，Mock 同步方法需在同一接口迁移任务中对齐。返回值维持字符串，现阶段不添加引擎信息、置信度或 MathML 字段。

`Pix2TexAdapter` 构造时接收客户端、固定基础 URL 和超时配置，便于使用假 HTTP 传输测试。识别异常独立于 FastAPI；由 service 映射成现有 `ApiError`，route 不处理模型异常。

## 6. 内部协议草案

仅作为未来实现契约；当前不创建这些端点。拟绑定 `127.0.0.1:8001`，端口可配置。

| 方法与路径 | 请求 | 成功响应 |
| --- | --- | --- |
| `GET /internal/v1/ready` | 无参数 | `{"status":"ready"}`；加载中或故障时返回 503 和对应状态 |
| `POST /internal/v1/recognize` | multipart，唯一 `file`，携带图片字节与已核验 MIME | 200，`{"latex":"x^{2}+2x+1=0"}` |

失败响应统一为 `{"error":{"code":"MODEL_UNAVAILABLE","message":"Model is unavailable."}}`，状态码遵循下表。它是内部协议，不使用公共识别响应中的计时字段。Backend 验证 JSON 类型及非空字符串结果，并自行组装公共响应。

只允许服务配置指定上游地址，不接受用户提供 URL、权重路径、设备或服务器文件路径。首版本只监听回环地址，不设置公网暴露；跨主机部署前须单独设计认证和加密连接。服务就绪检查用于启动诊断，不在每次推理前额外探活。

## 7. 数据流、生命周期与资源管理

1. Backend 在有限读取策略下校验上传，构造包含字节的内部输入；不得永久保存用户图片。
2. service 启动单次计时，通过异步 adapter 发送内部请求，保持原有公共路径不变。
3. AI 服务先检查容量与文件大小、实际格式、尺寸和可读性，不能信任上游发送的元数据。目标限制沿用 API 文档：PNG/JPEG/WEBP，5 MiB，宽高各 16 至 4096，拒绝动画。
4. `LatexOCRRunner` 在内存中完整解码图片，处理 EXIF 方向，透明图片合成白底，再转 RGB。方向变换后重新检查尺寸。首版不自行二值化、锐化或切割多行公式；缩放和模型专用预处理交给 Pix2Tex。
5. 模型仅在 AI 服务启动时初始化一次。启动前检查本地配置、tokenizer、权重及 resizer 文件；缺失则保持不可用，不在用户请求期间自动下载。资源路径使用绝对路径。
6. 启动状态从 loading 转 ready；失败时保存受控日志并保持 unavailable。Backend 启动不依赖 AI 必须就绪，原有 health 仍表示 Backend 存活。
7. 串行执行模型推理，输出仅去除首尾空白。空值、非字符串视为失败；不删除反斜杠、重写公式、推断置信度或把固定 Mock 输出当真实结果。
8. 在成功和异常清理路径均关闭图片/缓冲区，清除模型 `last_pic` 等请求级图片引用。通过自有 wrapper 清理，不修改第三方源码；不能承诺内存字节立即物理擦除。
9. Backend 验证结果、返回当前 `success/data/error` 结构。`data.processing_time` 继续以秒计，从 service 读取上传开始直到拿到结果，包含传输和校验，不含独立服务启动时间。
10. Backend 生命周期负责创建 adapter/service 并关闭客户端，避免导入模块时创建重型对象。AI 服务关闭时停止接单，等待有限时间后由部署管理器回收进程。

## 8. 并发与超时

初始配置采用一个 AI 进程、一个模型实例、同时最多一个推理任务、不排队。忙碌时立即返回 503 `MODEL_BUSY`，无自动重试，避免重传后重复推理。即使将来 Backend 使用多个 worker，AI 服务也必须独立执行这个容量限制。

同步模型工作放入 AI 进程的专用单工作线程，HTTP 事件循环负责探活和快速拒绝忙碌请求。调用普通同步函数并不会因为上层是 async 就自动移出事件循环；实现时应显式调度。线程池的框架行为可参考 [Starlette 官方文档](https://starlette.dev/threadpool/)。

初始超时沿用 API 文档的量级：Backend 连接上游 2 秒，从发起推理请求到读完响应的总等待上限 30 秒；应同时设置连接/读写超时及总截止时间，不能把单次读取超时当总预算。AI 端单任务执行预算也暂定 30 秒，具体值需用 CPU 样例实测修订。模型启动另设暂定 120 秒预算，不占用户请求预算。

HTTP 断开、异步取消或线程等待超时都不等于停止 PyTorch 推理。超时后应继续保持模型占用，直到工作线程确实结束；禁止提前释放并发许可并接入下一张图片。超时后的结果丢弃，待结束后才清理图片。持续卡住则停止就绪并由独立进程管理器重启 AI 服务；进程内线程方案不能承诺严格的算力中断。如果后续要求到时强制停止单个任务，应另行设计受监管的模型子进程。

## 9. 错误映射与配置

| 情况 | 公开 HTTP 状态 | 公开错误码 |
| --- | --- | --- |
| 上传为空、超限、不支持、损坏 | 保留现有 400/413/415/422 | 保留 `UPLOAD_*`；新增尺寸/动画校验须单独更新契约 |
| AI 不可达、尚未加载、权重不可用 | 503 | `MODEL_UNAVAILABLE` |
| 推理容量已满 | 503 | `MODEL_BUSY`，本设计新增，未来接入时同步 API 文档 |
| 连接超时 | 503 | `MODEL_UNAVAILABLE` |
| 已发送请求后超出总等待时间，或 AI 报告执行超时 | 504 | `RECOGNITION_TIMEOUT` |
| 模型执行异常、空 LaTeX | 500 | `RECOGNITION_FAILED` |
| 上游非 JSON、字段错误、未知错误状态 | 500 | `RECOGNITION_FAILED`，记录内部诊断，不转发原始正文 |

异常信息不得包含第三方堆栈、绝对路径或上传内容。配置真实引擎时不得因失败静默回退到 Mock；Mock 仅用于明确选择的开发和测试模式。

| 建议配置 | 所属进程 | 初始值或规则 |
| --- | --- | --- |
| `RECOGNITION_ENGINE` | Backend | `mock` 或 `pix2tex`；默认 mock，显式开启真实识别 |
| `PIX2TEX_SERVICE_URL` | Backend | `http://127.0.0.1:8001` |
| `PIX2TEX_CONNECT_TIMEOUT_SECONDS` | Backend | 2 |
| `PIX2TEX_REQUEST_TIMEOUT_SECONDS` | Backend | 30，总等待上限 |
| `PIX2TEX_DEVICE` | AI | cpu；以后再验证其他设备 |
| `PIX2TEX_MODEL_DIR` | AI | 包含所需配置与资源的绝对位置；后续映射到第三方支持的参数 |
| `PIX2TEX_MAX_CONCURRENCY` | AI | MVP 固定校验为 1 |
| `PIX2TEX_INFERENCE_TIMEOUT_SECONDS` | AI | 30，不能等同于强制终止 |
| `PIX2TEX_STARTUP_TIMEOUT_SECONDS` | AI | 120，待实测 |

这些配置尚不存在。后续需要明确增加环境变量读取及类型/范围校验，不能只在当前 dataclass 中声明名称就认为环境变量已生效。

## 10. 后续目录建议

以下路径均为规划，本次不创建：

```text
backend/app/recognition/
  adapter.py                  通用协议及 Mock，尽量保留已有导入兼容性
  types.py                    RecognitionInput
  errors.py                   项目自有识别异常
  pix2tex_adapter.py          内部 HTTP 适配器

ai_runtime/inference/
  app.py                      独立服务启动、内部请求与就绪状态
  schemas.py                  内部请求/响应契约
  config.py                   推理环境配置
  runner.py                   LatexOCRRunner 与模型生命周期

backend/tests/test_pix2tex_adapter.py
ai_runtime/tests/test_inference_runner.py
ai_runtime/tests/test_inference_service.py
```

`ai_runtime/scripts/` 保留人工单图验证用途，`samples/test_cases/` 保留质量样例。后续独立环境依赖管理应记录验证过的完整版本组合、CPU 构建来源、模型来源和校验值；本地安装快照不直接当跨机器锁文件使用。权重与虚拟环境继续忽略，不提交 Git。

## 11. 分任务实施与验收

每次只执行下列一个明确任务，不把方案确认视为全部实现授权：

1. **Backend 识别契约整理**：引入图片字节输入、异步协议与可注入 Mock；只跑现有 Mock 闭环，验证公共响应不变。
2. **独立模型 runner**：实现一次加载、多次串行推理、预处理、错误及图片引用清理，尚不创建内部服务。
3. **独立推理服务**：实现内部协议、就绪状态、容量限制与超时状态管理，在 AI 环境验证，Backend 继续 Mock。
4. **Backend 远程 adapter**：实现 HTTP 通信和异常映射，用假 HTTP 传输测试，尚不切换公开请求到真实模型。
5. **生命周期与显式切换**：接入配置和依赖注入，保留现有 `/api/v1/recognize`；安排实际环境端到端验证。

实施前或相应任务中补齐上传边界校验；凡改变公共校验行为或增加错误码，都同步契约与测试。后续任务应更新总体架构中已过时的部署建议及阶段状态。

验收测试覆盖：

- Mock 回归无需安装 Pix2Tex、联网或加载权重；原有成功与上传失败测试保持有效。
- runner 假模型测试覆盖仅初始化一次、解码失败、透明/方向处理、初始化失败、执行失败、空结果和清理。
- adapter 假 HTTP 测试覆盖字节传输、合法输出、不可达、忙碌、超时、非 JSON、缺字段、未知错误和客户端关闭。
- 并发测试验证第二个任务快速失败、探活仍响应、超时后旧任务未完成前不会重新接单、图片不会跨请求复用。
- 真实模型测试显式启用，使用四类现有图片，逐项记录实际 LaTeX、冷启动/热推理耗时和渲染比较结果；矩阵、多行作为探索性能力，不预先承诺正确率。
- 停止 AI 服务时 Backend health 仍可响应，识别返回明确不可用错误，不返回 Mock 假成功。

## 12. 参考与验证边界

- 仓库依据：`backend/app/recognition/adapter.py`、`services/recognition_service.py`、`schemas/recognition.py`、`core/config.py`、`main.py`、Backend 测试及现有三份项目设计文档。
- 本地模型行为依据：当前 AI venv 中 `pix2tex/cli.py` 与 `pix2tex/utils/utils.py` 的只读检查。副作用结论限定于本次检查的安装版本。
- [Pix2Tex 官方 README](https://github.com/lukas-blecher/LaTeX-OCR/blob/main/README.md?plain=1) 说明模型使用入口及权重自动下载行为；项目集成通过包装层处理资源策略，不改第三方源码。
- 本次完成静态结构、包元数据和文档一致性分析；未验证真实服务性能、并发安全实现或端到端接入。这些属于后续实现任务的验收内容。
