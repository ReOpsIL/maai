import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    """
    Analyzes the project concept (idea.md) and designs the high-level
    architecture and implementation strategy (impl.md).
    """

    def run(self, modification_text: str | None = None, update_mode: bool = False):
        """
        Executes the Architect agent's task: creating or updating the impl.md file.

        Args:
            modification_text: Instructions on how to modify the existing plan
                               (used when update_mode is True).
            update_mode: If True, read existing impl.md, apply modifications based
                         on modification_text and potentially updated idea.md, and overwrite.
                         If False, create a new impl.md based on idea.md.
        """
        self.logger.info(f"Running Architect Agent for project: {self.project_name} (Update Mode: {update_mode})")
        idea_md_path = os.path.join(self.docs_path, "idea.md")
        impl_md_path = os.path.join(self.docs_path, "impl.md")

        self.logger.info(f"Reading concept from: {idea_md_path}")
        idea_content = self._read_file(idea_md_path)
        if idea_content is None:
            raise FileNotFoundError(f"Could not read idea.md for project {self.project_name}. Please ensure it exists.")

        self.logger.info("Attempting to generate or update implementation plan using AI.")
        try:
            implementation_plan = self._generate_or_update_plan(
                idea_content=idea_content,
                modification_text=modification_text,
                update_mode=update_mode,
                impl_md_path=impl_md_path # Pass path for reading in update mode
            )
            self.logger.info("Successfully generated/updated implementation plan using AI.")
        except (FileNotFoundError, ValueError, ConnectionError, RuntimeError) as e: # Added FileNotFoundError
            self.logger.error(f"Failed to generate/update implementation plan using AI: {e}")
            raise RuntimeError(f"Architect Agent failed: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during plan generation/update: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Architect Agent: {e}")
        self.logger.info(f"Writing implementation plan to: {impl_md_path}")
        try:
            self._write_file(impl_md_path, implementation_plan)
            self.logger.info(f"Successfully wrote {impl_md_path}")
        except Exception as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write impl.md for project {self.project_name}: {e}")

        return impl_md_path

    def _generate_or_update_plan(self, idea_content: str, modification_text: str | None, update_mode: bool, impl_md_path: str) -> str:
        """Uses Generative AI to create or update the implementation plan."""
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("ArchitectAgent requires a configured Generative Model.")

        existing_impl_content = None
        if update_mode:
            if not modification_text:
                 raise ValueError("Modification text is required when running Architect in update mode.")
            self.logger.info(f"Reading existing implementation plan: {impl_md_path}")
            existing_impl_content = self._read_file(impl_md_path)
            if existing_impl_content is None:
                raise FileNotFoundError(f"Cannot update implementation plan: Existing file not found at {impl_md_path}")
            prompt = self._create_update_prompt(existing_impl_content, modification_text, idea_content)
            self.logger.debug(f"Generated update prompt for Gemini (Architect):\n{prompt[:500]}...")
        else:
            # Create mode
            prompt = self._create_prompt(idea_content)
            self.logger.debug(f"Generated create prompt for Gemini (Architect):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to Gemini API for architecture plan...")
            response = self.model.generate_content(prompt)
            generated_plan = response.text
            self.logger.info("Received architecture plan from Gemini API.")
            self.logger.debug(f"Generated Plan (first 200 chars):\n{generated_plan[:200]}...")
            return generated_plan
        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Architect): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for architecture plan: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Gemini API call (Architect): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate architecture plan using AI: {e}")


    def _create_prompt(self, idea_content: str) -> str: # For initial creation
        """Creates the prompt for the generative AI model to design the architecture."""
        prompt = f"""
Analyze the following project concept (provided in Markdown) and generate a detailed implementation plan, also in Markdown format. The plan should guide the Coder Agent in building the application.

**Project Concept (from idea.md):**
```markdown
{idea_content}
```

**Generate the following sections for the implementation plan (impl.md):**

1.  **Overall Architecture:** Describe the main components (e.g., CLI, core logic modules, data storage, external API interaction) and how they interact. Use Mermaid diagrams (```mermaid graph TD ... ```) if helpful to visualize flow. Specify Python as the implementation language.
2.  **Technology Stack:** Confirm or refine the technology choices (Python version, key libraries like `requests`, `argparse`, `pytest`, etc.). Justify any choices if necessary.
3.  **Project Structure:** Outline the proposed directory structure within the project's `src/` and `tests/` directories. List key files and their purpose (e.g., `src/main.py`, `src/api_client.py`, `src/utils.py`, `tests/test_main.py`).
4.  **Core Modules/Classes:** Define the main Python classes or modules needed. For each, specify:
    *   Purpose/Responsibility.
    *   Key methods/functions (including expected parameters and return types, use type hints).
    *   Important attributes or data structures it manages.
5.  **Data Structures:** Detail any significant data structures (e.g., dictionaries, custom classes) used for passing data between components or storing state.
6.  **API Interaction (if applicable):** If the project involves external APIs, specify:
    *   Which APIs are used.
    *   Key endpoints to interact with.
    *   Data format expected/returned.
    *   Authentication method (if known).
7.  **Error Handling Strategy:** Briefly describe how errors (e.g., API failures, invalid input, file not found) should be handled and reported.
8.  **Testing Strategy:** Outline the approach for testing. Mention the types of tests (unit, integration) and key areas to focus on. Suggest using `pytest` or `unittest`.

**Format the entire output strictly as Markdown.** Ensure the plan is detailed enough for a Coder Agent to understand and implement the project. Do not include introductory or concluding remarks outside the specified Markdown structure.
"""
        return prompt

    def _create_update_prompt(self, existing_impl_content: str, modification_text: str, idea_content: str) -> str:
        """Creates the prompt for the generative AI model to update an existing impl.md."""
        prompt = f"""
Refine and update the following existing implementation plan (impl.md) based on the provided modification instructions. Also consider the latest project concept (idea.md) for context.

**Latest Project Concept (idea.md):**
```markdown
{idea_content}
```

**Existing Implementation Plan (impl.md):**
```markdown
{existing_impl_content}
```

**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze the existing plan, the latest concept, and the modification instructions.**
2.  **Integrate the requested changes thoughtfully into the implementation plan.** This might involve adding/removing components, changing technology stack, updating module definitions, modifying project structure, etc.
3.  **Ensure the updated plan remains consistent** with the latest project concept (idea.md).
4.  **Maintain the overall Markdown structure** of the implementation plan (headings, lists, Mermaid diagrams if used, etc.).
5.  **Output the complete, updated implementation plan.** Do not just output the changes. The output should be the full `impl.md` file ready to be saved.
6.  **Format the entire output strictly as Markdown.** Do not include any introductory or concluding remarks like "Here is the updated plan:".

**Generate the complete, refined implementation plan (impl.md) below:**
"""
        return prompt