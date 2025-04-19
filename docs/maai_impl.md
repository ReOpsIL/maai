# Multi-Agent Coding CLI Application: Implementation Plan

## 1. Overview

This document details the implementation strategy for the Multi-Agent Coding CLI Application (MAAI), based on the concept outlined in `docs/maai.md`. It covers the architecture, technology stack, agent specifics, workflow, project structure, and potential future enhancements.

## 2. Architecture

The application will follow a modular, agent-based architecture orchestrated by a central CLI controller.

*   **Orchestrator:** The main entry point (`src/main.py`), responsible for parsing CLI commands, managing project lifecycles, and invoking the appropriate agent sequence.
*   **Agents:** Independent modules (`src/agents/`) each performing a specific task in the development pipeline. They will communicate primarily through files within the designated project directory.
*   **Project Structure:** All generated artifacts for a specific idea will reside within `projects/<project_name>/`, ensuring isolation and organization. The application's own code will live under `src/`.

```mermaid
graph TD
    A[User CLI Input] --> B(Orchestrator);

    subgraph Project Directory (projects/<name>/)
        P_IDEA(docs/idea.md);
        P_RESEARCH(docs/research_summary.md);
        P_ANALYSIS(docs/market_analysis.md);
        P_IMPL(docs/impl_*.md);
        P_INTEG(docs/integ.md);
        P_SRC(src/*.py);
        P_REVIEW(docs/review.md);
        P_TESTS(tests/test_*.py);
        P_DOCS(docs/*.md);
    end

    subgraph Agent Interactions
        B -- "--idea" --> C(Innovator Agent);
        C -- writes --> P_IDEA;

        B -- "--update-idea" --> C; # Innovator updates idea
        C -- updates --> P_IDEA;

        B -- "--research" --> J(Research Agent);
        J -- reads --> P_IDEA;
        J -- writes --> P_RESEARCH;

        B -- "--analyze-idea" --> K(Market Analyst Agent);
        K -- reads --> P_IDEA;
        K -- writes --> P_ANALYSIS;

        B -- "--build" --> D(Architect Agent);
        D -- reads --> P_IDEA;
        D -- writes --> P_IMPL;
        D -- writes --> P_INTEG;

        B -- "--code" --> E(Coder Agent);
        E -- reads --> P_IMPL;
        E -- reads --> P_INTEG;
        E -- writes --> P_SRC;

        B -- "--review" --> F(Reviewer Agent);
        F -- reads --> P_SRC;
        F -- reads --> P_IMPL;
        F -- writes --> P_REVIEW;

        B -- "--code --fix" --> E;
        E -- reads --> P_REVIEW; # Coder reads review for fix
        E -- writes --> P_SRC; # Coder updates code
        E -- notifies --> D; # Coder notifies Architect
        D -- reads --> P_REVIEW; # Architect reads review
        D -- reads --> P_SRC; # Architect reads updated code
        D -- writes --> P_IMPL; # Architect potentially updates impl
        D -- writes --> P_INTEG; # Architect potentially updates integ

        B -- "--generate-doc <type>" --> H(Documenter Agent);
        H -- reads --> P_IDEA;
        H -- reads --> P_IMPL;
        H -- reads --> P_SRC;
        H -- writes --> P_DOCS; # Specific doc file

        B -- "--update" --> D;
        D -- updates --> P_IMPL;
        D -- updates --> P_INTEG;
        D -- notifies --> E;
        E -- updates --> P_SRC;
        E -- notifies --> G(Tester Agent); # Tester is part of --update
        G -- updates --> P_TESTS;
        G -- notifies --> H; # Documenter regenerates overview
        H -- updates --> P_DOCS; # Specifically project_overview.md

        B -- "list/reset/scratch" --> I(Filesystem Operations);
    end
```

## 3. Technology Stack

*   **Language:** Python 3.9+
*   **CLI Parsing:** `argparse`
*   **AI Integration:** `google-generativeai` (for Innovator, potentially others)
*   **Code Analysis (Reviewer):** `pylint`, `flake8` (via `subprocess`)
*   **Testing (Tester):** `unittest` or `pytest` (generation assistance, execution via `subprocess`)
*   **File Operations:** `os`, `shutil`
*   **Environment Variables:** `python-dotenv` (to load `GEMINI_API_KEY`)

## 4. Orchestrator (`src/main.py`)

*   **Initialization:** Load environment variables (e.g., `GEMINI_API_KEY`) and configure logging.
*   **Argument Parsing:** Define arguments for `list`, `idea`, `update-idea`, `research`, `analyze-idea`, `build`, `code`, `review`, `reset`, `scratch`, `update`, `generate-doc`, etc., using `argparse`. Include the `--fix` flag for use with `--code`, and integrate enhanced error handling and logging as per the updated implementation.
    *   `idea`: Takes `<text>` and optional `--project <name>`.
    *   `update-idea`: Takes `<text>` and requires `--project <name>`.
    *   `research`, `analyze-idea`, `build`, `code`, `review`, `reset`, `scratch`, `update`, `generate-doc`: Require `--project <name>`.
    *   `generate-doc`: Takes `<type>` argument.
    *   `fix`: Boolean flag, only valid with `--code`.
*   **Project Management:**
    *   Functions to create project directories (`projects/<name>/{docs,src,tests}`).
    *   Functions to generate project names from idea text (slugify).
    *   Functions to list projects in `projects/`.
    *   Functions to handle `reset` (delete specific files) and `scratch` (delete files and clear directories).
*   **Command Handling:**
    *   `list`: Call project listing function.
    *   `idea`: Instantiate and run `InnovatorAgent` (create mode).
    *   `update-idea`: Instantiate and run `InnovatorAgent` (update mode).
    *   `research`: Instantiate and run `ResearchAgent`.
    *   `analyze-idea`: Instantiate and run `MarketAnalystAgent`.
    *   `build`: Instantiate and run `ArchitectAgent`.
    *   `code`: Instantiate and run `CoderAgent`. If `--fix` is present, read `docs/review.md` and pass feedback to `CoderAgent`, then notify `ArchitectAgent`.
    *   `review`: Instantiate and run `ReviewerAgent`.
    *   `update`: Instantiate and run sequence: `ArchitectAgent` -> `CoderAgent` -> `TesterAgent` -> `DocumenterAgent` based on general modification text.
    *   `generate-doc`: Instantiate and run `DocumenterAgent` with specified type.
    *   `reset`, `scratch`: Call respective project management functions.
*   **Error Handling:** Implement try-except blocks for file operations, API calls, and agent execution failures. Provide informative error messages.
*   **Logging:** Use the `logging` module for progress tracking and debugging.

## 5. Agent Implementations (`src/agents/`)

A base class `src/agents/base_agent.py` could define a common interface:

```python
# src/agents/base_agent.py
import logging
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, project_path):
        self.project_path = project_path
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def run(self, *args, **kwargs):
        """Executes the agent's primary task."""
        pass
```

### 5.1. Innovator Agent (`src/agents/innovator.py`)

*   **Input:** Idea text, optional existing project name.
*   **Process:**
    *   Check for `GEMINI_API_KEY`.
    *   Initialize the Google Generative AI client.
    *   Construct a prompt to expand the user's idea into features, user stories, etc.
    *   Call the LLM API.
    *   Determine project name (generate if needed).
    *   Ensure project directory structure exists.
    *   Write/Append the generated content to `projects/<name>/docs/idea.md`.
*   **Output:** Path to `idea.md`.

### 5.2. Research Agent (`src/agents/research_agent.py`)

*   **Input:** Path to `idea.md`.
*   **Process:**
    *   Read `idea.md`.
    *   Use LLM to search for relevant technical information, libraries, APIs, or existing projects based on the idea.
    *   Summarize findings.
*   **Output:** Writes summary to `projects/<name>/docs/research_summary.md`.

### 5.3. Market Analyst Agent (`src/agents/market_analyst.py`)

*   **Input:** Path to `idea.md`.
*   **Process:**
    *   Read `idea.md`.
    *   Use LLM to analyze the idea for potential target audience, market fit, unique selling points, and potential challenges.
*   **Output:** Writes analysis to `projects/<name>/docs/market_analysis.md`.

### 5.4. Architect Agent (`src/agents/architect.py`)

*   **Input:** Path to `idea.md`, or modification text (from user or `review.md`) + context from existing `impl_*.md`/`integ.md`. It uses a new method to create update prompts for regenerating plans.
*   **Process:**
    *   Read `idea.md` and/or existing plans/modification text.
    *   Analyze requirements/feedback using LLM.
    *   Define/update:
        *   Components, modules, classes, functions.
        *   Data structures.
        *   Interaction flows.
        *   Technology stack.
        *   Testing strategy.
    *   Format output using delimiters (`<<<COMPONENT: ...>>>`, `<<<INTEGRATION>>>`).
*   **Output:** Writes content to `projects/<name>/docs/impl_*.md` and `projects/<name>/docs/integ.md`.

### 5.5. Coder Agent (`src/agents/coder.py`)

*   **Input:** Paths to `impl_*.md`, `integ.md`. Optional feedback from `docs/review.md` (if `--fix` is used). It now includes methods for generating and parsing project structures (`_generate_structure_list`, `_parse_structure_text`, `_create_project_scaffolding`).
*   **Process:**
    *   Read implementation plans.
    *   Parse details (potentially using LLM).
    *   If feedback is provided (via `--fix`), incorporate it into the code generation/modification.
    *   Generate/update Python code files (`.py`) and save them into `projects/<name>/src/`.
*   **Output:** Paths to generated/modified source files. Notifies Architect if run with `--fix`.

### 5.6. Reviewer Agent (`src/agents/reviewer.py`)

*   **Input:** Paths to source code files (`src/*.py`), paths to implementation plans (`impl_*.md`).
*   **Process:**
    *   Read source code and implementation plans.
    *   Use LLM to review code against the plan for correctness, adherence, best practices, etc.
    *   Format feedback clearly if issues are found.
*   **Output:** Writes feedback to `projects/<name>/docs/review.md` if issues are found. Removes the file otherwise.

### 5.7. Tester Agent (`src/agents/tester.py`)

*   **Input:** Paths to source code files (`src/*.py`), paths to implementation plans (`impl_*.md`).
*   **Process:**
    *   Analyze plans and code (potentially LLM-assisted) to generate `pytest` test cases.
    *   Write test cases to `projects/<name>/tests/test_*.py`.
    *   *(Test execution is now typically handled manually or by a separate CI/CD process after code generation/review)*.
*   **Output:** Paths to generated/modified test files.

### 5.8. Documenter Agent (`src/agents/documenter.py`)

*   **Input:** Document type (`<type>` from `--generate-doc`), paths to `idea.md`, implementation plans (`impl_*.md`, `integ.md`), source code (`src/*.py`).
*   **Process:**
    *   Read relevant input files based on the requested document type.
    *   Use LLM with a specific prompt tailored to the document type (e.g., prompt for SRS, prompt for User Manual).
    *   Synthesize information from the various sources.
    *   Format as Markdown.
*   **Output:** Writes content to `projects/<name>/docs/<type>.md` (e.g., `srs.md`, `user_manual.md`). Note: `project_overview` might be saved as `project_docs.md` or `project_overview.md` depending on implementation.

## 6. Project Structure (Application Code)

```
maai/
├── projects/             # Generated projects reside here
│   └── <project_name>/
│       ├── docs/
│       │   ├── idea.md
│       │   ├── research_summary.md
│       │   ├── market_analysis.md
│       │   ├── impl_*.md
│       │   ├── integ.md
│       │   ├── review.md
│       │   └── *.md # Various generated docs (srs.md, api.md, etc.)
│       ├── src/
│       │   └── *.py
│       └── tests/
│           └── test_*.py
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── innovator.py
│   │   ├── architect.py
│   │   ├── coder.py
│   │   ├── reviewer.py
│   │   ├── tester.py
│   │   ├── documenter.py
│   │   ├── market_analyst.py
│   │   └── research_agent.py
│   ├── __init__.py
│   ├── main.py
│   └── utils.py          # Helper functions (e.g., slugify, file ops)
├── tests/                # Tests for the MAAI application itself
│   └── ...
├── requirements.txt
├── .env.example          # Example environment variables
└── README.md             # MAAI application README
```

## 7. Error Handling and Logging

*   Use Python's `logging` module configured in `main.py`. Log agent activities, errors, and key decisions.
*   Implement specific exception handling for API errors (`google.api_core.exceptions`), file I/O errors, `subprocess` errors, and invalid user input.
*   Provide clear feedback to the user upon errors.

## 8. Configuration

*   Requires a `.env` file in the root directory with `GEMINI_API_KEY=your_api_key`.
*   A `config.yaml` file can configure LLM model names and potentially other settings.
*   `requirements.txt` will list all dependencies.

## 9. Innovative Features & Future Enhancements

*   **Interactive Refinement:** Allow users to provide feedback directly to agents during the `build` process (e.g., "Change the database choice in `impl.md`," "Refactor this function in the code").
*   **Agent Specialization:** Allow users to specify *which* LLM model (or even non-LLM tools) to use for each agent role via configuration.
*   **Parallel Agent Execution:** Explore running independent agents (like Reviewer and Tester on different code parts) in parallel where possible.
*   **Version Control Integration:** Automatically initialize a Git repository for new projects and commit artifacts at key stages.
*   **Plugin System:** Allow users to create and add custom agents to the pipeline.
*   **Code Import:** Add a command to import existing code into a project structure for analysis and documentation by the agents.
*   **Security Agent:** Introduce an agent specifically focused on identifying security vulnerabilities in the generated code.
*   **Deployment Agent:** An agent that attempts to generate deployment configurations (e.g., Dockerfile, serverless function definitions).

## 10. Implementation Steps

1.  Set up the basic project structure and `requirements.txt`.
2.  Implement the `Orchestrator` CLI argument parsing (`argparse`) including all commands (`idea`, `update-idea`, `research`, `analyze-idea`, `build`, `code`, `review`, `fix`, `generate-doc`, `update`, `reset`, `scratch`, `list`) and project management functions.
3.  Implement the `InnovatorAgent` (`--idea`, `--update-idea`).
4.  Implement the `ResearchAgent` (`--research`).
5.  Implement the `MarketAnalystAgent` (`--analyze-idea`).
6.  Implement the `ArchitectAgent` (`--build`, update logic).
7.  Implement the `CoderAgent` (`--code`, `--fix` logic).
8.  Implement the `ReviewerAgent` (`--review`, writing to `review.md`).
9.  Implement the `TesterAgent` (test generation, update logic).
10. Implement the `DocumenterAgent` (`--generate-doc <type>`).
11. Integrate agent calls into the `Orchestrator` command handlers for all workflows (`--idea`, `--build`, `--code`, `--review`, `--update`, etc.).
12. Implement `reset` and `scratch` commands.
13. Add robust error handling and logging throughout.
14. Write tests for the MAAI application itself.
15. Refine agent prompts and logic for better results and handling of the various workflows.