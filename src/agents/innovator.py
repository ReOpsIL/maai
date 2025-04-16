import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from .base_agent import BaseAgent

class InnovatorAgent(BaseAgent):
    """
    Expands a simple user idea into a more detailed concept using a Generative AI model.
    """

    def run(self, idea_text: str):
        """
        Executes the Innovator agent's task: creating or updating the idea.md file.

        Args:
            idea_text: The initial idea text.
            modification_text: Instructions on how to modify the existing idea.
        """
        self.logger.info(f"Running Innovator Agent for project: {self.project_name})")
       
        if not idea_text:
            raise ValueError("Initial idea text is required")
        self.logger.info(f"Received initial idea: '{idea_text[:100]}...'")

        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            # Or raise a specific exception
            raise RuntimeError("InnovatorAgent requires a configured Generative Model.")

        idea_md_path = os.path.join(self.docs_path, "idea.md")

        # Create mode
        prompt = self._create_prompt(idea_text)
        self.logger.debug(f"Generated create prompt for Gemini:\n{prompt[:500]}...")

        try:
            self.logger.info("Sending request to Gemini API...")
            generated_output = self.model.generate_content(prompt)
            self.logger.info("Received response from Gemini API.")
            self.logger.debug(f"Generated Output (first 200 chars):\n{generated_output[:200]}...")
        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error: {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Gemini API call: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate concept using AI: {e}")

        # Determine content to write
        
        # Create mode - add prefix
        content_prefix = f"# Project Idea: {self.project_name}\n\n## Initial Concept\n\n"
        final_content_to_write = content_prefix + generated_output
        write_action = "wrote"

        try:
            self._write_file(idea_md_path, final_content_to_write)
            self.logger.info(f"Successfully {write_action} {idea_md_path}")
        except Exception as e:
            # Error already logged by _write_file
            raise IOError(f"Failed to write idea.md for project {self.project_name}: {e}")

        return idea_md_path

    def _create_prompt(self, idea_text: str) -> str: # For initial creation
        """Creates the prompt for the generative AI model."""
        prompt = f"""
            Expand the following user idea into a detailed project concept document in Markdown format.

            **User Idea:** "{idea_text}"

            **Instructions:**
            - Ensure each section is clearly marked using appropriate Markdown headers (e.g., `## Expanded Concept`).
            - Maintain professional tone, clear formatting, and structured bullets or paragraphs as needed.
            - Be creative but grounded—suggest features that are technically possible and aligned with the concept.
            - If the idea is vague or minimal, first expand it to ensure understanding before moving into the sections.

            **Generate the following sections:**

            1. **Expanded Concept**
            - Elaborate on the core idea. What problem does it solve? What is the primary goal?

            2. **Target Users**
            - Who would use this? Describe the ideal user profile(s) (e.g., roles, skills, needs).

            3. **Key Features**
            - List 5–20 core features with brief descriptions. Use bullet points. Focus on functions that address real user needs.

            4. **Potential Enhancements / Future Ideas**
            - Suggest 5–10 advanced features or long-term extensions. These can include integrations, automation, or expansion.

            5. **High-Level Technical Considerations**
            - Mention potential technologies, platforms, or architectures (e.g., Python + Flask for backend, mobile app with local DB, etc.). Keep high-level without diving into implementation.

            6. **User Stories (Examples)**
            - Write 5–10 user stories in the format:
                `As a [type of user], I want to [do something] so that [I get a benefit].`
                - Example: `As a returning user, I want to save my settings so that I don’t have to reconfigure them each time.`

            **Format the entire output strictly as Markdown.**
            Do not include any introductory or concluding text outside of the Markdown structure.
        """
        return prompt

    def _create_prompt_old(self, idea_text: str) -> str: # For initial creation
        """Creates the prompt for the generative AI model."""
        # Improved prompt for more structured output
        prompt = f"""
Expand the following user idea into a detailed project concept document in Markdown format.

**User Idea:** "{idea_text}"

**Generate the following sections:**

1.  **Expanded Concept:** Elaborate on the core idea. What problem does it solve? What is the primary goal?
2.  **Target Users:** Who would use this? Describe the ideal user profile(s).
3.  **Key Features:** List 5-20 core features with brief descriptions. Think creatively about potential functionalities.
4.  **Potential Enhancements / Future Ideas:** Suggest 5-10 advanced features or future directions for the project.
5.  **High-Level Technical Considerations:** Briefly mention potential technologies, platforms, or architectural approaches (e.g., CLI app, web service, database needs, language considerations like Python). Keep it high-level.
6.  **User Stories (Examples):** Write 5-10 example user stories in the format "As a [type of user], I want [an action] so that [a benefit]."

**Format the entire output strictly as Markdown.** Do not include any introductory or concluding remarks outside of the Markdown structure.
"""
        return prompt

    def _create_update_prompt(self, existing_content: str, modification_text: str) -> str:
        """Creates the prompt for the generative AI model to update an existing idea.md."""
        prompt = f"""
Refine and update the following existing project concept document (in Markdown format) based on the provided modification instructions.

**Existing Project Concept (idea.md):**
```markdown
{existing_content}
```

**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze the existing concept and the modification instructions.**
2.  **Integrate the requested changes thoughtfully.** This might involve adding new sections, removing obsolete parts, rewriting existing sections, or adjusting features/details.
3.  **Maintain the overall Markdown structure** of the document (headings, lists, etc.). Ensure consistency.
4.  **Output the complete, updated project concept document.** Do not just output the changes. The output should be the full `idea.md` file ready to be saved.
5.  **Format the entire output strictly as Markdown.** Do not include any introductory or concluding remarks like "Here is the updated document:".

**Generate the complete, refined Markdown document below:**
"""
        return prompt
