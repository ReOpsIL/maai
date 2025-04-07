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
    *   **Input:** The `idea.md` document or modification instructions (e.g., from user or review feedback) + existing `impl.md` (for context).
    *   **Process:** Designs `impl.md` based on `idea.md` or updates an existing `impl.md` based on instructions/feedback.
    *   **Output:** `docs/impl_*.md` and `docs/integ.md` (or potentially just `docs/impl.md` depending on agent implementation).

5.  **Coder Agent:**
    *   **Input:** The `impl.md` document, optional feedback (from `docs/review.md` via `--fix`), or general modification instructions + existing code.
    *   **Process:** Generates Python code (`src/`) based on `impl.md` or updates existing code based on instructions/feedback and the latest `impl.md`.
    *   **Output:** Python source files in `src/`.

6.  **Reviewer Agent:**
    *   **Input:** Python source code (`src/`) and the implementation plan (`impl.md`).
    *   **Process:** Uses the LLM to review the generated code for adherence to the plan, correctness, best practices, etc.
    *   **Output:** Writes feedback to `docs/review.md` if issues are found. Removes the file if the review passes.

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
    *   `python src/orchestrator.py --analyze --project <name>`
    *   Runs **Market Analyst Agent** using `docs/idea.md` -> `docs/market_analysis.md`.

*   **Generate Architecture:**
    *   `python src/orchestrator.py --build --project <name>`
    *   Runs **Architect Agent** using `docs/idea.md` -> `docs/impl_*.md`, `docs/integ.md`.

*   **Generate Code:**
    *   `python src/orchestrator.py --code --project <name>`
    *   Runs **Coder Agent** using `docs/impl_*.md` -> `src/*.py`.
    *   `python src/orchestrator.py --code --fix --project <name>`
    *   Runs **Coder Agent** using `docs/impl_*.md` and feedback from `docs/review.md` to update `src/*.py`. Also notifies **Architect Agent** to check if architecture docs need updates based on the review.

*   **Review Code:**
    *   `python src/orchestrator.py --review --project <name>`
    *   Runs **Reviewer Agent** using `src/*.py` and `docs/impl_*.md` -> `docs/review.md` (if issues found).

**Update Commands (for iterative refinement):**

*   **Update Idea:**
    *   `python src/orchestrator.py --update-idea "Modification instructions" --project <name>`
    *   Runs **Innovator Agent** to refine `docs/idea.md`.

*   **General Update (Implementation, Code, Tests, Docs):**
    *   `python src/orchestrator.py --update "General modification instructions" --project <name>`
    *   Runs a sequence to refine the project based on *general* instructions (distinct from the review/fix cycle):
        1.  **Architect** (updates architecture docs)
        2.  **Coder** (updates `src/*.py`)
        3.  **Tester** (updates `tests/*.py`)
        4.  **Documenter** (regenerates `docs/project_overview.md`)
    *   Note: This uses the general modification text for all agents. For targeted fixes based on review, use `--review` then `--code --fix`.


**Documentation Generation:**

*   **Generate Specific Document:**
    *   `python src/orchestrator.py --generate-doc <type> --project <name>`
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
    *   `python src/orchestrator.py --analyze --project a-cli-tool-for-basic-image...`

4.  **Generate Architecture:**
    *   `python src/orchestrator.py --build --project a-cli-tool-for-basic-image...`
    *   Monitors Architect Agent creating implementation plans. Review `docs/impl_*.md`.

5.  **Generate Code:**
    *   `python src/orchestrator.py --code --project a-cli-tool-for-basic-image...`
    *   Monitors Coder Agent creating source files. Review `src/`.

6.  **Review Code:**
    *   `python src/orchestrator.py --review --project a-cli-tool-for-basic-image...`
    *   Monitors Reviewer Agent. Check if `docs/review.md` was created.

7.  **Apply Fixes (if review.md exists):**
    *   `python src/orchestrator.py --code --fix --project a-cli-tool-for-basic-image...`
    *   Monitors Coder Agent applying fixes and Architect Agent checking for updates. Review changes in `src/` and potentially `docs/impl_*.md`.

8.  **(Optional) Generate Tests & Docs:** (Assuming Tester/Documenter are run manually or via a separate script/command now)
    *   *(Example: Manually trigger Tester/Documenter or use `--generate-doc`)*
    *   `python src/orchestrator.py --generate-doc project_overview --project a-cli-tool-for-basic-image...`

9.  **Iteratively Update (General Changes):**
    *   `python src/orchestrator.py --update "Add support for resizing images with an optional --width and --height argument" --project a-cli-tool-for-basic-image...`
    *   Runs Architect -> Coder -> Tester -> Documenter updates based on the general instruction.
    *   Review changes. Follow up with `--review` and `--code --fix` if needed.

10. **Clean Up:**
    *   `reset` or `scratch` as needed.

(Steps renumbered and content updated above)

(Steps renumbered and content updated above)

This provides a flexible workflow for generating, building, and iteratively refining software projects.