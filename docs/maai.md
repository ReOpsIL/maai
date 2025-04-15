# MAAI: Multi-Agent Coding CLI Application

## Overview

MAAI is a command-line application that leverages a multi-agent system to assist in the software development lifecycle, taking a simple software idea through stages like research, analysis, design, implementation, review, testing updates, and documentation. Each agent specializes in a specific part of the lifecycle, collaborating within a project structure.

## Core Idea

The application aims to streamline the process of turning high-level software ideas into designed, coded, and documented components. Users interact with the system via command-line flags (e.g., `--idea`, `--build`, `--code`, `--review`, `--update`, `--generate-doc`) to manage the development lifecycle and trigger specific agents. All generated artifacts (documents, code, tests) are stored within a structured directory under a main `projects/` folder (configurable, defaults to `~/projects`), specific to each project idea. Dependency management and virtual environment setup might require manual steps.

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
    *   **Input:** The `idea.md` document.
    *   **Process:** Analyzes `idea.md` for business potential.
    *   **Output:** `docs/market_analysis.md`

4.  **Architect Agent:**
    *   **Input:** The `idea.md` document, or modification instructions (e.g., from user via `--update` or review feedback via `--code --fix`) + existing implementation plans (for context).
    *   **Process:** Designs implementation plans based on `idea.md` or updates existing plans based on instructions/feedback.
    *   **Output:** Implementation plan files (e.g., `docs/impl_*.md`, `docs/integ.md`, or `docs/impl.md`).

5.  **Coder Agent:**
    *   **Input:** Implementation plan documents (`docs/impl_*.md`, `docs/integ.md`, `docs/impl.md`), optional feedback (from `docs/review.md` via `--fix`), or general modification instructions + existing code.
    *   **Process:** Generates Python code (`src/`) based on implementation plans or updates existing code based on instructions/feedback and the latest plans.
    *   **Output:** Python source files in `src/`.

6.  **Reviewer Agent:**
    *   **Input:** Python source code (`src/`) and the implementation plan(s) (e.g., `docs/impl.md`).
    *   **Process:** Uses the LLM to review the generated code for adherence to the plan, correctness, best practices, etc.
    *   **Output:** Writes feedback to `docs/review.md` if issues are found.

7.  **Tester Agent:**
    *   **Input:** Implementation plan(s), source code (`src/`), or modification instructions + existing tests.
    *   **Process:** Generates `pytest` tests (`tests/`) based on plans/code or updates existing tests based on instructions and latest plans/code (primarily used during the `--update` command). Test *execution* is not automatically handled by these commands.
    *   **Output:** Python test files in `tests/`.

8.  **Documenter Agent:**
    *   **Input:** `idea.md`, implementation plan(s), source code (`src/`), and a specified document type.
    *   **Process:** Generates specific documentation files (e.g., SRS, API, User Manual, SDD, Project Overview).
    *   **Output:** Specific Markdown files in `docs/`.

## Command-Line Interface

The application is controlled via `python src/orchestrator.py` followed by flags. Most actions require specifying a project using `--project <name>`. The default projects directory is `~/projects` but can be changed with `--projects-dir <path>`.

**Core Commands:**

*   **List Projects:**
    *   `python src/orchestrator.py --list [--projects-dir <path>]`
    *   Lists all project directories within the specified projects folder.

*   **Create New Idea:**
    *   `python src/orchestrator.py --idea "Your concise idea text here" [--project <name>] [--projects-dir <path>]`
    *   Generates a project name if not provided, creates structure, runs **Innovator Agent** to create `docs/idea.md`.

*   **Perform Research:**
    *   `python src/orchestrator.py --research --project <name> [--projects-dir <path>]`
    *   Runs **Research Agent** using `docs/idea.md` -> `docs/research_summary.md`.

*   **Analyze Idea (Market):**
    *   `python src/orchestrator.py --analyze-idea --project <name> [--projects-dir <path>]`
    *   Runs **Market Analyst Agent** using `docs/idea.md` -> `docs/market_analysis.md`.

*   **Generate/Update Architecture:**
    *   `python src/orchestrator.py --build --project <name> [--projects-dir <path>]`
    *   Runs **Architect Agent** using `docs/idea.md` to generate or update implementation plan documents (e.g., `docs/impl_*.md`, `docs/integ.md`). This command *only* handles the architecture step.

*   **Generate/Update Code:**
    *   `python src/orchestrator.py --code --project <name> [--projects-dir <path>]`
    *   Runs **Coder Agent** using the implementation plan documents found in `docs/` to generate or update `src/*.py`. Requires plans to exist (run `--build` first).
    *   `python src/orchestrator.py --code --fix --project <name> [--projects-dir <path>]`
    *   Runs **Coder Agent** using implementation plans and feedback from `docs/review.md` to update `src/*.py`. Also notifies **Architect Agent** to check if architecture docs need updates based on the review feedback. Requires `review.md` to exist (run `--review` first).

*   **Review Code:**
    *   `python src/orchestrator.py --review --project <name> [--projects-dir <path>]`
    *   Runs **Reviewer Agent** using `src/*.py` and implementation plan(s) (e.g., `docs/impl.md`). Writes feedback to `docs/review.md` if issues are found. Requires code and plans to exist.

**Update Commands (for iterative refinement):**

*   **Update Idea:**
    *   `python src/orchestrator.py --update-idea "Modification instructions" --project <name> [--projects-dir <path>]`
    *   Runs **Innovator Agent** to refine `docs/idea.md`.

*   **General Update (Architecture, Code, Tests, Docs):**
    *   `python src/orchestrator.py --update "General modification instructions" --project <name> [--projects-dir <path>]`
    *   Runs a sequence to refine the project based on *general* instructions (distinct from the targeted review/fix cycle):
        1.  **Architect** (updates architecture docs)
        2.  **Coder** (updates `src/*.py`)
        3.  **Tester** (updates `tests/*.py`)
        4.  **Documenter** (regenerates `docs/project_overview.md`)
    *   Note: This uses the general modification text for all agents involved. Requires `impl.md` to exist.

**Documentation Generation:**

*   **Generate Specific Document:**
    *   `python src/orchestrator.py --generate-doc <type> --project <name> [--projects-dir <path>]`
    *   Runs **Documenter Agent** to generate a specific document.
    *   Supported `<type>` values: `api`, `project_overview`, `sdd`, `srs`, `user_manual`.
    *   Output examples: `docs/api.md`, `docs/project_overview.md`, `docs/sdd.md`, etc. (Note: `project_overview` might save as `project_docs.md` based on agent implementation).

**Project Management Commands:**

*   **Reset Project:**
    *   `python src/orchestrator.py --reset --project <name> [--projects-dir <path>]`
    *   Deletes generated docs (`impl.md`, `impl_*.md`, `integ.md`, `market_analysis.md`, `research_summary.md`, `review.md`, specific doc types like `api.md`, `project_docs.md`), and `requirements.txt`. Keeps `idea.md`, `src/`, `tests/`, `.venv/`.

*   **Scratch Project:**
    *   `python src/orchestrator.py --scratch --project <name> [--projects-dir <path>]`
    *   Performs `reset` and additionally removes `src/`, `tests/`, and the virtual environment (`.venv/`). Keeps only `docs/idea.md` and the basic project directory structure.

## How to Use (Example Workflow)

1.  **Setup:**
    *   Ensure Python 3.9+ is installed.
    *   Clone the MAAI repository.
    *   Install MAAI's own dependencies: `pip install -r requirements.txt` (in the MAAI repo root).
    *   Create a `.env` file in the MAAI repo root with `GEMINI_API_KEY=YOUR_API_KEY_HERE`.
    *   Review `config.yaml` if needed.

2.  **Create Idea:**
    *   `python src/orchestrator.py --idea "A CLI tool for basic image format conversion (jpg, png, webp) using Pillow"`
    *   This creates a project directory (e.g., `~/projects/a-cli-tool-for-basic-image.../`) and `docs/idea.md`. Review `idea.md`. Let's call the project `image-converter`.

3.  **(Optional) Research/Analysis:**
    *   `python src/orchestrator.py --research --project image-converter`
    *   `python src/orchestrator.py --analyze-idea --project image-converter`

4.  **Generate Architecture:**
    *   `python src/orchestrator.py --build --project image-converter`
    *   Monitors Architect Agent creating implementation plan(s). Review the generated file(s) in `docs/` (e.g., `impl.md`, `impl_*.md`).

5.  **Generate Code:**
    *   `python src/orchestrator.py --code --project image-converter`
    *   Monitors Coder Agent creating source files based on the plans. Review `src/`.

6.  **Review Code:**
    *   `python src/orchestrator.py --review --project image-converter`
    *   Monitors Reviewer Agent. Check if `docs/review.md` was created.

7.  **Apply Fixes (if review.md exists):**
    *   `python src/orchestrator.py --code --fix --project image-converter`
    *   Monitors Coder Agent applying fixes based on `review.md` and Architect Agent checking for plan updates. Review changes in `src/` and potentially `docs/`. Repeat steps 6 & 7 if necessary.

8.  **(Manual) Setup Dependencies & Environment:**
    *   Navigate to the project directory: `cd ~/projects/image-converter`
    *   Create a virtual environment: `python -m venv .venv`
    *   Activate it: `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows)
    *   Identify required packages (e.g., from `impl.md` or code analysis). Let's assume `Pillow` is needed.
    *   Install dependencies: `pip install Pillow`
    *   (Optional) Create `requirements.txt`: `pip freeze > requirements.txt`

9.  **(Manual) Generate Tests & Run Them:**
    *   Use the `--update` command with instructions for tests, or manually trigger the Tester agent if possible, or write tests manually based on `impl.md`.
    *   Example using `--update` (might need refinement): `python ../../src/orchestrator.py --update "Generate pytest tests for the core conversion logic" --project image-converter` (Run from MAAI root or adjust path). Review `tests/`.
    *   Run tests (ensure venv is active): `pytest`

10. **(Optional) Generate Documentation:**
    *   `python ../../src/orchestrator.py --generate-doc project_overview --project image-converter`
    *   `python ../../src/orchestrator.py --generate-doc user_manual --project image-converter`

11. **Iteratively Update (General Changes):**
    *   `python ../../src/orchestrator.py --update "Add support for resizing images with an optional --width and --height argument" --project image-converter`
    *   Runs Architect -> Coder -> Tester -> Documenter updates based on the general instruction.
    *   Review changes. Follow up with `--review` and `--code --fix` if needed (Steps 6-7). Manually update dependencies if required (Step 8). Rerun tests (Step 9).

12. **Clean Up:**
    *   Use `--reset` or `--scratch` from the MAAI root directory as needed.
    *   `python src/orchestrator.py --scratch --project image-converter`

This provides a flexible workflow, combining automated agent steps with necessary manual intervention for environment setup and testing.