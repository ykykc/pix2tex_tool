import asyncio
import json
from email import policy
from email.parser import BytesParser

import httpx
import pytest

from app.core.config import Settings
from app.recognition.pix2tex_client import Pix2TexClient, Pix2TexClientError


SUCCESS = {"success": True, "latex": r"\frac{a}{b}", "model": "pix2tex", "processing_time": 0.25}


def call(handler, **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with Pix2TexClient("http://ai.test:8001/", client=http, **kwargs) as client:
                return await client.recognize(b"image bytes", filename="sample.png")
    return asyncio.run(run())


def test_request_format_and_response():
    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == "http://ai.test:8001/recognize"
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.read())
        parts = list(message.iter_parts())
        assert len(parts) == 1
        assert parts[0].get_param("name", header="content-disposition") == "image"
        assert parts[0].get_filename() == "sample.png"
        assert parts[0].get_content_type() == "image/png"
        assert parts[0].get_payload(decode=True) == b"image bytes"
        return httpx.Response(200, json=SUCCESS)
    result = call(handler)
    assert result.latex == SUCCESS["latex"]
    assert result.processing_time == 0.25
    assert result.model == "pix2tex"
    assert result.success is True


@pytest.mark.parametrize("status,code", [(503, "MODEL_BUSY"), (503, "MODEL_UNAVAILABLE"),
    (422, "UPLOAD_INVALID_IMAGE"), (500, "RECOGNITION_FAILED"), (504, "RECOGNITION_TIMEOUT")])
def test_known_service_errors(status, code):
    with pytest.raises(Pix2TexClientError) as error:
        call(lambda request: httpx.Response(status, json={"success": False, "error": {
            "code": code, "message": "private server path"}}))
    assert error.value.code == code
    assert "private" not in error.value.message


@pytest.mark.parametrize("body", [None, [], {}, {**SUCCESS, "success": 1},
    {**SUCCESS, "latex": ""}, {**SUCCESS, "latex": 123}, {**SUCCESS, "model": "other"},
    {**SUCCESS, "processing_time": -1}, {**SUCCESS, "processing_time": True},
    {**SUCCESS, "processing_time": "0.1"}, {"success": False, "error": []}])
def test_invalid_response_schema(body):
    with pytest.raises(Pix2TexClientError, match="unexpected response"):
        call(lambda request: httpx.Response(200, content=json.dumps(body)))


def test_invalid_json():
    with pytest.raises(Pix2TexClientError, match="invalid JSON"):
        call(lambda request: httpx.Response(502, text="<html>private details</html>"))


@pytest.mark.parametrize("status", [302, 404, 500])
def test_wrong_http_status_even_with_success_json(status):
    with pytest.raises(Pix2TexClientError):
        call(lambda request: httpx.Response(status, json=SUCCESS))


@pytest.mark.parametrize("exc,code", [(httpx.ConnectError, "MODEL_UNAVAILABLE"),
    (httpx.ConnectTimeout, "MODEL_UNAVAILABLE"), (httpx.ReadTimeout, "RECOGNITION_TIMEOUT")])
def test_transport_errors(exc, code):
    def handler(request):
        raise exc("private connection detail", request=request)
    with pytest.raises(Pix2TexClientError) as error:
        call(handler)
    assert error.value.code == code


def test_total_deadline():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=SUCCESS)
    with pytest.raises(Pix2TexClientError) as error:
        call(handler, timeout_seconds=0.01)
    assert error.value.code == "RECOGNITION_TIMEOUT"


def test_configuration_and_connection_ownership(monkeypatch):
    monkeypatch.setenv("PIX2TEX_SERVICE_URL", "http://configured.test:8002")
    config = Settings()
    monkeypatch.setattr("app.recognition.pix2tex_client.settings", config)
    async def run():
        seen = []
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: (seen.append(str(request.url)) or httpx.Response(200, json=SUCCESS)))) as http:
            async with Pix2TexClient(client=http) as client:
                await client.recognize(b"image")
            assert not http.is_closed
        assert seen == ["http://configured.test:8002/recognize"]
        owned = Pix2TexClient()
        await owned.aclose()
        await owned.aclose()
        assert owned._client.is_closed
    asyncio.run(run())


@pytest.mark.parametrize("url", ["", "file:///tmp/image", "http://user:pass@localhost", "http://localhost?x=1"])
def test_invalid_base_url(url):
    with pytest.raises(ValueError):
        Pix2TexClient(service_url=url)
