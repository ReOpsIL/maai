import os


from .base_agent import BaseAgent

class InnovatorAgent(BaseAgent):
    """
    Expands a simple user idea into a more detailed concept using a Generative AI model.
    """

    def run(self, idea_text: str, wild_mode: bool):
        """
        Executes the Innovator agent's task: creating the idea.md file.

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
        prompt = self._create_prompt(idea_text, wild_mode=wild_mode)
        self.logger.debug(f"Generated create prompt for LLM:\n{prompt[:500]}...")

        try:
            self.logger.info("Sending request to LLM API...")
            generated_output = self.model.generate_content(prompt)
            self.logger.info("Received response from LLM API.")
            self.logger.debug(f"Generated Output (first 200 chars):\n{generated_output[:200]}...")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM API call: {e}", exc_info=True)
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

    def _improve_idea_prompt(self, idea_path):
        prompt = f"""Please review the project proposal and the associated business plan,
        including the current scoring. I would like you to enhance the idea to make the business
        opportunity more compelling. As you do so, recalculate the score after each iteration while
        critically evaluating the proposal.
        Repeat this process multiple times to maximize the final score.
        Important: Do not alter the scoring method or formula.
        """
        return ""

    def _create_prompt(self, idea_text: str, wild_mode: bool) -> str: # For initial creation
        """Creates the prompt for the generative AI model."""
        w1 = ""
        w2 = ""
        if wild_mode:
            w1 = """**INNOVATIVE** **FUTURISTIC** **WILD** **IMAGINATIVE**"""
            w2 = """**DONT** generate a project concept based on current market trends or existing products. **BE INNOVATIVE** **THINK OUTSIDE THE BOX** **BE ORIGINAL** **BE UNIQUE**"""

        prompt = f"""
            Expand the following user idea into a detailed {w1} project concept document in Markdown format.
            
            {w2}

            **User Idea:** "{idea_text}"

            * Use appropriate Markdown headers to clearly separate each section (e.g., `## Expanded Concept`).
            * Maintain a professional tone, clear structure, and consistent formatting using bullet points or paragraphs as needed.
            * Be imaginative yet practical—propose features that are technically feasible and aligned with the core concept.
            * If the input idea is vague or underdeveloped, begin by expanding on it to establish a clear understanding before proceeding with the other sections.

            **Generate the following sections in strict Markdown format (no extra intro or conclusion text):**

            1. **Expanded Concept**

            * Elaborate on the core idea. What problem does it address? What is the primary goal or outcome?

            2. **Target Users**

            * Identify and describe the intended user profiles (e.g., roles, skill levels, goals, or needs).

            3. **Key Features**

            * List **5–20 core features** with detailed descriptions. Focus on functionalities that solve real user problems.
            * *Do not* include implementation-level details—explain each feature thoroughly from the user's perspective.

            4. **Potential Enhancements / Future Ideas**

            * Suggest **5–10 advanced or long-term features**, such as integrations, automation, or scalability improvements.
            * Provide detailed explanations for each idea without diving into implementation specifics.

            5. **High-Level Technical Considerations**

            * Outline possible technologies, platforms, or architectures that could support the concept (e.g., backend frameworks, mobile app structures, database types).
            * Keep this section high-level—no code or deep technical breakdowns.

            6. **User Stories (Examples)**

            * Write **5–10 user stories** using this format:
                `As a [type of user], I want to [do something] so that [I achieve a benefit].`

                * Example: `As a returning user, I want to save my settings so that I don’t have to reconfigure them each time.`

        """
        return prompt
