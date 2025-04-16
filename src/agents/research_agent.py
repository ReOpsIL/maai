import os

from google.api_core import exceptions as google_exceptions
from .base_agent import BaseAgent

class ResearchAgent(BaseAgent):
    """
    Performs research based on the project concept (idea.md) to find relevant
    technologies, implementation strategies, and architectural patterns, summarizing findings.
    Leverages the LLM's knowledge base which includes web data.
    """

    def run(self) -> str:
        """
        Executes the Research agent's task. Reads idea.md and generates research_summary.md.

        Returns:
            The absolute path to the generated research_summary.md file.
        """
        self.logger.info(f"Running Research Agent for project: {self.project_name}")

        idea_md_path = os.path.join(self.docs_path, "idea.md")
        research_summary_path = os.path.join(self.docs_path, "research_summary.md")

        self.logger.info(f"Reading project concept from: {idea_md_path}")
        idea_content = self._read_file(idea_md_path)
        if idea_content is None:
            raise FileNotFoundError(f"Could not read idea.md for project {self.project_name}. Please ensure it exists.")

        # Model initialization is handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("ResearchAgent requires a configured Generative Model.")

        self.logger.info("Attempting to perform research and generate summary using AI.")
        try:
            prompt = self._create_research_prompt(idea_content)
            self.logger.debug(f"Generated research prompt for Gemini:\n{prompt[:500]}...")
            research_summary = self.model.generate_content(prompt)
            self.logger.info("Received research summary response from Gemini API.")
            self.logger.debug(f"Generated Research Summary (first 200 chars):\n{research_summary[:200]}...")

        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Research Agent): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for research summary: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during research generation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate research summary using AI: {e}")

        self.logger.info(f"Writing research summary to: {research_summary_path}")
        try:
            self._write_file(research_summary_path, research_summary)
            self.logger.info(f"Successfully wrote {research_summary_path}")
        except Exception as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write research_summary.md for project {self.project_name}: {e}")

        return research_summary_path

    def _create_research_prompt(self, idea_content: str) -> str:
        """Creates the prompt for the generative AI model to perform research and summarize."""
        prompt = f"""
Act as a technical research assistant. Analyze the following project concept and perform research (based on your knowledge,
including web data up to your last training cut-off) to identify relevant technologies,
implementation patterns, and architectural considerations.

**Project Concept (idea.md):**
```markdown
{idea_content}
```

**Task:**

1.  **Identify Key Technical Areas:** Based on the concept, determine the core technical challenges or areas requiring specific technologies (e.g., data storage, API integration, UI framework, specific algorithms, deployment environment).
2.  **Simulate Research:** Find 5-10 relevant articles, blog posts, tutorials, or documentation summaries related to these key technical areas. For each resource found:
    *   Provide a **Title** (or a descriptive name if a formal title isn't available).
    *   Provide a **URL** if possible (or indicate if it's general knowledge).
    *   Write a **Concise Summary** focusing specifically on:
        *   Relevant **technologies** mentioned (libraries, frameworks, databases, languages).
        *   Key **implementation details** or techniques discussed.
        *   Relevant **architectural patterns** or considerations.
        *   Potential **pros and cons** mentioned regarding the approaches.
3.  **Synthesize Findings:** Briefly conclude with a high-level synthesis of the common or most promising technologies/approaches identified for this project concept.

**Output Format:**

Generate a Markdown document (`research_summary.md`) structured as follows:

```markdown
# Technical Research Summary for [Project Name - Infer from Concept]

## Key Technical Areas Identified
*   [Area 1, e.g., Real-time Data Processing]
*   [Area 2, e.g., User Authentication]
*   [Area 3, e.g., Cloud Deployment]
*   ...

## Relevant Resources & Summaries

### 1. Title: [Title of Resource 1]
*   **URL:** [URL or "General Knowledge"]
*   **Summary:**
    *   **Technologies:** [List technologies, e.g., Python, Kafka, React, PostgreSQL]
    *   **Implementation Notes:** [Summarize key techniques/steps, e.g., "Uses Kafka consumers for ingestion...", "Recommends JWT for auth..."]
    *   **Architecture:** [Mention patterns, e.g., "Microservices architecture suggested...", "Event-driven approach..."]
    *   **Pros/Cons:** [Summarize any mentioned trade-offs]

### 2. Title: [Title of Resource 2]
*   **URL:** [URL or "General Knowledge"]
*   **Summary:**
    *   **Technologies:** [...]
    *   **Implementation Notes:** [...]
    *   **Architecture:** [...]
    *   **Pros/Cons:** [...]

### 3. Title: [Title of Resource 3]
*   **URL:** [URL or "General Knowledge"]
*   **Summary:**
    *   **Technologies:** [...]
    *   **Implementation Notes:** [...]
    *   **Architecture:** [...]
    *   **Pros/Cons:** [...]

...(Add up to 5 resources)...

## Synthesis & Recommendations
[Briefly summarize the key takeaways regarding technologies and approaches relevant to implementing the project concept.]
```

**Important:** Focus the summaries on actionable technical details relevant to implementation, not just high-level descriptions. Format the entire output strictly as Markdown.
"""
        return prompt
