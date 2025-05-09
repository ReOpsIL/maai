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
            raise RuntimeError(f"Diagrams Agent failed during diagrams generation: project markdown documents found in project path") 
       
        # --- Read Context (Source Code, Existing Tests if updating) ---
        self.logger.info(f"Reading source code from: {self.src_path}")
        source_code = coder.read_all_code_files()
        if not source_code:
            self.logger.warning(f"No source code found in {self.src_path}.")
            raise RuntimeError(f"Diagram Agent failed during diagrams generation: No source code found in project path") 
       
        # --- Generate or Update Test Cases ---
        self.logger.info("Attempting to generate diagrams using AI.")
        generated_mermaid_files_content = ""
        try:
            create_diagrams_prompt = self._create_diagram_prompt(all_content + "\n\n" + source_code)

            generated_mermaid_files_content = self.model.generate_content(create_diagrams_prompt)
            if not generated_mermaid_files_content:
                raise RuntimeError(f"Diagram Agent failed during mermaid diagrams generation)") 
    
            self.logger.info("Received diagrams generation response from LLM API.")
            self.logger.debug(f"Generated Text (first 200 chars):\n{generated_mermaid_files_content[:200]}...")

            # --- Parsing the generated text into files ---
            # Use the existing robust parser
            generated_content = coder._parse_code_blocks(generated_mermaid_files_content)
            if not generated_content:
                # This is more critical now, as it means no code was generated 
                raise RuntimeError(f"AI response parsed, but no valid code blocks (<<<FILENAME: ...) found.") # Re-raise to signal failure

            diagram_files = coder._write_code_files(generated_content)
            for mdd_file in diagram_files:
                svg_file = mdd_file.replace(".mdd",".svg")
                cmd = f"mmdc -i {mdd_file} -o {svg_file}"
                print(cmd)
                os.system(cmd)

            log_action =  "generated"
            self.logger.info(f"Successfully {log_action} content for {len(generated_mermaid_files_content)} diagram file(s) using AI.")
            
            return diagram_files

        except (ValueError, ConnectionError, RuntimeError) as e:
            self.logger.error(f"Failed to generate diagrams using AI: {e}")
            raise RuntimeError(f"Diagram Agent failed during diagrams generation: {e}") # Re-raise to signal failure
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during diagrams generation: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred during diagrams generation: {e}")


    def _create_diagram_prompt(self, files_content: str) -> str: 
        """Creates a diagram prompt for the generative AI model."""
        prompt = f"""
        Create mermaid diagram for documents and source code:

        ```
        {files_content}
        ```

        Instructions:
        1.  **Diagram Selection:** Smartly choose the most appropriate Mermaid diagram type for each input file's content. For example:
            *   Use Class Diagrams for source code (showing classes, hierarchy, connections, methods, attributes).
            *   Use Flowcharts (`graph TD`) or Sequence Diagrams for feature descriptions or implementation plans (`.md` files) to show system flow, components, integration, connections, and communication.
        2.  **Detail Level:** The diagrams must contain sufficient detail for software programmers and team managers to understand the system flow, components, integration, connections, and communication between modules and components.
        3.  **Source Code Diagrams:** If generating diagrams for source code, focus on class structure, inheritance/relationships, key methods/attributes, API interactions (if evident), and data structures.
        4.  **Mandatory Output Format:** The output structure is critical. You *must* follow the format specified below for *every* generated Mermaid diagram.
            *   Enclose each complete Mermaid diagram definition within a fenced code block.
            *   **Prefix** each code block with `<<<FILENAME: path/to/diagram_name.mdd` on its own line. Use a relevant path and filename (e.g., `diagrams/feature_flow.mdd`, `diagrams/backend_components.mdd`).
            *   **Postfix** each code block with `>>>` on its own line.

        **Required Output Format Example:**

        *This example shows the MANDATORY structure for EACH diagram you generate:*

        <<<FILENAME: diagrams/duck_example.mdd
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
        """
        
        return prompt
