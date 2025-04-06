import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from .base_agent import BaseAgent

class MarketAnalystAgent(BaseAgent):
    """
    Analyzes the project concept (idea.md) for market potential,
    competitive landscape, and business viability.
    """

    def run(self, modification_text: str | None = None, update_mode: bool = False) -> str:
        """
        Executes the Market Analyst agent's task: generating or updating market_analysis.md.

        Args:
            modification_text: Specific instructions for modifying existing analysis
                               (used when update_mode is True).
            update_mode: If True, read existing analysis and update based on context/instructions.
                         If False, generate new analysis based on idea.md.

        Returns:
            The absolute path to the generated or updated market_analysis.md file.
        """
        self.logger.info(f"Running Market Analyst Agent for project: {self.project_name} (Update Mode: {update_mode})")
        if update_mode and not modification_text:
             raise ValueError("Modification text is required when running Market Analyst in update mode.")
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
        if update_mode:
             self.logger.info(f"Reading existing market analysis: {analysis_md_path}")
             existing_analysis_content = self._read_file(analysis_md_path)
             if existing_analysis_content is None:
                  self.logger.warning(f"Existing analysis file not found at {analysis_md_path}. Will generate new analysis based on instructions.")
                  # Proceed, effectively generating based on instructions + idea context.

        self.logger.info("Attempting to generate or update market analysis using AI.")
        try:
            if update_mode and existing_analysis_content:
                 prompt = self._create_update_analysis_prompt(idea_content, existing_analysis_content, modification_text)
                 self.logger.debug(f"Generated update analysis prompt for Gemini:\n{prompt[:500]}...")
            else:
                 # Create mode or update mode where existing file was missing
                 prompt = self._create_analysis_prompt(idea_content)
                 self.logger.debug(f"Generated create analysis prompt for Gemini:\n{prompt[:500]}...")

            response = self.model.generate_content(prompt)
            generated_analysis = response.text # This is the full new/updated analysis
            log_action = "updated" if update_mode and existing_analysis_content else "generated"
            self.logger.info(f"Received {log_action} market analysis response from Gemini API.")
            self.logger.debug(f"Generated Analysis (first 200 chars):\n{generated_analysis[:200]}...")
        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Market Analyst): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for market analysis: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during analysis generation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate/update market analysis using AI: {e}")

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
    *   Identify 3-5 key existing competitors or alternative solutions (provide names if possible).
    *   Briefly describe their offerings and target audience.
    *   What are their potential strengths and weaknesses compared to this new idea?
    *   What is this idea's unique selling proposition (USP) or key differentiator?

3.  **Business Potential & Monetization:**
    *   Assess the overall business potential (e.g., high, medium, low). Justify your assessment.
    *   Suggest 2-3 potential monetization strategies (e.g., subscription, freemium, one-time purchase, ads, enterprise licenses).
    *   Discuss potential challenges or risks to market entry and success (e.g., technical hurdles, adoption barriers, regulatory issues).

4.  **Innovative Insights & Strategic Recommendations:**
    *   Suggest 1-2 innovative features or strategic pivots that could significantly enhance the idea's market appeal or business value.
    *   Identify potential strategic partnerships that could accelerate growth.
    *   Provide a concluding remark on the idea's overall market viability and potential impact.

**Format the entire output strictly as Markdown.** Use clear headings for each section. Be insightful and provide specific examples where possible. Do not include introductory or concluding remarks outside the specified Markdown structure.
"""
        return prompt

    def _create_update_analysis_prompt(self, idea_content: str, existing_analysis: str, modification_text: str) -> str:
        """Creates the prompt for the generative AI model to update existing market analysis."""
        prompt = f"""
Refine and update the following existing market analysis report (`market_analysis.md`) based on the provided modification instructions. Use the latest project concept (`idea.md`) as primary context.

**Latest Project Concept (idea.md):**
```markdown
{idea_content}
```

**Existing Market Analysis Report (market_analysis.md):**
```markdown
{existing_analysis}
```

**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze all provided context:** the existing analysis, the latest concept, and the modification instructions.
2.  **Integrate the requested changes thoughtfully into the market analysis.** This might involve revising competitor info, adjusting market size estimates, refining monetization strategies, adding new insights based on the instructions, etc.
3.  **Ensure the updated analysis remains consistent** with the latest project concept and provides insightful business/market perspectives.
4.  **Maintain the overall Markdown structure** of the report (headings, lists, etc.).
5.  **Output the complete, updated market analysis report.** Do not just output the changes. The output should be the full `market_analysis.md` file ready to be saved.
6.  **Format the entire output strictly as Markdown.** Do not include any introductory or concluding remarks.

**Generate the complete, refined market analysis report (`market_analysis.md`) below:**
"""
        return prompt