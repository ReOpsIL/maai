import os
import re # Added for parsing
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    """
    Analyzes the project concept (idea.md) and generates detailed implementation
    plans for each major component (impl_[component].md) and an integration
    plan (integ.md).
    """

    def run(self, modification_text: str | None = None, update_mode: bool = False) -> list[str]:
        """
        Executes the Architect agent's task: creating or updating component-specific
        implementation plans (impl_*.md) and an integration plan (integ.md).

        Args:
            modification_text: Instructions on how to modify the existing plans
                               (used when update_mode is True).
            update_mode: If True, use modification_text and potentially updated
                         idea.md to regenerate plans. The previous impl.md might be
                         read for context by _generate_or_update_plan.
                         If False, create new plans based on idea.md.

        Returns:
            A list of paths to the generated/updated markdown files.

        Raises:
            FileNotFoundError: If idea.md cannot be read.
            RuntimeError: If AI generation fails or parsing fails.
            IOError: If writing output files fails.
        """
        self.logger.info(f"Running Architect Agent for project: {self.project_name} (Update Mode: {update_mode})")
        idea_md_path = os.path.join(self.docs_path, "idea.md")
        # Define potential path for old impl.md (used for context in update mode)
        old_impl_md_path = os.path.join(self.docs_path, "impl.md")

        self.logger.info(f"Reading concept from: {idea_md_path}")
        idea_content = self._read_file(idea_md_path)
        if idea_content is None:
            raise FileNotFoundError(f"Could not read idea.md for project {self.project_name}. Please ensure it exists.")

        self.logger.info("Attempting to generate or update implementation plan using AI.")
        try:
            # Generate the combined plan string from AI
            combined_plan_output = self._generate_or_update_plan(
                idea_content=idea_content,
                modification_text=modification_text,
                update_mode=update_mode,
                old_impl_md_path=old_impl_md_path # Pass path for reading context
            )
            self.logger.info("Successfully generated/updated implementation plan using AI.")
        except (FileNotFoundError, ValueError, ConnectionError, RuntimeError) as e: # Added FileNotFoundError
            self.logger.error(f"Failed to generate/update implementation plan using AI: {e}")
            raise RuntimeError(f"Architect Agent failed: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during plan generation/update: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Architect Agent: {e}")
        self.logger.info("Parsing generated plan into component and integration files.")
        try:
            # Parse the combined output and write individual files
            generated_files = self._parse_and_write_plans(combined_plan_output)
            self.logger.info(f"Successfully created/updated implementation files: {generated_files}")
        except ValueError as e:
            self.logger.error(f"Failed to parse AI response: {e}", exc_info=True)
            raise RuntimeError(f"Architect Agent failed during parsing: {e}")
        except IOError as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write implementation files for project {self.project_name}: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during plan writing: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Architect Agent during writing: {e}")

        return generated_files

    def _generate_or_update_plan(self, idea_content: str, modification_text: str | None, update_mode: bool, old_impl_md_path: str) -> str:
        """
        Uses Generative AI to create or update the implementation plan string.
        In update mode, it reads the old impl.md for context if it exists.
        """
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("ArchitectAgent requires a configured Generative Model.")

        existing_impl_content = None
        if update_mode:
            if not modification_text:
                 raise ValueError("Modification text is required when running Architect in update mode.")
            self.logger.info(f"Attempting to read previous implementation plan for context: {old_impl_md_path}")
            # Read the old impl.md for context, but don't fail if it doesn't exist
            existing_impl_content = self._read_file(old_impl_md_path, optional=True)
            if existing_impl_content:
                 self.logger.info(f"Using content from {old_impl_md_path} as context for update.")
            else:
                 self.logger.warning(f"Previous plan {old_impl_md_path} not found or empty. Updating based on idea and modifications only.")
            prompt = self._create_update_prompt(existing_impl_content, modification_text, idea_content) # Pass content (or None)
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
Analyze the following project concept (provided in Markdown) and generate a set of detailed implementation plans, one for each major component, and a separate integration plan. These plans must be highly detailed to guide a Coder Agent.

**Project Concept (from idea.md):**
```markdown
{idea_content}
```

**Instructions:**

1.  **Identify Major Components:** Based on the concept, identify the distinct major components of the system (e.g., backend, frontend, database, deployment, external_service_integration, etc.). Use simple, lowercase names for components (e.g., `backend`, `frontend`).
2.  **Generate Component Implementation Plans:** For EACH major component identified, generate a detailed implementation plan in Markdown format. Each plan should cover:
    *   **Technology Stack:** Specific technologies, libraries, frameworks, and versions for this component.
    *   **Project Structure:** Detailed directory and file structure within the component's sub-directory (e.g., `backend/src/...`, `frontend/src/...`). List key files and their purpose.
    *   **Core Modules/Classes/Functions:** Define the main code structures. Specify purpose, key methods/functions (with parameters, return types, type hints), and important attributes/data. Be very specific.
    *   **Data Structures:** Detail significant data structures internal to this component or passed immediately to/from it.
    *   **API Definitions (if applicable):** If this component provides or consumes an API, define the endpoints, request/response formats, and authentication details relevant *to this component*.
    *   **Error Handling:** Specific error handling strategies within this component.
    *   **Testing Strategy:** Specific unit and integration tests for this component. Suggest relevant libraries (`pytest`, `jest`, etc.).
    *   **Setup/Run Instructions:** Basic steps to set up and run this component independently, if possible.
3.  **Generate Integration Plan:** Create a separate integration plan (`integ.md`) in Markdown format that describes:
    *   **Overall Architecture Diagram/Description:** A high-level overview of how all components fit together. Use a textual description or simple diagram (like ASCII art, avoid Mermaid).
    *   **Communication Flow:** Describe the sequence of interactions between components for key use cases. Detail the protocols (e.g., REST API calls, message queues, database queries), data formats, and authentication methods used *between* components.
    *   **Shared Data Structures:** Define data structures used for communication *between* components.
    *   **Cross-Cutting Concerns:** Address aspects like authentication, logging, and configuration management across components.
    *   **Deployment Overview:** Briefly outline how the components will be deployed together (e.g., Docker Compose, Kubernetes).
4.  **Format Output:** Structure the entire output clearly using the following delimiters. **Crucially, place each component's plan and the integration plan between these delimiters.**

    ```
    <<<COMPONENT: [component_name_1]>>>
    # Implementation Plan: [Component Name 1]
    (Detailed Markdown plan for component 1...)

    <<<COMPONENT: [component_name_2]>>>
    # Implementation Plan: [Component Name 2]
    (Detailed Markdown plan for component 2...)

    <<<COMPONENT: [component_name_n]>>>
    # Implementation Plan: [Component Name N]
    (Detailed Markdown plan for component n...)

    <<<INTEGRATION>>>
    # Integration Plan
    (Detailed Markdown plan for integration...)
    ```

    *   Replace `[component_name_1]`, `[component_name_2]`, etc., with the actual lowercase names you identified (e.g., `backend`, `frontend`).
    *   Ensure the content within each delimited section is valid Markdown.
    *   Do not include any text before the first delimiter or after the last plan.

**Output the complete response containing all delimited sections.**
"""
        return prompt

    def _parse_and_write_plans(self, combined_output: str) -> list[str]:
        """
        Parses the AI's combined output string based on delimiters and writes
        individual component and integration markdown files.

        Args:
            combined_output: The raw string response from the AI model.

        Returns:
            A list of paths to the files written.

        Raises:
            ValueError: If parsing fails (e.g., delimiters not found).
            IOError: If writing files fails.
        """
        # Updated regex to capture content until the next delimiter or end of string
        component_pattern = re.compile(r"<<<COMPONENT:\s*(.*?)>>>\s*(.*?)(?=\s*<<<|\Z)", re.DOTALL | re.IGNORECASE)
        integration_pattern = re.compile(r"<<<INTEGRATION>>>(.*)", re.DOTALL | re.IGNORECASE)

        components = component_pattern.findall(combined_output)
        integration_match = integration_pattern.search(combined_output)

        if not components and not integration_match:
            raise ValueError("Could not find any <<<COMPONENT: ...>>> or <<<INTEGRATION>>> delimiters in the AI output.")

        written_files = []

        # Write component files
        for name, content in components:
            component_name = name.strip().lower().replace(" ", "_")
            if not component_name:
                self.logger.warning("Found component block with empty name, skipping.")
                continue
            file_name = f"impl_{component_name}.md"
            file_path = os.path.join(self.docs_path, file_name)
            self.logger.info(f"Writing component plan to: {file_path}")
            plan_content = content.strip()
            # Add a header if the AI didn't include one (optional, but good practice)
            if not plan_content.startswith("#"):
                 plan_content = f"# Implementation Plan: {component_name.capitalize()}\n\n{plan_content}"
            self._write_file(file_path, plan_content) # Raises IOError on failure
            written_files.append(file_path)

        # Write integration file
        if integration_match:
            file_name = "integ.md"
            file_path = os.path.join(self.docs_path, file_name)
            self.logger.info(f"Writing integration plan to: {file_path}")
            plan_content = integration_match.group(1).strip()
             # Add a header if the AI didn't include one
            if not plan_content.startswith("#"):
                 plan_content = f"# Integration Plan\n\n{plan_content}"
            self._write_file(file_path, plan_content) # Raises IOError on failure
            written_files.append(file_path)
        else:
            self.logger.warning("No <<<INTEGRATION>>> section found in the AI output.")

        if not written_files:
             raise ValueError("Parsing completed, but no valid component or integration plans were extracted to write.")

        return written_files

    def _create_update_prompt(self, existing_impl_content: str | None, modification_text: str, idea_content: str) -> str:
        """
        Creates the prompt for the generative AI model to update implementation plans.
        Note: This currently regenerates all plans based on the idea and modifications,
        using the old impl.md (if available) only as context for the previous state.
        A future improvement could involve reading and updating individual component files.
        """
        existing_plan_section = ""
        if existing_impl_content:
            existing_plan_section = f"""
**Previous Implementation Plan (impl.md - for context only):**
```markdown
{existing_impl_content}
```
"""

        prompt = f"""
Update and regenerate the implementation plans based on the provided modification instructions, the latest project concept, and the context from the previous plan (if provided). The output must follow the multi-component structure detailed below.

**Latest Project Concept (idea.md):**
```markdown
{idea_content}
```
{existing_plan_section}
**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze the latest concept, the modification instructions, and the previous plan context (if available).**
2.  **Identify the major components** required for the *updated* system (e.g., backend, frontend, database, deployment). Use simple, lowercase names.
3.  **Generate Updated Component Plans:** For EACH major component, generate a *complete and detailed* implementation plan reflecting the requested modifications and the latest concept. Follow the detailed structure specified below for component plans.
4.  **Generate Updated Integration Plan:** Create a *complete and detailed* integration plan (`integ.md`) reflecting the updated architecture and interactions. Follow the detailed structure specified below for the integration plan.
5.  **Output Format:** Structure the entire output using the delimiters `<<<COMPONENT: [component_name]>>>` for each component plan and `<<<INTEGRATION>>>` for the integration plan, exactly as specified in the initial creation instructions. Ensure the content within each section is valid Markdown.

**Component Plan Structure (Repeat for each component):**
*   Technology Stack
*   Project Structure (Detailed)
*   Core Modules/Classes/Functions (Detailed: purpose, methods/params/returns/types, attributes)
*   Data Structures
*   API Definitions (if applicable)
*   Error Handling
*   Testing Strategy
*   Setup/Run Instructions

**Integration Plan Structure:**
*   Overall Architecture Diagram/Description (Textual/ASCII)
*   Communication Flow (Protocols, Data Formats, Auth between components)
*   Shared Data Structures (Between components)
*   Cross-Cutting Concerns (Auth, Logging, Config)
*   Deployment Overview

**Output the complete response containing all delimited sections for the updated plans.** Do not include any introductory text or text after the final plan.
"""
        return prompt