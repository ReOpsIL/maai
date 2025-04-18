import os
from .base_agent import BaseAgent

class IdeaGenAgent(BaseAgent):
    """
    Pros and Cons a simple user idea in business perspective.
    """

    def run(self, idea_subject_text: str, subject_name: str, num_ideas: int):
        """
        Executes the IdeaGenAgent  task: creating the subject_name.json file.

        """
        self.logger.info(f"Running IdeaGenAgent for project: {self.project_name})")

        if not idea_subject_text:
            raise ValueError("Initial idea text is required")
        self.logger.info(f"Received initial idea: '{idea_subject_text[:100]}...'")


        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            # Or raise a specific exception
            raise RuntimeError("IdeaGenAgent requires a configured Generative Model.")


        ideas_list_path = os.path.join(self.docs_path, f"{subject_name}.json")

        # Create mode
        prompt = self._create_prompt(idea_subject_text, num_ideas)
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
        final_content_to_write = generated_output
        write_action = "wrote"

        try:
            self._write_file(ideas_list_path, final_content_to_write)
            self.logger.info(f"Successfully {write_action} {ideas_list_path}")
        except Exception as e:
            # Error already logged by _write_file
            raise IOError(f"Failed to write {subject_name}.json for project {self.project_name}: {e}")

        return ideas_list_path

    def _create_prompt(self, idea_subject_text: str, num_ideas: int) -> str:
        """Creates the prompt for the generative AI model to generate structured startup ideas."""
        prompt = f"""
        Generate a diverse list of {num_ideas} innovative startup ideas that leverage AI, machine learning,
        or other advanced technologies to solve problems or **CREATE NEW OPPORTUNITIES** in the field of:

        **{idea_subject_text}**

        **DONT** generate a projects concept based on current market trends or existing products.
        **BE INNOVATIVE** **FUTURISTIC** **THINK OUTSIDE THE BOX** **BE ORIGINAL** **BE UNIQUE**

        Each idea must be:
        - Feasible for a solo founder or a small team.
        - Clearly categorized (e.g., "Healthcare", "Education", "HR and Recruitment", etc.).
        - Accompanied by a concise description covering:
        - Core concept
        - Key features
        - Potential benefits
        - Target audience

        Ensure the ideas represent a variety of use cases within the **{idea_subject_text}** domain.

        Return only the following JSON structure—no comments, markdown, or extra text:

        {{
        "startup_ideas": [
            {{
            "id": 1,
            "category": "Virtual Assistance",
            "title": "AI-powered virtual event planning assistant",
            "description": "Develop an AI-powered assistant that helps plan and manage events such as conferences, weddings, and parties. It suggests venues, caterers, and entertainment options based on user preferences and budget."
            }},
            {{
            "id": 2,
            "category": "Travel",
            "title": "Personalized virtual travel planning assistant",
            "description": "Create a travel assistant that uses AI to build custom itineraries based on user interests, travel history, and budget. It can also handle bookings for flights, hotels, and activities."
            }},
            ...
            {{
            "id": {num_ideas},
            "category": "HR and Recruitment",
            "title": "AI-based employee onboarding and training",
            "description": "Build a platform that provides AI-driven onboarding and training, offering personalized learning paths and performance tracking for new employees."
            }}
        ]
        }}
        """
        return prompt.strip()
