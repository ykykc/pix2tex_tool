# Development Plan

## Purpose

This document defines the staged development plan for the formula recognition web platform.

The project goal is to build a web platform similar to SimpleTex that supports image formula upload, Pix2Tex-based recognition, LaTeX output, MathML output, online preview, and future AI formula explanation and technical document generation.

## Execution Rule

Each development turn must complete only one clear task.

Before starting any implementation task:

- Confirm the task scope.
- Avoid mixing unrelated changes.
- Update or create the relevant design document when the task changes architecture, APIs, model integration, or user workflows.
- Add tests for the completed feature when code is implemented.
- Do not directly modify Pix2Tex or other third-party model source code.

## Phase 1: Project Planning and Documentation

Goal: establish the project foundation before writing application code.

Tasks:

- Create `AGENTS.md` with project rules and development principles.
- Create `docs/development_plan.md`.
- Create `docs/architecture.md` describing the system architecture.
- Create `docs/api_design.md` describing backend API contracts.
- Create `docs/pix2tex_integration.md` describing the model integration boundary.
- Create `docs/testing_strategy.md` describing test categories and commands.
- Decide the initial frontend framework and backend framework.
- Decide the initial local development and deployment approach.

Exit criteria:

- Core documentation exists.
- The main modules and responsibilities are defined.
- The first implementation task can be started without changing the project direction.

## Phase 2: Project Skeleton

Goal: create a clean, modular project structure without implementing business logic too early.

Tasks:

- Create the frontend project skeleton.
- Create the backend project skeleton.
- Add base configuration files.
- Add basic README setup instructions.
- Add `.gitignore`.
- Add placeholder module directories for upload, recognition, conversion, preview, and future AI features.
- Add initial test directories.

Exit criteria:

- Frontend and backend can be installed independently.
- The repository structure matches the architecture documents.
- Empty or minimal test commands are available.

## Phase 3: Image Upload Foundation

Goal: support safe formula image upload before model recognition.

Tasks:

- Design the image upload API contract.
- Implement backend image upload validation.
- Support common image formats such as PNG, JPG, and JPEG.
- Add file size validation.
- Add image parsing validation.
- Add frontend upload component.
- Add frontend image preview.
- Add tests for valid upload, invalid type, oversized file, empty file, and unreadable image.

Exit criteria:

- Users can upload a formula image.
- Invalid files are rejected with clear errors.
- Upload behavior is covered by tests.

## Phase 4: Pix2Tex Recognition Integration

Goal: integrate Pix2Tex through a project-owned adapter.

Tasks:

- Design the recognition module interface.
- Create the Pix2Tex adapter boundary.
- Add image preprocessing before inference.
- Load and call Pix2Tex without modifying third-party source code.
- Return normalized recognition results.
- Add recognition error handling.
- Add tests for adapter success, model unavailable, invalid input, and inference failure.

Exit criteria:

- The backend can return LaTeX from an uploaded formula image.
- Pix2Tex is isolated behind a project-owned module.
- Recognition behavior has focused tests.

## Phase 5: LaTeX Result Display

Goal: display and manage recognized LaTeX in the web interface.

Tasks:

- Add the API response field for LaTeX output.
- Add frontend result display.
- Add copy-to-clipboard behavior.
- Add basic LaTeX validation or warning display.
- Add tests for result rendering and copy behavior.

Exit criteria:

- Users can see and copy recognized LaTeX.
- Empty or failed recognition results are handled clearly.

## Phase 6: MathML Conversion

Goal: convert recognized LaTeX into MathML.

Tasks:

- Design the conversion module interface.
- Choose the LaTeX-to-MathML conversion approach.
- Implement backend conversion flow.
- Add MathML to the recognition API response.
- Add frontend MathML display.
- Add copy-to-clipboard behavior for MathML.
- Add tests for successful conversion and conversion failure.

Exit criteria:

- Users can see and copy MathML output.
- Conversion failures do not break LaTeX output.

## Phase 7: Online Formula Preview

Goal: provide a reliable online preview for recognized formulas.

Tasks:

- Choose KaTeX or MathJax for frontend rendering.
- Add formula preview component.
- Handle invalid LaTeX gracefully.
- Add loading, success, and error states.
- Add responsive layout checks.
- Add frontend tests for preview rendering and error display.

Exit criteria:

- Users can preview recognized formulas in the browser.
- Invalid formulas produce clear preview errors.

## Phase 8: Stability and User Experience

Goal: make the core workflow reliable and comfortable to use.

Tasks:

- Add structured backend error responses.
- Add frontend error messages.
- Add loading and retry states.
- Add backend request timing logs.
- Add model inference timing logs.
- Add basic rate or concurrency safeguards for local use.
- Add end-to-end tests for the full upload-to-preview workflow.

Exit criteria:

- The main workflow is testable end to end.
- Failures are visible and understandable.
- Logs provide enough information for debugging.

## Phase 9: AI Formula Explanation

Goal: extend the platform with AI-based formula explanation after the core recognition workflow is stable.

Tasks:

- Design the AI explanation API.
- Define prompt inputs and structured output format.
- Add explanation generation for recognized formulas.
- Add frontend explanation panel.
- Add tests for request validation, successful explanation, and failed AI response.

Exit criteria:

- Users can request an explanation for a recognized formula.
- AI output is structured and displayed consistently.

## Phase 10: Technical Document Generation

Goal: support generating technical documentation from recognized formulas and explanations.

Tasks:

- Design document generation workflows.
- Define supported output formats.
- Generate Markdown technical notes.
- Consider future DOCX or PDF export.
- Add frontend export controls.
- Add tests for generated document structure.

Exit criteria:

- Users can generate a basic technical document from formula recognition results.
- The generated document format is predictable and testable.

## Suggested Next Task

The next single task should be:

Create `docs/architecture.md` describing the system overall architecture, module boundaries, and deployment shape.

