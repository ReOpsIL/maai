# MAAI: Multi-Agent Coding CLI Application

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Optional: Add a license badge if applicable -->

## Overview

MAAI is a command-line application that leverages a multi-agent system to take a simple software idea from conception through research, analysis, design, implementation, testing, and documentation. Each agent specializes in a specific part of the software development lifecycle, collaborating within a project structure to build and refine the final product.

The application aims to automate and streamline the process of turning high-level software ideas into functional, tested, and documented code.

## Features

*   **Multi-Agent System:** Utilizes specialized agents (Innovator, Researcher, Analyst, Architect, Coder, Reviewer, Tester, Documenter) for different development tasks.
*   **End-to-End Automation:** Manages the software lifecycle from idea generation to documentation.
*   **CLI Control:** Provides a command-line interface for managing projects and triggering agents/pipelines.
*   **Structured Projects:** Organizes all generated artifacts (code, tests, docs) within a dedicated `projects/` directory for each idea.
*   **Automated Environment:** Handles dependency extraction (`requirements.txt`), virtual environment creation (`.venv/`), and installation during the build process.
*   **AI-Powered:** Leverages Generative AI (e.g., Google Gemini) for core agent functionalities.

## Installation & Setup

1.  **Prerequisites:**
    *   Python 3.9+

2.  **Clone the Repository (if applicable):**
    ```bash
    git clone <your-repo-url>
    cd maai
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Key:**
    *   Create a `.env` file in the root directory.
    *   Add your Generative AI API key:
        ```
        GEMINI_API_KEY=YOUR_API_KEY_HERE
        ```
    *   *(Note: Replace `GEMINI_API_KEY` if using a different provider as configured in `config.yaml`)*

5.  **Review Configuration:**
    *   Check the `config.yaml` file for model settings and other configurations.

## Usage

MAAI is controlled via the `src/orchestrator.py` script. Most commands require specifying a project name using `--project <name>`.

**1. Create a New Project Idea:**

```bash
python src/orchestrator.py --idea "A brief description of your software idea"
# Example: python src/orchestrator.py --idea "A CLI tool for basic image format conversion"
```
This generates a project name (or uses one if provided with `--project`), creates the directory structure in `projects/`, and runs the Innovator Agent to create `docs/idea.md`.

**2. Build the Project:**

```bash
python src/orchestrator.py --build --project <your-project-name>
# Example: python src/orchestrator.py --build --project a-cli-tool-for-basic-image...
```
This executes the full development pipeline: Architect -> Dependency Setup -> Coder -> Reviewer/Coder Loop -> Tester -> Documenter.

**3. Update an Existing Project:**

```bash
python src/orchestrator.py --update "Instructions for modification" --project <your-project-name>
# Example: python src/orchestrator.py --update "Add support for resizing images" --project a-cli-tool-for-basic-image...
```
This runs the Architect, Coder, Tester, and Documenter agents to update the project based on your instructions. Run `--build` afterwards for full validation including the AI Reviewer and test execution.

**4. List Projects:**

```bash
python src/orchestrator.py --list
```

**5. Generate Specific Documentation:**

```bash
python src/orchestrator.py --generate-doc --doc-type <type> --project <your-project-name>
# Supported types: api, project_overview, sdd, srs, user_manual
# Example: python src/orchestrator.py --generate-doc --doc-type api --project a-cli-tool-for-basic-image...
```

**6. Other Commands:**

Refer to `docs/maai.md` or use `python src/orchestrator.py --help` (if implemented) for details on other commands like `--research`, `--analyze-idea`, `--update-idea`, `--reset`, `--scratch`.

## Agent Roles

*   **Innovator:** Expands ideas.
*   **Research:** Finds relevant technical resources.
*   **Market Analyst:** Analyzes business potential.
*   **Architect:** Designs the implementation plan (`impl.md`).
*   **Coder:** Generates Python code (`src/`).
*   **Reviewer:** Reviews code quality and adherence to the plan.
*   **Tester:** Generates and runs tests (`tests/`).
*   **Documenter:** Generates project documentation (`docs/`).

## Contributing

(Optional: Add guidelines for contributing if this is an open project).

## License

(Optional: Specify the project's license, e.g., MIT License).