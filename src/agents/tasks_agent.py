import os
from .base_agent import BaseAgent

class TasksAgent(BaseAgent):
    """
    Generate tasks file for project.
    """

    def run(self):
        """
        Executes the Tasks agent's task: creating the tasks.md file.

        """
        self.logger.info(f"Running Tasks Agent for project: {self.project_name})")

        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            # Or raise a specific exception
            raise RuntimeError("TasksAgent requires a configured Generative Model.")

        idea_md_path = os.path.join(self.docs_path, "idea.md")
        if not os.path.exists(idea_md_path):
            raise Exception("idea.md file does not exists")

        idea_text = self._read_file(idea_md_path)

        tasks_md_path = os.path.join(self.docs_path, "tasks.md")

        # Create mode
        prompt = self._create_prompt(idea_text)
        self.logger.debug(f"Generated create prompt for:\n{prompt[:500]}...")

        try:
            self.logger.info("Sending request to LLM API...")
            generated_output = self.model.generate_content(prompt)
            self.logger.info("Received response from LLM API.")
            self.logger.debug(f"Generated Output (first 200 chars):\n{generated_output[:200]}...")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during API call: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate concept using AI: {e}")

        # Determine content to write

        # Create mode - add prefix
        content_prefix = f"# Project **{self.project_name}** tasks perspective:\n\n"
        final_content_to_write = content_prefix + generated_output
        write_action = "wrote"

        try:
            self._write_file(tasks_md_path, final_content_to_write)
            self.logger.info(f"Successfully {write_action} {tasks_md_path}")
        except Exception as e:
            # Error already logged by _write_file
            raise IOError(f"Failed to write tasks.md for project {self.project_name}: {e}")

        return tasks_md_path

    def _create_prompt(self, idea_text: str) -> str: 
        """Creates the prompt for the generative AI model."""
        prompt = f"""
        Act as a project planner. Take the provided project idea document and convert it into a comprehensive Markdown task list suitable for tracking development progress.

        Instructions:
        1.  **Format:** Use standard Markdown checklists (`[ ] Task description` or `[x] Task description` for completed items if specified).
        2.  **Source Sections:** Primarily extract tasks from sections like 'Key Features', 'Potential Enhancements / Future Ideas', and 'High-Level Technical Considerations'. Also review 'Expanded Concept', 'Target Users', and 'User Stories' to ensure core requirements and goals are translated into actionable tasks.
        3.  **Granularity:** Break down larger features or technical considerations into smaller, actionable tasks where appropriate. Aim for tasks that represent a manageable unit of work.
        4.  **Categorization:** Organize the tasks into logical sections. Adapt the categories based on the project type. General suggestions include:
            *   Foundational Setup / Project Initialization
            *   Core Functionality / Algorithm Development
            *   Data Handling & Integration (e.g., APIs, Databases, External Systems like PACS/EHR)
            *   Backend / Server-Side Tasks
            *   Frontend / User Interface / Client Application Tasks (if applicable)
            *   Infrastructure / Deployment / Operations
            *   Testing / Validation / Quality Assurance
            *   Regulatory / Compliance (Especially important for specific domains like medical)
            *   Documentation
            *   Potential Enhancements / Future Work
        5.  **Domain Specificity:** Pay close attention to domain-specific requirements, standards, technologies, or regulations mentioned (e.g., medical standards like DICOM, FDA regulations, specific hardware, financial compliance, specific APIs) and create relevant tasks.
        6.  **Include Implicit Tasks:** Add standard software development tasks that might not be explicitly listed but are necessary, such as:
            *   Detailed requirements gathering/refinement
            *   Architecture design
            *   Environment setup (Dev, Test, Prod)
            *   Database schema design/migration planning
            *   UI/UX design and prototyping (if applicable)
            *   Security planning and implementation
            *   Testing strategy definition (Unit, Integration, E2E, Performance, Security, UAT)
            *   Deployment strategy and automation
            *   Monitoring and logging setup
        7.  **Label Enhancements:** Clearly mark tasks derived from the 'Enhancements' or 'Future Ideas' section (e.g., using `[Enhancement]` prefix).
        8.  **Maintain Context:** Ensure the tasks reflect the overall goals and target users described in the document.

        Here is the project idea document:
        
         ```markdown
        {idea_text}
        ```
        
        """
        
        return prompt
