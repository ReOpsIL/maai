# MAAI: Multi-Agent Coding CLI Application

## Overview

MAAI is a command-line application that leverages a multi-agent system to take a simple software idea from conception through research, analysis, design, implementation, testing, and documentation. Each agent specializes in a specific part of the software development lifecycle, collaborating within a project structure to build and refine the final product.

## Core Idea

The application aims to automate and streamline the process of turning high-level software ideas into functional, tested, and documented code. Users interact with the system via command-line flags (e.g., `--idea`, `--build`, `--research`, `--update`, `--generate-doc`) to manage the development lifecycle and trigger specific agents or the full build pipeline. All generated artifacts (documents, code, tests) are stored within a structured directory under a main `projects/` folder, specific to each project idea. The build process automatically handles dependency extraction, virtual environment creation (in `.venv/`), and installation.

## Agent Roles

The application consists of the following agents, most utilizing a Generative AI model (like Google Gemini, configured via `config.yaml` and requiring a `GEMINI_API_KEY` environment variable) for their core functionality:

1.  **Innovator Agent:**
    *   **Input:** A simple user-provided idea text or modification instructions.
    *   **Process:** Expands an idea into `idea.md` or updates an existing `idea.md` based on instructions.
    *   **Output:** `docs/idea.md`

2.  **Research Agent:**
    *   **Input:** The `idea.md` document.
    *   **Process:** Uses the LLM's knowledge to find and summarize relevant technical resources.
    *   **Output:** `docs/research_summary.md`

3.  **Market Analyst Agent:**
    *   **Input:** The `idea.md` document or modification instructions.
    *   **Process:** Analyzes `idea.md` for business potential or updates an existing `market_analysis.md`.
    *   **Output:** `docs/market_analysis.md`

4.  **Architect Agent:**
    *   **Input:** The `idea.md` document or modification instructions + existing `impl.md`.
    *   **Process:** Designs `impl.md` based on `idea.md` or updates an existing `impl.md` based on instructions.
    *   **Output:** `docs/impl.md`

5.  **Coder Agent:**
    *   **Input:** The `impl.md` document, optional feedback, or modification instructions + existing code.
    *   **Process:** Generates Python code (`src/`) based on `impl.md` or updates existing code based on instructions and the latest `impl.md`.
    *   **Output:** Python source files in `src/`.

6.  **Reviewer Agent:**
    *   **Input:** Python source code (`src/`) and the implementation plan (`impl.md`).
    *   **Process:** Uses the LLM to review the generated code for adherence to the plan, correctness, best practices, clarity, and basic security considerations. Provides feedback for the Coder Agent if issues are found.
    *   **Output:** Review feedback (used internally in build).

7.  **Tester Agent:**
    *   **Input:** `impl.md`, source code (`src/`), or modification instructions + existing tests.
    *   **Process:** Generates `pytest` tests (`tests/`) based on `impl.md`/code or updates existing tests based on instructions and latest `impl.md`/code. Test execution happens within the `--build` command (using the project's `.venv/`).
    *   **Output:** Python test files in `tests/`.

8.  **Documenter Agent:**
    *   **Input:** `idea.md`, `impl.md`, source code (`src/`), and a specified document type.
    *   **Process:** Generates specific documentation files (e.g., SRS, API, User Manual, SDD, Project Overview).
    *   **Output:** Specific Markdown files in `docs/`.

## Command-Line Interface

The application is controlled via `python src/orchestrator.py` followed by flags. Most actions require specifying a project using `--project <name>`.

**Core Commands:**

*   **List Projects:**
    *   `python src/orchestrator.py --list`
    *   Lists all project directories within the `projects/` folder.

*   **Create New Idea:**
    *   `python src/orchestrator.py --idea "Your concise idea text here"`
    *   Generates a project name, creates structure, runs **Innovator Agent** to create `docs/idea.md`.
    *   `python src/orchestrator.py --idea "Your idea" --project specific-project-name`
    *   Uses specified name, creates structure, runs **Innovator Agent** to create `docs/idea.md`.

*   **Perform Research:**
    *   `python src/orchestrator.py --research --project <name>`
    *   Runs **Research Agent** using `docs/idea.md` -> `docs/research_summary.md`.

*   **Analyze Idea (Market):**
    *   `python src/orchestrator.py --analyze-idea --project <name>`
    *   Runs **Market Analyst Agent** using `docs/idea.md` -> `docs/market_analysis.md`.

*   **Full Build Pipeline:**
    *   `python src/orchestrator.py --build --project <name>`
    *   Executes the main development pipeline:
        1.  **Architect** (creates `impl.md`)
        2.  **Dependency Setup:** (creates `requirements.txt`, `./.venv/`, installs deps)
        3.  **Coder** (creates `src/*.py`)
        4.  **Reviewer/Coder Loop** (refines code using LLM review feedback)
        5.  **Tester** (creates `tests/test_*.py` & runs `pytest` in `./.venv/`)
        6.  **Documenter** (creates `docs/project_docs.md`)
    *   Stops on major errors.

**Update Commands (for iterative refinement):**

*   **Update Idea:**
    *   `python src/orchestrator.py --update-idea "Modification instructions" --project <name>`
    *   Runs **Innovator Agent** to refine `docs/idea.md`.

*   **Update Implementation, Code, Tests, and Docs:**
    *   `python src/orchestrator.py --update "Modification instructions" --project <name>`
    *   Runs a sequence to refine the project based on instructions:
        1.  **Architect** (updates `impl.md`)
        2.  **Coder** (updates `src/*.py` based on new `impl.md` and instructions)
        3.  **Tester** (updates `tests/*.py` based on new `impl.md`, new code, and instructions)
        4.  **Documenter** (regenerates `docs/project_docs.md` based on all updated artifacts)
    *   Note: This does *not* automatically run the Reviewer or execute tests. Run `--build` afterwards for full validation.

*   **Update Market Analysis:** (Kept separate as it's analysis, not core implementation)
    *   `python src/orchestrator.py --update-analysis "Modification instructions" --project <name>`
    *   Runs **Market Analyst Agent** to refine `docs/market_analysis.md`.

**Documentation Generation:**

*   **Generate Specific Document:**
    *   `python src/orchestrator.py --generate-doc --doc-type <type> --project <name>`
    *   Runs **Documenter Agent** to generate a specific document.
    *   Supported `<type>` values: `api`, `project_overview`, `sdd`, `srs`, `user_manual`.
    *   Output examples: `docs/api.md`, `docs/project_docs.md`, `docs/sdd.md`, etc.

**Project Management Commands:**

*   **Reset Project:**
    *   `python src/orchestrator.py --reset --project <name>`
    *   Deletes generated docs (`impl.md`, `requirements.txt`, `*.md` from Documenter/MarketAnalyst/ResearchAgent). Keeps `idea.md`, `src/`, `tests/`, `.venv/`.

*   **Scratch Project:**
    *   `python src/orchestrator.py --scratch --project <name>`
    *   Performs `reset` and removes `src/`, `tests/`, `.venv/`. Keeps only `docs/idea.md`.

## How to Use (Manual Flow Example)

1.  **Setup:**
    *   Ensure Python 3.9+ is installed.
    *   Install MAAI's dependencies: `pip install -r requirements.txt`.
    *   Create `.env` file with `GEMINI_API_KEY=YOUR_API_KEY_HERE`.
    *   Review `config.yaml`.

2.  **Create Idea:**
    *   `python src/orchestrator.py --idea "A CLI tool for basic image format conversion (jpg, png, webp) using Pillow"`
    *   Creates `./projects/a-cli-tool-for-basic-image.../docs/idea.md`. Review it.

3.  **(Optional) Research/Analysis:**
    *   `python src/orchestrator.py --research --project a-cli-tool-for-basic-image...`
    *   `python src/orchestrator.py --analyze-idea --project a-cli-tool-for-basic-image...`

4.  **Build Initial Version:**
    *   `python src/orchestrator.py --build --project a-cli-tool-for-basic-image...`
    *   Monitors Architect, Dependency Setup, Coder, **AI Reviewer**/Code loop, Tester, Documenter steps.

5.  **Review Artifacts:** Check `impl.md`, `requirements.txt`, `src/`, `tests/`, `docs/project_docs.md`.

6.  **(Optional) Generate Specific Docs:**
    *   `python src/orchestrator.py --generate-doc --doc-type api --project a-cli-tool-for-basic-image...`

7.  **Iteratively Update:**
    *   `python src/orchestrator.py --update "Add support for resizing images with an optional --width and --height argument" --project a-cli-tool-for-basic-image...`
    *   Runs Architect -> Coder -> Tester -> Documenter updates.
    *   Review changes.

8.  **(Optional) Re-Build for Validation:**
    *   `python src/orchestrator.py --build --project a-cli-tool-for-basic-image...`
    *   Re-runs the full pipeline, including the **AI Reviewer** loop and test execution.

9.  **Clean Up:**
    *   `reset` or `scratch` as needed.

This provides a flexible workflow for generating, building, and iteratively refining software projects.