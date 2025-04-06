# Multi-Agent Coding CLI Application: Implementation Plan

## 1. Overview

This document details the implementation strategy for the Multi-Agent Coding CLI Application (MAAI), based on the concept outlined in `docs/maai.md`. It covers the architecture, technology stack, agent specifics, workflow, project structure, and potential future enhancements.

## 2. Architecture

The application will follow a modular, agent-based architecture orchestrated by a central CLI controller.

*   **Orchestrator:** The main entry point (`src/orchestrator.py`), responsible for parsing CLI commands, managing project lifecycles, and invoking the appropriate agent sequence.
*   **Agents:** Independent modules (`src/agents/`) each performing a specific task in the development pipeline. They will communicate primarily through files within the designated project directory.
*   **Project Structure:** All generated artifacts for a specific idea will reside within `projects/<project_name>/`, ensuring isolation and organization. The application's own code will live under `src/`.

```mermaid
graph TD
    A[User CLI Input] --> B(Orchestrator);
    B -- idea command --> C(Innovator Agent);
    C -- idea.md --> B;
    B -- build command --> D(Architect Agent);
    D -- impl.md --> E(Coder Agent);
    E -- src/*.py --> F(Reviewer Agent);
    F -- Feedback --> E;
    F -- Code OK --> G(Tester Agent);
    G -- impl.md, src/*.py --> G;
    G -- test_*.py, Results --> F;
    F -- Tests Failed --> E;
    F -- Tests Passed --> H(Documenter Agent);
    H -- idea.md, impl.md, src/*.py --> H;
    H -- project_docs.md --> B;
    B -- list/reset/scratch commands --> I(Filesystem Operations);

    subgraph Project Directory (projects/<name>/)
        C -- writes --> J(docs/idea.md);
        D -- writes --> K(docs/impl.md);
        E -- writes --> L(src/*.py);
        G -- writes --> M(tests/test_*.py);
        H -- writes --> N(docs/project_docs.md);
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

## 4. Orchestrator (`src/orchestrator.py`)

*   **Initialization:** Load environment variables (e.g., `GEMINI_API_KEY`).
*   **Argument Parsing:** Define subparsers for `list`, `idea`, `build`, `reset`, `scratch` using `argparse`.
    *   `idea`: Takes `<text>` and optional `--project <name>`.
    *   `build`, `reset`, `scratch`: Require `--project <name>`.
*   **Project Management:**
    *   Functions to create project directories (`projects/<name>/{docs,src,tests}`).
    *   Functions to generate project names from idea text (slugify).
    *   Functions to list projects in `projects/`.
    *   Functions to handle `reset` (delete specific files) and `scratch` (delete files and clear directories).
*   **Command Handling:**
    *   `list`: Call project listing function.
    *   `idea`: Instantiate and run `InnovatorAgent`.
    *   `build`: Instantiate and run agents sequentially (Architect -> Coder -> Reviewer -> Tester -> Documenter), handling the feedback loops and file I/O. Pass project context (paths) to agents.
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
    *   Call the Gemini API.
    *   Determine project name (generate if needed).
    *   Ensure project directory structure exists.
    *   Write/Append the generated content to `projects/<name>/docs/idea.md`.
*   **Output:** Path to `idea.md`.

### 5.2. Architect Agent (`src/agents/architect.py`)

*   **Input:** Path to `idea.md`.
*   **Process:**
    *   Read `idea.md`.
    *   Analyze the requirements (potentially using an LLM with a specific prompt focused on architecture, or rule-based analysis for simpler projects).
    *   Define:
        *   High-level components/modules.
        *   Key data structures.
        *   Function signatures (high-level).
        *   Interaction flow between components.
        *   Technology choices (if not already implied).
    *   Format the output as Markdown.
*   **Output:** Writes content to `projects/<name>/docs/impl.md`.

### 5.3. Coder Agent (`src/agents/coder.py`)

*   **Input:** Path to `impl.md`, potential feedback from Reviewer/Tester.
*   **Process:**
    *   Read `impl.md`.
    *   Parse the implementation details (potentially using an LLM prompted to generate Python code based on the spec, or structured parsing if `impl.md` follows a strict format).
    *   If feedback is provided, incorporate it into the code generation/modification process.
    *   Generate Python code files (`.py`) and save them into `projects/<name>/src/`. Ensure basic syntax validity.
*   **Output:** Paths to generated/modified source files.

### 5.4. Reviewer Agent (`src/agents/reviewer.py`)

*   **Input:** Paths to source code files, path to `impl.md`.
*   **Process:**
    *   **Static Analysis:** Run `pylint` and `flake8` using `subprocess`. Capture and parse results.
    *   **Specification Adherence:** Compare code structure/functionality against `impl.md` (can be complex; might involve LLM analysis or keyword/structure checking).
    *   **Logic Review (Optional):** Use an LLM to review code snippets for potential bugs or improvements based on the context from `impl.md`.
    *   **Decision:**
        *   If issues found: Generate structured feedback (e.g., file, line number, issue description). Trigger Coder Agent.
        *   If code looks okay: Trigger Tester Agent.
*   **Output:** Feedback data structure (internal), trigger signal (Coder or Tester).

### 5.5. Tester Agent (`src/agents/tester.py`)

*   **Input:** Paths to source code files, path to `impl.md`.
*   **Process:**
    *   **Test Case Generation:** Analyze `impl.md` and source code (potentially LLM-assisted) to generate `unittest` or `pytest` test cases. Focus on function inputs/outputs and component interactions described in `impl.md`.
    *   Write test cases to `projects/<name>/tests/test_*.py`.
    *   **Test Execution:** Run tests using `subprocess` (e.g., `python -m unittest discover projects/<name>/tests` or `pytest projects/<name>/tests`).
    *   **Result Parsing:** Capture and parse test runner output.
    *   **Decision:**
        *   If tests fail: Generate feedback (failed test names, errors). Trigger Reviewer/Coder Agent.
        *   If tests pass: Signal success to the Orchestrator/Reviewer.
*   **Output:** Paths to test files, test results (pass/fail), feedback data structure (internal), trigger signal (Coder/Reviewer or Success).

### 5.6. Documenter Agent (`src/agents/documenter.py`)

*   **Input:** Paths to `idea.md`, `impl.md`, final source code files.
*   **Process:**
    *   Read all input files.
    *   Synthesize information (potentially using an LLM prompted to generate user documentation).
    *   Include:
        *   Project purpose (from `idea.md`).
        *   High-level architecture (from `impl.md`).
        *   How to run/use the generated code.
        *   Key features implemented.
    *   Format as Markdown.
*   **Output:** Writes content to `projects/<name>/docs/project_docs.md`.

## 6. Project Structure (Application Code)

```
maai/
├── projects/             # Generated projects reside here
│   └── <project_name>/
│       ├── docs/
│       │   ├── idea.md
│       │   ├── impl.md
│       │   └── project_docs.md
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
│   │   └── documenter.py
│   ├── __init__.py
│   ├── orchestrator.py
│   └── utils.py          # Helper functions (e.g., slugify, file ops)
├── tests/                # Tests for the MAAI application itself
│   └── ...
├── requirements.txt
├── .env.example          # Example environment variables
└── README.md             # MAAI application README
```

## 7. Error Handling and Logging

*   Use Python's `logging` module configured in `orchestrator.py`. Log agent activities, errors, and key decisions.
*   Implement specific exception handling for API errors (`google.api_core.exceptions`), file I/O errors, `subprocess` errors, and invalid user input.
*   Provide clear feedback to the user upon errors.

## 8. Configuration

*   Requires a `.env` file in the root directory with `GEMINI_API_KEY=your_api_key`.
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
2.  Implement the `Orchestrator` CLI argument parsing and basic project management functions (`list`, directory creation).
3.  Implement the `InnovatorAgent` with Gemini API integration and the `idea` command.
4.  Implement the `ArchitectAgent` and integrate it into the `build` command.
5.  Implement the `CoderAgent` (initially simple, perhaps rule-based or basic LLM call).
6.  Implement the `ReviewerAgent` with static analysis (`pylint`/`flake8`).
7.  Implement the `TesterAgent` (basic test generation/execution).
8.  Implement the `DocumenterAgent`.
9.  Refine the `build` command logic in the `Orchestrator` to handle the full agent pipeline and basic feedback loops.
10. Implement `reset` and `scratch` commands.
11. Add robust error handling and logging.
12. Write tests for the MAAI application itself.
13. Refine agent capabilities, potentially adding more sophisticated LLM interactions and handling the feedback loops more intelligently.