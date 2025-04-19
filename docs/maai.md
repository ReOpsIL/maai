# MAAI: Multi-Agent Coding CLI Application

## Overview

MAAI is a command-line application that leverages a multi-agent system to assist in the software development lifecycle, taking a simple software idea through stages like research, analysis, design, implementation, review, testing updates, and documentation. Each agent specializes in a specific part of the lifecycle, collaborating within a project structure.

## Core Idea

The application aims to streamline the process of turning high-level software ideas into designed, coded, and documented components. Users interact with the system via command-line flags (e.g., `--idea`, `--build`, `--code`, `--review`, `--update`, `--generate-doc`) to manage the development lifecycle and trigger specific agents. All generated artifacts (documents, code, tests) are stored within a structured directory under a main `projects/` folder (configurable, defaults to `~/projects`), specific to each project idea. Dependency management and virtual environment setup might require manual steps.

## Agent Roles

Based on the current implementation in main.py, the agents are as follows:

1.  **InnovatorAgent:** Handles idea generation and expansion.
2.  **ArchitectAgent:** Generates architecture plans.
3.  **CoderAgent:** Generates or updates code based on plans.
4.  **ReviewerAgent:** Reviews code and provides feedback.
5.  **TesterAgent:** Generates tests.
6.  **DocumenterAgent:** Generates documentation.
7.  **MarketAnalystAgent:** Performs market analysis.
8.  **ResearchAgent:** Performs research.
9.  **BusinessAgent:** Generates business perspectives.
10. **ScoringAgent:** Generates scoring reports.
11. **IdeaGenAgent:** Generates lists of ideas.

Each agent is imported and used in specific command handlers, utilizing AI models for their operations.

## Command-Line Interface

From the main.py script, the CLI is parsed using argparse with various mutually exclusive actions. Here's a summary based on the code:

*   **--list:** Lists projects in the specified directory.
*   **--subject:** Generates new list of project ideas based on a subject.
*   **--bulk:** Processes a bulk file to generate projects.
*   **--idea:** Generates a new project idea.
*   **--business:** Generates business docs for a project.
*   **--scoring:** Generates scoring docs for a project.
*   **--research:** Performs technical research for a project.
*   **--analyze:** Performs market analysis for a project.
*   **--docs:** Generates specific documentation for a project.
*   **--build:** Generates architecture docs for a project.
*   **--code:** Generates or fixes code for a project.
*   **--review:** Reviews code for a project.

Each command handler in main.py corresponds to these actions, ensuring the project structure is maintained.

## How to Use (Example Workflow)

1.  **Setup:**
    *   Ensure Python 3.9+ is installed.
    *   Clone the MAAI repository.
    *   Install MAAI's own dependencies: `pip install -r requirements.txt` (in the MAAI repo root).
    *   Create a `.env` file in the MAAI repo root with `GEMINI_API_KEY=YOUR_API_KEY_HERE`.
    *   Review `config.yaml` if needed.

2.  **Create Idea:**
    *   `python src/main.py --idea "A CLI tool for basic image format conversion (jpg, png, webp) using Pillow"`
    *   This creates a project directory (e.g., `~/projects/a-cli-tool-for-basic-image.../`) and `docs/idea.md`. Review `idea.md`. Let's call the project `image-converter`.

3.  **(Optional) Research/Analysis:**
    *   `python src/main.py --research --project image-converter`
    *   `python src/main.py --analyze-idea --project image-converter`

4.  **Generate Architecture:**
    *   `python src/main.py --build --project image-converter`
    *   Monitors Architect Agent creating implementation plan(s). Review the generated file(s) in `docs/` (e.g., `impl.md`, `impl_*.md`).

5.  **Generate Code:**
    *   `python src/main.py --code --project image-converter`
    *   Monitors Coder Agent creating source files based on the plans. Review `src/`.

6.  **Review Code:**
    *   `python src/main.py --review --project image-converter`
    *   Monitors Reviewer Agent. Check if `docs/review.md` was created.

7.  **Apply Fixes (if review.md exists):**
    *   `python src/main.py --code --fix --project image-converter`
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
    *   Example using `--update` (might need refinement): `python ../../src/main.py --update "Generate pytest tests for the core conversion logic" --project image-converter` (Run from MAAI root or adjust path). Review `tests/`.
    *   Run tests (ensure venv is active): `pytest`

10. **(Optional) Generate Documentation:**
    *   `python ../../src/main.py --generate-doc project_overview --project image-converter`
    *   `python ../../src/main.py --generate-doc user_manual --project image-converter`

11. **Iteratively Update (General Changes):**
    *   `python ../../src/main.py --update "Add support for resizing images with an optional --width and --height argument" --project image-converter`
    *   Runs Architect -> Coder -> Tester -> Documenter updates based on the general instruction.
    *   Review changes. Follow up with `--review` and `--code --fix` if needed (Steps 6-7). Manually update dependencies if required (Step 8). Rerun tests (Step 9).

12. **Clean Up:**
    *   Use `--reset` or `--scratch` from the MAAI root directory as needed.
    *   `python src/main.py --scratch --project image-converter`

This provides a flexible workflow, combining automated agent steps with necessary manual intervention for environment setup and testing.