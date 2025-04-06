import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from .base_agent import BaseAgent

class DocumenterAgent(BaseAgent):
    """
    Generates user-friendly documentation based on the project concept,
    implementation plan, and final source code.
    """

    SUPPORTED_DOC_TYPES = ['sdd', 'srs', 'api', 'user_manual', 'project_overview']

    def run(self, doc_type: str, update_mode: bool = False) -> str:
        """
        Executes the Documenter agent's task: generating a specific type of documentation.

        Args:
            doc_type: The type of document to generate (e.g., 'srs', 'api', 'user_manual').

        Returns:
            The absolute path to the generated document file.
        """
        self.logger.info(f"Running Documenter Agent for project: {self.project_name} (Doc Type: {doc_type})")

        if doc_type not in self.SUPPORTED_DOC_TYPES:
            raise ValueError(f"Unsupported document type '{doc_type}'. Supported types: {', '.join(self.SUPPORTED_DOC_TYPES)}")

        # Determine output path based on doc_type
        output_filename = f"{doc_type}.md" # Simple naming convention
        if doc_type == 'project_overview': # Keep original name for general docs
             output_filename = "project_docs.md"
        output_doc_path = os.path.join(self.docs_path, output_filename)
        idea_md_path = os.path.join(self.docs_path, "idea.md")
        impl_md_path = os.path.join(self.docs_path, "impl.md")
        # project_docs_md_path = os.path.join(self.docs_path, "project_docs.md") # Replaced by dynamic path

        # --- Read Input Files ---
        self.logger.info(f"Reading concept from: {idea_md_path}")
        idea_content = self._read_file(idea_md_path)
        if idea_content is None:
            self.logger.warning(f"Could not read {idea_md_path}. Documentation might be incomplete.")
            idea_content = "# Project Concept\n\n(Could not read idea.md)"

        self.logger.info(f"Reading implementation plan from: {impl_md_path}")
        impl_content = self._read_file(impl_md_path)
        if impl_content is None:
            self.logger.warning(f"Could not read {impl_md_path}. Documentation might be incomplete.")
            impl_content = "# Implementation Plan\n\n(Could not read impl.md)" # Keep reading context

        self.logger.info("Reading source code...")
        source_code_content = self._read_source_code()
        if not source_code_content:
             self.logger.warning("No source code found. Documentation quality may be limited.")

        existing_docs_content = None
        if update_mode:
             self.logger.info(f"Reading existing documentation: {project_docs_md_path}")
             existing_docs_content = self._read_file(project_docs_md_path)
             if existing_docs_content is None:
                  self.logger.warning(f"Existing documentation file not found at {project_docs_md_path}. Will generate new documentation based on instructions.")
                  # Treat as creation mode but with modification text as primary input? Or fail?
                  # Let's proceed, effectively generating based on instructions + context.
        # --- Generate Specific Documentation ---
        self.logger.info(f"Attempting to generate '{doc_type}' documentation using AI.")
        try:
            documentation = self._generate_specific_documentation(
                doc_type=doc_type,
                idea_content=idea_content,
                impl_content=impl_content,
                source_code=source_code_content
            )
            self.logger.info(f"Successfully generated '{doc_type}' documentation content using AI.")
        except (ValueError, ConnectionError, RuntimeError) as e:
            self.logger.error(f"Failed to generate '{doc_type}' documentation using AI: {e}")
            raise RuntimeError(f"Documenter Agent failed: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during '{doc_type}' documentation generation: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Documenter Agent: {e}")

        # --- Write Documentation File ---
        self.logger.info(f"Writing documentation to: {output_doc_path}")
        try:
            self._write_file(output_doc_path, documentation)
            self.logger.info(f"Successfully wrote {output_doc_path}")
        except Exception as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write {output_filename} for project {self.project_name}: {e}")

        return output_doc_path


    def _read_source_code(self) -> dict[str, str]:
        """Reads all .py files from the project's src directory."""
        # This is identical to the one in TesterAgent - consider moving to BaseAgent
        code_files = {}
        if not os.path.isdir(self.src_path):
            self.logger.warning(f"Source directory not found: {self.src_path}")
            return code_files

        try:
            for filename in os.listdir(self.src_path):
                if filename.endswith(".py"):
                    file_path = os.path.join(self.src_path, filename)
                    content = self._read_file(file_path)
                    if content is not None:
                        # Store with path relative to project root (e.g., src/module.py)
                        relative_path = os.path.relpath(file_path, self.project_path)
                        code_files[relative_path] = content
        except Exception as e:
            self.logger.error(f"Error reading source code files from {self.src_path}: {e}", exc_info=True)
        return code_files

    def _generate_specific_documentation(self, doc_type: str, idea_content: str, impl_content: str, source_code: dict[str, str]) -> str:
        """Generates the content for a specific documentation type."""
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("DocumenterAgent requires a configured Generative Model.")

        # Dispatch to the correct prompt creation function
        prompt_func = getattr(self, f"_create_{doc_type}_prompt", None)
        if not prompt_func:
             # Fallback or error if specific prompt function doesn't exist
             self.logger.warning(f"No specific prompt function found for doc type '{doc_type}'. Using project overview prompt.")
             prompt_func = self._create_project_overview_prompt # Default to overview

        prompt = prompt_func(idea_content, impl_content, source_code)
        self.logger.debug(f"Generated prompt for '{doc_type}' using {prompt_func.__name__}:\n{prompt[:500]}...")
        try:
            self.logger.info(f"Sending request to Gemini API for '{doc_type}' documentation...")
            # Consider adjusting token limits if context is large
            # generation_config = genai.types.GenerationConfig(max_output_tokens=4096)
            # response = self.model.generate_content(prompt, generation_config=generation_config)
            response = self.model.generate_content(prompt)
            generated_docs = response.text
            self.logger.info(f"Received '{doc_type}' documentation response from Gemini API.")
            self.logger.debug(f"Generated '{doc_type}' Docs (first 200 chars):\n{generated_docs[:200]}...")
            return generated_docs

        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Documenter - {doc_type}): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for '{doc_type}' documentation: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Gemini API call (Documenter - {doc_type}): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate '{doc_type}' documentation using AI: {e}")


    # --- Prompt Creation Functions ---

    def _create_project_overview_prompt(self, idea_content: str, impl_content: str, source_code: dict[str, str]) -> str:
        """Creates the prompt for the general project documentation (project_docs.md)."""

        source_code_blocks = []
        if source_code:
            for path, code in source_code.items():
                 # Limit code length per file in prompt if necessary
                 max_code_len = 1500
                 truncated_code = code[:max_code_len] + ("\n..." if len(code) > max_code_len else "")
                 source_code_blocks.append(f"**File: `{path}`**\n```python\n{truncated_code}\n```")
        else:
             source_code_blocks.append("*(No source code provided)*")

        source_code_section = "\n\n".join(source_code_blocks)

        prompt = f"""
Generate user-friendly project documentation in Markdown format (`project_docs.md`) based on the provided project concept, implementation plan, and final source code.

**Project Concept (from idea.md):**
```markdown
{idea_content}
```

**Implementation Plan (from impl.md):**
```markdown
{impl_content}
```

**Final Source Code Snippets (from src/):**
{source_code_section}

**Instructions:**

1.  **Generate a comprehensive `project_docs.md` file.**
2.  **Target Audience:** Assume a user who wants to understand what the project does and how to use it. Technical users might also appreciate architecture overview.
3.  **Include the following sections:**
    *   **Project Overview:** Briefly describe the project's purpose and main goal (synthesize from `idea.md`).
    *   **Features:** List the key features implemented (refer to `idea.md` and `impl.md`).
    *   **Getting Started / Usage:** Explain how to run or use the generated application/tool. Include example commands if it's a CLI tool. Mention any prerequisites (e.g., Python version, `pip install requirements.txt`).
    *   **Architecture Overview (Optional but Recommended):** Briefly describe the main components and how they work together (summarize from `impl.md`). A Mermaid diagram from `impl.md` could be included if relevant and simple.
    *   **Configuration (if applicable):** Mention any required configuration (e.g., environment variables like API keys).
    *   **Troubleshooting (Optional):** Common issues and solutions.
4.  **Synthesize information** from all provided inputs (`idea.md`, `impl.md`, source code snippets).
5.  **Maintain a clear and concise writing style.** Use Markdown formatting effectively (headings, lists, code blocks).
6.  **Do NOT just copy sections verbatim.** Rephrase and structure the information logically for documentation purposes.
7.  **Format the entire output strictly as Markdown.** Do not include introductory or concluding remarks outside the Markdown structure.
"""
        # This prompt is the same as the original _create_prompt
        # ... (keep the original prompt content here) ...
        source_code_blocks = []
        if source_code:
            for path, code in source_code.items():
                 max_code_len = 1500 # Keep truncation for prompt size
                 truncated_code = code[:max_code_len] + ("\n..." if len(code) > max_code_len else "")
                 source_code_blocks.append(f"**File: `{path}`**\n```python\n{truncated_code}\n```")
        else:
             source_code_blocks.append("*(No source code provided)*")
        source_code_section = "\n\n".join(source_code_blocks)

        prompt = f"""
Generate user-friendly project documentation in Markdown format (`project_docs.md`) based on the provided project concept, implementation plan, and final source code.

**Project Concept (from idea.md):**
```markdown
{idea_content}
```

**Implementation Plan (from impl.md):**
```markdown
{impl_content}
```

**Final Source Code Snippets (from src/):**
{source_code_section}

**Instructions:**

1.  **Generate a comprehensive `project_docs.md` file.**
2.  **Target Audience:** Assume a user who wants to understand what the project does and how to use it. Technical users might also appreciate architecture overview.
3.  **Include the following sections:**
    *   **Project Overview:** Briefly describe the project's purpose and main goal (synthesize from `idea.md`).
    *   **Features:** List the key features implemented (refer to `idea.md` and `impl.md`).
    *   **Getting Started / Usage:** Explain how to run or use the generated application/tool. Include example commands if it's a CLI tool. Mention any prerequisites (e.g., Python version, `pip install requirements.txt`).
    *   **Architecture Overview (Optional but Recommended):** Briefly describe the main components and how they work together (summarize from `impl.md`). A Mermaid diagram from `impl.md` could be included if relevant and simple.
    *   **Configuration (if applicable):** Mention any required configuration (e.g., environment variables like API keys).
    *   **Troubleshooting (Optional):** Common issues and solutions.
4.  **Synthesize information** from all provided inputs (`idea.md`, `impl.md`, source code snippets).
5.  **Maintain a clear and concise writing style.** Use Markdown formatting effectively (headings, lists, code blocks).
6.  **Do NOT just copy sections verbatim.** Rephrase and structure the information logically for documentation purposes.
7.  **Format the entire output strictly as Markdown.** Do not include introductory or concluding remarks outside the Markdown structure.
"""
        return prompt


    def _create_srs_prompt(self, idea_content: str, impl_content: str, source_code: dict[str, str]) -> str:
         """Creates the prompt for generating an SRS document."""
         # Note: Source code might be less relevant for SRS, but included for context
         prompt = f"""
Generate a System Requirements Specification (SRS) document in Markdown format based on the provided project concept and implementation plan.

**Project Concept (idea.md):**
```markdown
{idea_content}
```

**Implementation Plan (impl.md):**
```markdown
{impl_content}
```

**Instructions:**

1.  **Generate an SRS document (`srs.md`).**
2.  **Focus on detailing functional and non-functional requirements.**
3.  **Include the following sections (adapt based on available information):**
    *   **Introduction:** Purpose of the document, scope of the project, definitions/acronyms.
    *   **Overall Description:** Product perspective, product functions (summarized), user characteristics, constraints, assumptions.
    *   **Functional Requirements:** Detail specific functions the system must perform. Use clear, numbered requirements (e.g., FR-01: The system shall...). Derive these from the features in `idea.md` and the modules/methods in `impl.md`.
    *   **Non-Functional Requirements:** Detail quality attributes like performance, usability, reliability, security, maintainability, portability. (Infer these or make reasonable assumptions if not specified).
    *   **Interface Requirements:** Describe user interfaces (CLI, GUI if applicable), hardware interfaces, software interfaces (e.g., external APIs mentioned in `impl.md`).
    *   **(Optional) Use Cases / User Stories:** Include key use cases or user stories from `idea.md` if available.
4.  **Synthesize information** primarily from `idea.md` and `impl.md`.
5.  **Format the entire output strictly as Markdown.** Use clear headings and structured lists for requirements.

**Generate the complete SRS document (`srs.md`) below:**
"""
         return prompt

    def _create_api_docs_prompt(self, idea_content: str, impl_content: str, source_code: dict[str, str]) -> str:
         """Creates the prompt for generating API documentation."""
         # Note: Requires source code analysis by the LLM.
         source_code_blocks = []
         if source_code:
             for path, code in source_code.items():
                  # Include full code for API docs if possible, maybe truncate less aggressively
                  max_code_len = 4000
                  truncated_code = code[:max_code_len] + ("\n..." if len(code) > max_code_len else "")
                  source_code_blocks.append(f"**File: `{path}`**\n```python\n{truncated_code}\n```")
         else:
              return "**Error:** Cannot generate API documentation without source code."
         source_code_section = "\n\n".join(source_code_blocks)

         prompt = f"""
Generate API documentation in Markdown format based on the provided Python source code and implementation plan. Focus on documenting public functions, classes, and methods that form the project's API (internal or external).

**Implementation Plan (impl.md):**
```markdown
{impl_content}
```

**Source Code (src/):**
{source_code_section}

**Instructions:**

1.  **Generate API documentation (`api.md`).**
2.  **Analyze the source code** to identify public classes, methods, and functions. Pay attention to docstrings and type hints.
3.  **Structure the documentation logically,** perhaps by module.
4.  **For each key component (class/function):**
    *   Provide a brief description of its purpose.
    *   List methods/functions with their parameters (including type hints if available).
    *   Describe what each method/function does.
    *   Mention return values (including type hints if available).
    *   Include simple code examples if possible (especially for CLI entry points or key library functions).
5.  **If the project exposes an external API (e.g., REST),** document the endpoints, request/response formats, and authentication methods based on the `impl.md` and code.
6.  **Format the entire output strictly as Markdown.** Use code blocks for signatures and examples.

**Generate the complete API documentation (`api.md`) below:**
"""
         return prompt

    def _create_user_manual_prompt(self, idea_content: str, impl_content: str, source_code: dict[str, str]) -> str:
         """Creates the prompt for generating a User Manual."""
         # Note: Source code less critical here, focus on idea/impl
         prompt = f"""
Generate a user manual (or help guide) in Markdown format for the project described below. Assume the target audience is an end-user who wants to install and use the application/tool.

**Project Concept (idea.md):**
```markdown
{idea_content}
```

**Implementation Plan (impl.md):**
```markdown
{impl_content}
```

**Instructions:**

1.  **Generate a User Manual (`user_manual.md`).**
2.  **Focus on practical steps and explanations for the end-user.**
3.  **Include the following sections (adapt based on available information):**
    *   **Introduction:** What the project is and what it does for the user.
    *   **Installation / Setup:** Step-by-step instructions on how to install prerequisites (like Python, pip) and the application itself (e.g., `pip install -r requirements.txt`). Mention any necessary configuration (e.g., setting API keys in `.env`).
    *   **Getting Started / Basic Usage:** A simple tutorial showing how to perform the main task(s). Include example commands for CLI tools.
    *   **Features / Commands:** Describe the main features or commands in more detail. Explain options and arguments.
    *   **(Optional) Examples:** Provide more detailed examples of use cases.
    *   **(Optional) Troubleshooting:** List common problems and how to solve them.
    *   **(Optional) Getting Help:** Where to find more information or report issues.
4.  **Synthesize information** primarily from `idea.md` (features, user stories) and `impl.md` (architecture, CLI commands, configuration).
5.  **Format the entire output strictly as Markdown.** Use clear headings, lists, and code blocks for commands/examples.

**Generate the complete User Manual (`user_manual.md`) below:**
"""
         return prompt

    def _create_sdd_prompt(self, idea_content: str, impl_content: str, source_code: dict[str, str]) -> str:
         """Creates the prompt for generating a Software Design Document (SDD)."""
         # Note: Relies heavily on impl.md and source code.
         source_code_blocks = []
         if source_code:
             for path, code in source_code.items():
                  # Include full code if possible, maybe truncate less aggressively
                  max_code_len = 4000
                  truncated_code = code[:max_code_len] + ("\n..." if len(code) > max_code_len else "")
                  source_code_blocks.append(f"**File: `{path}`**\n```python\n{truncated_code}\n```")
         else:
              source_code_blocks.append("*(No source code provided)*")
         source_code_section = "\n\n".join(source_code_blocks)

         prompt = f"""
Generate a Software Design Document (SDD) in Markdown format based on the provided implementation plan and source code.

**Implementation Plan (impl.md):**
```markdown
{impl_content}
```

**Source Code (src/):**
{source_code_section}

**Instructions:**

1.  **Generate an SDD document (`sdd.md`).**
2.  **Focus on describing the system's architecture, components, interfaces, and data.**
3.  **Include the following sections (derive details from `impl.md` and source code):**
    *   **Introduction:** Purpose, scope, overview of the design.
    *   **System Architecture:** High-level overview of the architecture (e.g., layers, major components). Use Mermaid diagrams from `impl.md` if available and relevant.
    *   **Component Design (Low-Level Design):** For each major component/module identified in `impl.md` or `src/`:
        *   Purpose and responsibilities.
        *   Key classes and functions within the component.
        *   Relationships with other components (dependencies).
        *   Algorithms or complex logic used (if applicable).
    *   **Data Design:** Describe major data structures, file formats, or database schemas used (refer to `impl.md` and code).
    *   **Interface Design:**
        *   User Interface (CLI description, if applicable).
        *   External Interfaces (APIs the system consumes or provides, based on `impl.md` and code).
        *   Internal Interfaces (how components interact).
    *   **Deployment Considerations (Optional):** Briefly mention how the system might be deployed based on its nature (e.g., standalone script, web service).
4.  **Synthesize information** primarily from `impl.md` and the actual `source_code`. Use `idea.md` for high-level context if needed.
5.  **Format the entire output strictly as Markdown.** Use clear headings, subheadings, lists, and code blocks where appropriate.

**Generate the complete SDD document (`sdd.md`) below:**
"""
         return prompt

    # Removed _create_update_prompt as update mode is deferred