import os
from .base_agent import BaseAgent

class ScoringAgent(BaseAgent):
    """
    Scoring agent for business Pros and Cons.
    """

    def run(self):
        """
        Executes the Scoring agent's task: creating the score.md file.

        """
        self.logger.info(f"Running Scoring Agent for project: {self.project_name})")

        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            # Or raise a specific exception
            raise RuntimeError("ScoringAgent requires a configured Generative Model.")

        business_md_path = os.path.join(self.docs_path, "business.md")
        if not os.path.exists(business_md_path):
            raise Exception("idea.md file does not exists")

        business_text = self._read_file(business_md_path)

        scoring_md_path = os.path.join(self.docs_path, "scoring.md")

        # Create mode
        prompt = self._create_prompt(business_text)
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
        content_prefix = f"# Project {self.project_name} scoring for business: {self.project_name}\n\n"
        final_content_to_write = content_prefix + generated_output
        write_action = "wrote"

        try:
            self._write_file(scoring_md_path, final_content_to_write)
            self.logger.info(f"Successfully {write_action} {scoring_md_path}")
        except Exception as e:
            # Error already logged by _write_file
            raise IOError(f"Failed to write scoring.md for project {self.project_name}: {e}")

        return scoring_md_path

    def _create_prompt(self, business_text: str) -> str:
        """Creates the prompt for the generative AI model."""
        prompt = f"""

        Please analyze the following business idea review, which is structured into categories with Pros and Cons. Your task is to generate a quantitative score reflecting the idea's viability based on this analysis.

        Follow these steps:

        1.  **Read the entire analysis carefully**, including the introduction and conclusion, to understand the overall context and the analyst's sentiment.
        2.  **For each numbered category listed below, assign a Category Score from 1 to 10.** Base this score on the balance and significance of the Pros versus the Cons presented within that specific category.
            *   **Scoring Guide:**
                *   1-3: Very Weak / High Risk (Cons heavily outweigh Pros)
                *   4-5: Weak / Moderate Risk (Cons outweigh Pros)
                *   6: Neutral / Slightly Positive (Balanced, or minor Pros edge out Cons)
                *   7-8: Strong / Moderate Opportunity (Pros clearly outweigh Cons)
                *   9-10: Very Strong / High Opportunity (Compelling Pros, minimal Cons)
        3.  **Use the following categories and weights:**
            *   1. Market Opportunity & Need: Weight = 20%
            *   2. Value Proposition & Differentiation: Weight = 20%
            *   3. Monetization Strategy & Potential: Weight = 15%
            *   4. Required Investment & Financials: Weight = 10%
            *   5. Technical Feasibility & Challenges: Weight = 10%
            *   6. Scalability & Growth Potential: Weight = 10%
            *   7. Team & Execution: Weight = 5%
            *   8. Key Risks & Barriers to Entry: Weight = 10%
            *   *(If a category is missing from the input text, note it and exclude it from the calculation, adjusting the weights of the remaining categories proportionally if possible, or assign a neutral score of 6).*
        4.  **Calculate the Weighted Score for each category:** `Category Score * Category Weight`
        5.  **Calculate the Overall Viability Score:** Sum all Weighted Scores and divide the total by 10. The result should be a score between 1 and 10.
        6.  **Output the results clearly.** Include:
            *   The Category Score (1-10) for each category.
            *   A brief justification (1 sentence) for each Category Score, referencing the key Pros/Cons.
            *   The final Overall Viability Score (rounded to two decimal places).

        **Business Idea Review Text:**

        {business_text}
        """
        return prompt
