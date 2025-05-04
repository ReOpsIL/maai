import os
from .base_agent import BaseAgent
from .coder import CoderAgent

class DiagramAgent(BaseAgent):
    """
    Source code and flow diagrams generator.
    """

    def run(self):
        """
        Executes the Diagram agent's task: creating the tasks.md file.

        """
        self.logger.info(f"Running Diagram Agent for project: {self.project_name})")

        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            # Or raise a specific exception
            raise RuntimeError("DiagramAgent requires a configured Generative Model.")

        coder = CoderAgent(project_name=self.project_name, project_path=self.project_path)
        all_content, _ = coder.get_all_content()
        if not all_content:
            self.logger.warning(f"No project markdown documents found in {self.src_path}.")
            raise RuntimeError(f"Diagrams Agent failed during diagrams generation: roject markdown documents found in project path") 
       
        # --- Read Context (Source Code, Existing Tests if updating) ---
        self.logger.info(f"Reading source code from: {self.src_path}")
        source_code = coder.read_all_code_files()
        if not source_code:
            self.logger.warning(f"No source code found in {self.src_path}.")
            raise RuntimeError(f"Tester Agent failed during diagrams generation: No source code found in project path") 
       
        # --- Generate or Update Test Cases ---
        self.logger.info("Attempting to generate diagrams using AI.")
        generated_mermaid_files_content = ""
        try:
            create_diagrams_prompt = self._create_diagram_prompt(all_content + "\n\n" + source_code)

            generated_llm_diagrams_prompt = self.model.generate_content(create_diagrams_prompt)
            generated_mermaid_files_content = self.model.generate_content(generated_llm_diagrams_prompt)

            self.logger.info("Received diagrams generation response from LLM API.")
            self.logger.debug(f"Generated Text (first 200 chars):\n{generated_mermaid_files_content[:200]}...")

            # --- Parsing the generated text into files ---
            # Use the existing robust parser
            generated_content = coder._parse_code_blocks(generated_mermaid_files_content)
            if not generated_mermaid_files_content:
                 # This is more critical now, as it means no code was generated 
                 self.logger.warning("AI response parsed, but no valid code blocks (```python filename=...```) found.")
                 # Returning empty dict, the caller handles the warning/error.

            diagram_files = coder._write_code_files(generated_content)
            for mdd_file in diagram_files:
                svg_file = mdd_file.replace(".mdd",".svg")
                cmd = f"mmdc -i {mdd_file}.mmd -o {svg_file}.svg"
                os.system(cmd)

            log_action =  "generated"
            self.logger.info(f"Successfully {log_action} content for {len(generated_mermaid_files_content)} diagram file(s) using AI.")

            return diagram_files

        except (ValueError, ConnectionError, RuntimeError) as e:
            self.logger.error(f"Failed to generate diagrams using AI: {e}")
            raise RuntimeError(f"Tester Agent failed during diagrams generation: {e}") # Re-raise to signal failure
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during diagrams generation: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred during diagrams generation: {e}")


    def _create_diagram_prompt(self, files_content: str) -> str: 
        """Creates a diagram prompt for the generative AI model."""
        prompt = f"""
        Act as a software architect. Take the provided project markdown and source code documents and create an LLM promot for generating a mermaid diagram for each file, and an overview diagram for each major module / compenent (eg. backend, frontend, servers, mobile etc. ).

        Here are the project documents and source code:

        ```
        {files_content}
        ```
        Instructions:
        1. **Each mermaid diagram type should be smartly chosen for each input file content accordingly, for example mermaid class diagram should be created to source code and Flowchart and/or Sequance diagram should be created to a feature or implemnetation description file (*.md)
        2. **The prompt should instruct the LLM to structure the output using Markdown code blocks.** Each block MUST be prefixed with the intended relative filename from the project root, like this:
        3. **The diagrams should contain high details*.* Software programers and team managers should be able to understand the system flow, components, integration , connection and comunication between modules and components.
        4. **Incase of source code.** Provide class diagrams and hierarchy, connection between classes, api calls and data structures.
        
        *Example diagram output structure:*
        
        ```
        <<<FILENAME: diagrams/duck.mdd
        ---
        title: Animal example
        ---
        classDiagram
            note "From Duck till Zebra"
            Animal <|-- Duck
            note for Duck "can fly\ncan swim\ncan dive\ncan help in debugging"
            Animal <|-- Fish
            Animal <|-- Zebra
            Animal : +int age
            Animal : +String gender
            Animal: +isMammal()
            Animal: +mate()
            class Duck{{
                +String beakColor
                +swim()
                +quack()
            }}
            class Fish{{
                -int sizeInFeet
                -canEat()
            }}
            class Zebra{{
                +bool is_wild
                +run()
        }}
        >>>

        <<<FILENAME: diagrams/bank.mdd
            ---
            title: Bank example
            ---
            classDiagram
                class BankAccount
                BankAccount : +String owner
                BankAccount : +Bigdecimal balance
                BankAccount : +deposit(amount)
                BankAccount : +withdrawal(amount)

        >>>
        ```

        """
        
        return prompt
