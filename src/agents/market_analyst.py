import os


from .base_agent import BaseAgent

class MarketAnalystAgent(BaseAgent):
    """
    Analyzes the project concept (idea.md) for market potential,
    competitive landscape, and business viability.
    """

    def run(self) -> str:
        """
        Executes the Market Analyst agent's task: generating or updating market_analysis.md.

        Args:
            modification_text: Specific instructions for modifying existing analysis.
            
        Returns:
            The absolute path to the generated or updated market_analysis.md file.
        """
        self.logger.info(f"Running Market Analyst Agent for project: {self.project_name})")
       

        idea_md_path = os.path.join(self.docs_path, "idea.md")
        analysis_md_path = os.path.join(self.docs_path, "market_analysis.md")

        self.logger.info(f"Reading project concept from: {idea_md_path}")
        idea_content = self._read_file(idea_md_path)
        if idea_content is None:
            raise FileNotFoundError(f"Could not read idea.md for project {self.project_name}. Please ensure it exists.")

        # Model initialization is handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("MarketAnalystAgent requires a configured Generative Model.")

        existing_analysis_content = None
        
        self.logger.info("Attempting to generate or update market analysis using AI.")
        try:
            # Create mode where existing file was missing
            prompt = self._create_analysis_prompt(idea_content)
            self.logger.debug(f"Generated create analysis prompt for:\n{prompt[:500]}...")
            generated_analysis = self.model.generate_content(prompt)
            log_action = "generated"
            self.logger.info(f"Received {log_action} market analysis response from LLM API.")
            self.logger.debug(f"Generated Analysis (first 200 chars):\n{generated_analysis[:200]}...")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during analysis generation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate market analysis using AI: {e}")

        self.logger.info(f"Writing market analysis to: {analysis_md_path}")
        try:
            self._write_file(analysis_md_path, generated_analysis)
            self.logger.info(f"Successfully wrote {analysis_md_path}")
        except Exception as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write market_analysis.md for project {self.project_name}: {e}")

        return analysis_md_path

    def _create_analysis_prompt(self, idea_content: str) -> str: # For initial creation
        """Creates the prompt for the generative AI model to perform initial market analysis."""
        prompt = f"""
Analyze the following project concept (provided in Markdown) from a business and market perspective. Provide innovative insights beyond a simple summary.

**Project Concept (from idea.md):**
```markdown
{idea_content}
```

**Generate a Market Analysis Report (`market_analysis.md`) covering the following sections:**

1.  **Target Market & Audience Analysis:**
    *   Identify the primary and secondary target markets.
    *   Estimate the potential market size (e.g., niche, growing, large).
    *   Describe the key characteristics and needs of the target audience in more detail. Are there underserved segments?

2.  **Competitive Landscape:**
    *   Identify 5-10 key existing competitors or alternative solutions (provide names if possible).
    *   Briefly describe their offerings and target audience.
    *   What are their potential strengths and weaknesses compared to this new idea?
    *   What is this idea's unique selling proposition (USP) or key differentiator?

3.  **Business Potential & Monetization:**
    *   Assess the overall business potential (e.g., high, medium, low). Justify your assessment.
    *   Suggest 5-10 potential monetization strategies (e.g., subscription, freemium, one-time purchase, ads, enterprise licenses).
    *   Discuss potential challenges or risks to market entry and success (e.g., technical hurdles, adoption barriers, regulatory issues).

4.  **Innovative Insights & Strategic Recommendations:**
    *   Suggest 5-10 innovative features or strategic pivots that could significantly enhance the idea's market appeal or business value.
    *   Identify potential strategic partnerships that could accelerate growth.
    *   Provide a concluding remark on the idea's overall market viability and potential impact.

**Format the entire output strictly as Markdown.** Use clear headings for each section. Be insightful and provide specific examples where possible. Do not include introductory or concluding remarks outside the specified Markdown structure.
"""
        return prompt
