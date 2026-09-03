# AGENTS.md

## Project Goal

This project aims to build a web platform similar to SimpleTex for recognizing mathematical formulas from uploaded images and converting them into structured outputs.

Core capabilities:

- Upload images containing mathematical formulas.
- Recognize formulas using Pix2Tex.
- Output LaTeX.
- Output MathML.
- Provide online web preview of recognized formulas.
- Later support AI-powered formula explanation and technical document generation.

## Working Principles

- Design before coding. Before implementing a feature, first clarify the user flow, module boundaries, data flow, API shape, and testing approach.
- Develop modularly. Keep upload handling, recognition, format conversion, preview rendering, AI explanation, document generation, and persistence concerns separated.
- Preserve development documentation. Record important design decisions, architecture notes, API contracts, and testing instructions in project documents.
- Every feature needs tests. Add focused tests for each feature or behavioral change, including success paths, failure paths, and edge cases where appropriate.
- Do not directly modify third-party model source code. Treat Pix2Tex and other external model libraries as dependencies. Add wrappers, adapters, configuration, or extension layers inside this project instead.

## Expected Architecture Direction

Prefer a layered structure:

- Frontend: image upload, result display, LaTeX preview, MathML preview, user interactions.
- Backend API: request validation, file handling, recognition orchestration, response formatting.
- Recognition module: Pix2Tex integration through a project-owned wrapper.
- Conversion module: LaTeX to MathML conversion and related validation.
- Preview module: browser-side or server-assisted formula rendering.
- AI module: future formula explanation and technical document generation.
- Shared utilities: logging, error handling, configuration, file validation, and common types.
- Tests: unit tests for isolated logic, integration tests for API flows, and frontend tests for critical user interactions.

## Development Workflow

1. Confirm the feature goal and expected behavior.
2. Write or update a short design note when the change affects architecture, APIs, model integration, or user workflows.
3. Implement the smallest coherent module change.
4. Add or update tests for the changed behavior.
5. Run the relevant checks before considering the work complete.
6. Update documentation when behavior, setup, API contracts, or dependencies change.

## Model Integration Rules

- Integrate Pix2Tex through a local adapter or service layer.
- Keep model loading, inference configuration, preprocessing, and postprocessing encapsulated.
- Do not patch installed package files or vendored third-party source unless explicitly approved.
- If a third-party behavior must change, prefer configuration, subclassing, wrapper logic, or upstream-compatible extension points.
- Document model versions, runtime requirements, and hardware assumptions.

## Testing Expectations

For each implemented feature, include appropriate tests:

- Image upload validation: accepted formats, size limits, invalid files, empty uploads.
- Formula recognition wrapper: normal inference path, model failure path, timeout or unavailable model path.
- LaTeX output: formatting, escaping, empty or invalid recognition results.
- MathML output: conversion correctness and conversion failure handling.
- Web preview: rendering success, invalid formula handling, responsive layout basics.
- Future AI explanation and document generation: prompt inputs, structured outputs, error handling, and regression fixtures.

## Documentation Expectations

Keep development documents close to the codebase. Useful documents may include:

- Architecture overview.
- API design notes.
- Model integration notes.
- Setup and dependency instructions.
- Test strategy and test commands.
- Feature-specific design notes.

Documentation should be updated as the project evolves, especially when decisions affect future development.

## Code Quality Guidelines

- Follow existing project conventions once the codebase exists.
- Keep modules small and purpose-driven.
- Prefer explicit interfaces between frontend, backend, model, conversion, and AI layers.
- Handle errors clearly and return user-friendly messages at API boundaries.
- Avoid hidden global state where it would make testing or model lifecycle management difficult.
- Keep configuration in documented environment variables or configuration files.

## Out of Scope for Routine Changes

Unless explicitly requested, do not:

- Rewrite or directly edit Pix2Tex source code.
- Add unrelated frameworks or large dependencies.
- Refactor unrelated modules while implementing a focused feature.
- Store uploaded user images permanently without a documented retention decision.
- Implement AI explanation or document generation before the core recognition workflow is designed.

