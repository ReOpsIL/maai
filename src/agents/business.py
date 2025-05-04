import os
from .base_agent import BaseAgent

class BusinessAgent(BaseAgent):
    """
    Pros and Cons a simple user idea in business perspective.
    """

    def run(self):
        """
        Executes the Business agent's task: creating the business.md file.

        """
        self.logger.info(f"Running Business Agent for project: {self.project_name})")

        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            # Or raise a specific exception
            raise RuntimeError("BusinessAgent requires a configured Generative Model.")

        idea_md_path = os.path.join(self.docs_path, "idea.md")
        if not os.path.exists(idea_md_path):
            raise Exception("idea.md file does not exists")

        idea_text = self._read_file(idea_md_path)

        business_md_path = os.path.join(self.docs_path, "business.md")

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
        content_prefix = f"# Project **{self.project_name}** business perspective:\n\n"
        final_content_to_write = content_prefix + generated_output
        write_action = "wrote"

        try:
            self._write_file(business_md_path, final_content_to_write)
            self.logger.info(f"Successfully {write_action} {business_md_path}")
        except Exception as e:
            # Error already logged by _write_file
            raise IOError(f"Failed to write business.md for project {self.project_name}: {e}")

        return business_md_path

    def _create_prompt(self, idea_text: str) -> str: # For initial creation
        """Creates the prompt for the generative AI model."""
        prompt = f"""

        Analyze the following startup idea from a comprehensive business perspective. Evaluate its strengths (Pros) and weaknesses (Cons) to help assess its viability and potential for success.

        **Your Startup Idea:
        ```markdown
        {idea_text}
        ```

        **Analysis Structure:**
        Please structure your evaluation using the following categories, detailing both the potential upsides (Strengths/Pros) and downsides (Weaknesses/Cons) for each where applicable:

        **Market Opportunity & Need:**
        Pros: Evidence of market need? Size of the potential market (TAM/SAM/SOM)? Growing or declining market? Specific underserved niche? Potential for disruption?
        Cons: Is the problem significant enough for people to pay for a solution? Is the market already saturated? Strong incumbent competitors? Difficulty reaching the target audience?

        **Value Proposition & Differentiation:**
        Pros: How unique is the solution? What makes it clearly better (faster, cheaper, more effective) than existing alternatives (including inaction)? Strong competitive advantage (technology, network effects, IP, brand)?
        Cons: Is the value proposition clear and easily understood? Is the differentiation sustainable? Risk of being easily copied? Are alternatives "good enough"?

        **Monetization Strategy & Potential:**
        Pros: Clear path(s) to revenue (e.g., subscription, transaction fees, freemium, advertising, licensing)? High potential lifetime value (LTV)? Strong pricing power? Multiple potential revenue streams?
        Cons: Difficulty in getting customers to pay? High customer acquisition cost (CAC) relative to LTV? Reliance on a single, unproven revenue stream? Price sensitivity of the target market?

        **Required Investment & Financials:**
        Pros: Low initial capital requirement (bootstrappable)? Potential for high margins? Clear path to profitability? Attractive to investors?
        Cons: High upfront investment needed (R&D, inventory, infrastructure)? Long path to profitability? High ongoing operational costs? Funding challenges?

        **Technical Feasibility & Challenges:**
        Pros: Utilizes existing, proven technology? Simple to build/implement? Few technical dependencies?
        Cons: Relies on unproven or cutting-edge technology? Significant R&D required? Complex integration challenges? Potential for high technical debt? Scarcity of required technical talent?

        **Scalability & Growth Potential:**
        Pros: Easily scalable business model (e.g., software, digital platform)? Potential for rapid user/customer growth? Network effects that accelerate growth? Ability to expand geographically or into adjacent markets?
        Cons: Difficult or expensive to scale operations? Reliance on manual processes? Geographic or regulatory limitations to growth? Infrastructure bottlenecks?

        **Team & Execution:**
        (Assume a hypothetical capable team if you don't have one yet, but note if specific expertise is critical)
        Pros: Idea aligns with common team strengths? Relatively straightforward execution plan?
        Cons: Requires highly specialized or rare expertise? Complex operational hurdles (logistics, regulation, partnerships)? High execution risk?

        **Key Risks & Barriers to Entry:**
        Pros: High barriers to entry for competitors (once established)? Defensible intellectual property? Strong network effects lock-in users?
        Cons: Low barriers to entry (easy for others to copy)? Significant regulatory hurdles? High dependence on key partners/platforms? Market timing risk (too early/too late)? Reputational risks?

        **Overall Conclusion:**
        Based on the analysis above, provide a brief summary statement on the overall viability and attractiveness of this startup idea from a business perspective. Highlight the most critical factors (positive and negative) that would influence a decision to pursue it.

        """
        return prompt
