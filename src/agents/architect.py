import os
import re # Added for parsing

from .base_agent import BaseAgent
from .coder import CoderAgent


class ArchitectAgent(BaseAgent):
    """
    Analyzes the project concept (idea.md) and generates detailed implementation
    plans for each major component (impl_[component].md) and an integration
    plan (integ.md).
    """

    def run(self) -> list[str]:
        """
        Executes the Architect agent's task: creating component-specific
        implementation plans (impl_*.md) and an integration plan (integ.md).

        Returns:
            A list of paths to the generated markdown files.

        Raises:
            FileNotFoundError: If idea.md cannot be read.
            RuntimeError: If AI generation fails or parsing fails.
            IOError: If writing output files fails.
        """
        self.logger.info(f"Running Architect Agent for project: {self.project_name})")
        idea_md_path = os.path.join(self.docs_path, "idea.md")

        self.logger.info(f"Reading concept from: {idea_md_path}")
        idea_content = self._read_file(idea_md_path)
        if idea_content is None:
            raise FileNotFoundError(f"Could not read idea.md for project {self.project_name}. Please ensure it exists.")

        self.logger.info("Attempting to generate implementation plan using AI.")
        try:
            # Generate the combined plan string from AI
            combined_plan_output = self._generate(
                idea_content=idea_content
            )
            self.logger.info("Successfully generated implementation plan using AI.")
        except (FileNotFoundError, ValueError, ConnectionError, RuntimeError) as e: # Added FileNotFoundError
            self.logger.error(f"Failed to generate implementation plan using AI: {e}")
            raise RuntimeError(f"Architect Agent failed: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during plan generation : {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Architect Agent: {e}")
        self.logger.info("Parsing generated plan into component and integration files.")
        try:
            # Parse the combined output and write individual files
            generated_files = self._parse_and_write_plans(combined_plan_output)
            self.logger.info(f"Successfully created implementation files: {generated_files}")
        except ValueError as e:
            self.logger.error(f"Failed to parse AI response: {e}", exc_info=True)
            raise RuntimeError(f"Architect Agent failed during parsing: {e}")
        except IOError as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write implementation files for project {self.project_name}: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during plan writing: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Architect Agent during writing: {e}")

        return generated_files
    
    def run_features_impl(self):
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("ArchitectAgent requires a configured Generative Model.")

        coder = CoderAgent(project_name=self.project_name, project_path=self.project_path)
    
        feature_content = coder.get_feature_content()
        idea_content = coder.get_idea_content()
        prompt = self._create_feature_impl_prompt(idea_content, feature_content)
        
        # Create mode 
        self.logger.debug(f"Generated create prompt for LLM (Architect):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to LLM API for feature impl prompt...")
            feature_impl_prompt = self.model.generate_content(prompt)           
            self.logger.debug(f"Generated feature impl prompt (first 500 chars):\n{feature_impl_prompt[:500]}...")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM API call (Architect): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate architecture plan using AI: {e}")
        
        try:
            # Parse the combined output and write individual files
            generated_files = self._parse_and_write_feature_plans(feature_impl_prompt)
            self.logger.info(f"Successfully created implementation files: {generated_files}")
        except ValueError as e:
            self.logger.error(f"Failed to parse AI response: {e}", exc_info=True)
            raise RuntimeError(f"Architect Agent failed during parsing: {e}")
        except IOError as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write implementation files for project {self.project_name}: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during plan writing: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Architect Agent during writing: {e}")

        return generated_files
    

    def run_enhance(self, features=True):
        generated_files = []
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("ArchitectAgent requires a configured Generative Model.")

        coder = CoderAgent(project_name=self.project_name, project_path=self.project_path)
    
        
        if features:
            idea_content = coder.get_idea_content()
            prompt = self._create_features_prompt(idea_content)
        # else:
        #     //TODO - handle 
        #     impl_content, plan_files = coder.get_all_content()
        #     prompt = self._create_enhanced_prompt(impl_content, plan_files)
        
        file_name = f"request_enhanced_prompt.txt"
        file_path = os.path.join(self.docs_path, file_name)
        self.logger.info(f"Writing request enhanced prompt to: {file_path}")
        self._write_file(file_path, prompt)
    
        # Create mode 
        self.logger.debug(f"Generated create prompt for LLM (Architect):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to LLM API for enhanced prompt...")
            enhanced_prompt = self.model.generate_content(prompt)    
            file_name = f"enhanced_prompt.txt"
            file_path = os.path.join(self.docs_path, file_name)
            self.logger.info(f"Writing enhanced prompt to: {file_path}")
            self._write_file(file_path, enhanced_prompt)
            self.logger.debug(f"Generated enhanced prompt (first 500 chars):\n{enhanced_prompt[:500]}...")
            enhanced_content = self.model.generate_content(enhanced_prompt)
            file_name = f"enhanced_content.txt"
            file_path = os.path.join(self.docs_path, file_name)
            self.logger.info(f"Writing enhanced content to: {file_path}")
            self._write_file(file_path, enhanced_content)
            self.logger.debug(f"Generated enhanced content (first 500 chars):\n{enhanced_prompt[:500]}...")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM API call (Architect): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate architecture plan using AI: {e}")
        
        try:
            if features:
                # features_file_path = os.path.join(self.docs_path, "features.md")
                # self._write_file(features_file_path, enhanced_content)
                features_files = self._parse_and_write_features_descriptions(enhanced_content)                
                self.logger.info(f"Successfully created features file: {features_files}")
                return features_files
            else:
                # Parse the combined output and write individual files
                generated_files = self._parse_and_write_plans(enhanced_content)
                self.logger.info(f"Successfully created implementation files: {generated_files}")
                return generated_files
        except ValueError as e:
            self.logger.error(f"Failed to parse AI response: {e}", exc_info=True)
            raise RuntimeError(f"Architect Agent failed during parsing: {e}")
        except IOError as e:
            # Error logged by _write_file
            raise IOError(f"Failed to write implementation files for project {self.project_name}: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during plan writing: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Architect Agent during writing: {e}")
    
    def _generate(self, idea_content: str) -> str:
        """
        Uses Generative AI to create the implementation plan string.
        """
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("ArchitectAgent requires a configured Generative Model.")

        existing_impl_content = None
         
        # Create mode 
        prompt = self._create_prompt(idea_content)
        self.logger.debug(f"Generated create prompt for LLM (Architect):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to LLM API for architecture plan...")
            generated_plan = self.model.generate_content(prompt)
            self.logger.info("Received architecture plan from LLM API.")
            self.logger.debug(f"Generated Plan (first 200 chars):\n{generated_plan[:200]}...")
            return generated_plan
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM API call (Architect): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate architecture plan using AI: {e}")

    def _create_feature_impl_prompt(self, idea_content: str, feature_content: str) -> str: # For initial creation
            """Creates the prompt for the generative AI model to design the architecture of each feature."""
            prompt = f"""
    Analyze the following project idea and features description list (provided in Markdown) and generate a set of detailed implementation plans, for each feature and for each optional feature, and a separate integration plan for each feature. These plans must be highly detailed to guide a Coder Agent.

    **Project idea (from idea.md):**
    ```markdown
    {idea_content}
    ```

    **Project features (from features*.md):**
    ```markdown
    {feature_content}
    ```

    **Instructions:**

    1.  **Identify Major Components:** Based on the concept and feature description, identify the distinct major componentss for implementaing **each feature** (e.g., backend, frontend, database, deployment, external_service_integration, etc.). Use simple, lowercase names for components (e.g., `backend`, `frontend`) **with feature name as prefix**.
    2.  **Generate Component Implementation Plans:** For **EACH** major feature component identified of **EACH** feature, generate a **detailed implementation plan** in Markdown format. **Each plan should cover the following items**:
        *   **Technology Stack:** Specific technologies, libraries, frameworks, and versions for this component **(related to feature**)**.
        *   **Project Structure:** Detailed directory and file structure within the feature component's sub-directory (e.g., `[feature_name]/backend/src/...`, `[feature_name]/frontend/src/...`). List key files and their purpose.
        *   **Core Modules/Classes/Functions:** Define the main code structures. Specify purpose, key methods/functions (with parameters, return types, type hints), and important attributes/data. *Be very specific*.
        *   **Data Structures:** Detail significant data structures internal to this component or passed immediately to/from it.
        *   **API Definitions (if applicable):** If this feature component provides or consumes an API, define the endpoints, request/response formats, and authentication details relevant *to this feature component*.
        *   **Error Handling:** Specific error handling strategies within this feature component.
        *   **Testing Strategy:** Specific unit and integration tests for this feature component. Suggest relevant libraries (`pytest`, `jest`, etc.).
        *   **Setup/Run Instructions:** Basic steps to set up and run this feature component independently, if possible.
    3.  **Generate Integration Plan:** Create a separate integration plan (`integ.md`) in Markdown format that describes:
        *   **Overall Architecture Diagram/Description:** A high-level overview of how all feature components fit together. Use a textual description or simple diagram (like ASCII art, avoid Mermaid).
        *   **Communication Flow:** Describe the sequence of interactions between feature components for key use cases. Detail the protocols (e.g., REST API calls, message queues, database queries), data formats, and authentication methods used *between* components.
        *   **Shared Data Structures:** Define data structures used for communication *between* feature components.
        *   **Cross-Cutting Concerns:** Address aspects like authentication, logging, and configuration management across festure components.
        *   **Deployment Overview:** Briefly outline how the festure components will be deployed together (e.g., Docker Compose, Kubernetes).
    4.  **Format Output:** Structure the entire output clearly using the following delimiters. **Crucially, place each feature component's plan and the integration plan between these delimiters.**

        ```
        <<<FEATURE: [feature_name_1]>>>
            ## All components fore feature [feature_name_1]

            <<<COMPONENT: [component_name_1]>>>
            # Implementation Plan: [Component Name 1]
            (Detailed Markdown plan for component 1...)

            <<<COMPONENT: [component_name_2]>>>
            # Implementation Plan: [Component Name 2]
            (Detailed Markdown plan for component 2...)

            <<<COMPONENT: [component_name_n]>>>
            # Implementation Plan: [Component Name N]
            (Detailed Markdown plan for component n...)

            <<<INTEGRATION>>>
            # Integration Plan
            (Detailed Markdown plan for integration...)

        <<<FEATURE: [feature_name_2]>>>
            ## All components fore feature [feature_name_2]

            <<<COMPONENT: [component_name_1]>>>
            # Implementation Plan: [Component Name 1]
            (Detailed Markdown plan for component 1...)

            <<<COMPONENT: [component_name_2]>>>
            # Implementation Plan: [Component Name 2]
            (Detailed Markdown plan for component 2...)

            <<<COMPONENT: [component_name_n]>>>
            # Implementation Plan: [Component Name N]
            (Detailed Markdown plan for component n...)

            <<<INTEGRATION>>>
            # Integration Plan
            (Detailed Markdown plan for integration...)
        ```

        *   Replace `[feature_name_1]`, `[feature_name_2]`, etc., with the actual lowercase feature name
        *   Replace `[component_name_1]`, `[component_name_2]`, etc., with the actual lowercase component names you identified theat belog to a feature (e.g., `backend`, `frontend`).
        *   Ensure the content within each delimited section is valid Markdown.
        *   Do not include any text before the first delimiter or after the last plan.

    **Output the complete response containing all delimited sections.**
    """
            return prompt


    def _create_prompt(self, idea_content: str) -> str: # For initial creation
        """Creates the prompt for the generative AI model to design the architecture."""
        prompt = f"""
Analyze the following project concept (provided in Markdown) and generate a set of detailed implementation plans, one for each major component, and a separate integration plan. These plans must be highly detailed to guide a Coder Agent.

**Project Concept (from idea.md):**
```markdown
{idea_content}
```

**Instructions:**

1.  **Identify Major Components:** Based on the concept, identify the distinct major components of the system (e.g., backend, frontend, database, deployment, external_service_integration, etc.). Use simple, lowercase names for components (e.g., `backend`, `frontend`).
2.  **Generate Component Implementation Plans:** For **EACH** major component identified, generate a **detailed implementation plan** in Markdown format. **Each plan should cover the following items**:
    *   **Technology Stack:** Specific technologies, libraries, frameworks, and versions for this component.
    *   **Project Structure:** Detailed directory and file structure within the component's sub-directory (e.g., `backend/src/...`, `frontend/src/...`). List key files and their purpose.
    *   **Core Modules/Classes/Functions:** Define the main code structures. Specify purpose, key methods/functions (with parameters, return types, type hints), and important attributes/data. *Be very specific*.
    *   **Data Structures:** Detail significant data structures internal to this component or passed immediately to/from it.
    *   **API Definitions (if applicable):** If this component provides or consumes an API, define the endpoints, request/response formats, and authentication details relevant *to this component*.
    *   **Error Handling:** Specific error handling strategies within this component.
    *   **Testing Strategy:** Specific unit and integration tests for this component. Suggest relevant libraries (`pytest`, `jest`, etc.).
    *   **Setup/Run Instructions:** Basic steps to set up and run this component independently, if possible.
3.  **Generate Integration Plan:** Create a separate integration plan (`integ.md`) in Markdown format that describes:
    *   **Overall Architecture Diagram/Description:** A high-level overview of how all components fit together. Use a textual description or simple diagram (like ASCII art, avoid Mermaid).
    *   **Communication Flow:** Describe the sequence of interactions between components for key use cases. Detail the protocols (e.g., REST API calls, message queues, database queries), data formats, and authentication methods used *between* components.
    *   **Shared Data Structures:** Define data structures used for communication *between* components.
    *   **Cross-Cutting Concerns:** Address aspects like authentication, logging, and configuration management across components.
    *   **Deployment Overview:** Briefly outline how the components will be deployed together (e.g., Docker Compose, Kubernetes).
4.  **Format Output:** Structure the entire output clearly using the following delimiters. **Crucially, place each component's plan and the integration plan between these delimiters.**

    ```
    <<<COMPONENT: [component_name_1]>>>
    # Implementation Plan: [Component Name 1]
    (Detailed Markdown plan for component 1...)

    <<<COMPONENT: [component_name_2]>>>
    # Implementation Plan: [Component Name 2]
    (Detailed Markdown plan for component 2...)

    <<<COMPONENT: [component_name_n]>>>
    # Implementation Plan: [Component Name N]
    (Detailed Markdown plan for component n...)

    <<<INTEGRATION>>>
    # Integration Plan
    (Detailed Markdown plan for integration...)
    ```

    *   Replace `[component_name_1]`, `[component_name_2]`, etc., with the actual lowercase names you identified (e.g., `backend`, `frontend`).
    *   Ensure the content within each delimited section is valid Markdown.
    *   Do not include any text before the first delimiter or after the last plan.

**Output the complete response containing all delimited sections.**
"""
        return prompt
    
    
    def _create_features_prompt(self, idea_content):
        return f"""**Act as a Prompt Engineering Specialist.**

            **Your goal is to generate a comprehensive prompt.** This prompt will be used later to instruct another large language model to act as an expert system architect and senior developer.

            The prompt you generate should tell the model to perform the following tasks based on provided input files:

            1.  **Read and Understand:** Instruct the model to meticulously read and fully understand the project idea described in a file named `idea.md`.
            2.  **Extend and Detail Key Features:** Instruct the model to significantly extend, refine, and add greater detail to *each* of the <## Key Features> in `idea.md` 
            3.  **Extend and Detail Potential Enhancements / Future Ideas:** Instruct the model to significantly extend, refine, and add greater detail to *each* of the <## Potential Enhancements / Future Ideas> in `idea.md`     
            4.  **Generate Output:** Instruct the model that its final output should be the complete, updated content of *each* of the <## Key Features>  and <## Potential Enhancements / Future Ideas> .
            5.  **Target Outcome:** Emphasize that the objective of the generated prompt's task is to produce a robust, accurate, and detailed feaures descriptions that are sufficiently clear and complete to allow direct implementation of the described features.

            Your output should be *only* the text of the prompt described above. Do not include any conversational text or explanations outside of the prompt itself.
            
            6.  **Format Output:** Structure the entire output clearly using the following delimiters. **Crucially, place each component's plan and the integration plan between these delimiters.**

                ```
                # Key features section:
                <<<KEY_FEATURE: [feature_name_1]>>>
                # Feature description: [Feature Name 1]
                (Detailed Markdown plan for feature 1...)

                <<<KEY_FEATURE: [feature_name_2]>>>
                # Feature description: [Feature Name 2]
                (Detailed Markdown plan for feature 2...)

                <<<KEY_FEATURE: [feature_name_n]>>>
                # Feature description: [Feature Name N]
                (Detailed Markdown plan for feature n...)

                # Optional feature section:
                <<<KEY_FEATURE: [opt_feature_name_1]>>>
                # Optional feature description: [Optional Feature Name 1]
                (Detailed Markdown plan for optional feature 1...)

                <<<KEY_FEATURE: [opt_feature_name_2]>>>
                # Optional feature description: [Optional Feature Name 2]
                (Detailed Markdown plan for optional feature 2...)

                <<<KEY_FEATURE: [opt_feature_name_n]>>>
                # Optional feature description: [Optional Feature Name N]
                (Detailed Markdown plan for optional feature n...)

                ```

                *   Replace `[feature_name_1]`, `[feature_name_2]`, `[opt_feature_name_1]`, `[opt_feature_name_2]`, etc., with the actual lowercase names of the features (e.g., `calcium risk`, `preview axial` Etc').
                *   Ensure the content within each delimited section is valid Markdown.
                *   Do not include any text before the first delimiter or after the last plan.

            **Output the complete response containing all delimited sections.**
            
            **idea file with list of features and optional features(`idea.md`):**
            ```markdown

            {idea_content}

            ```
            """
    
    def _create_enhanced_prompt(self, impl_content, plan_files):
        plan_files_str = ",".join(plan_files)

        return f"""**Act as a Prompt Engineering Specialist.**

            **Your goal is to generate a comprehensive prompt.** This prompt will be used later to instruct another large language model to act as an expert system architect and senior developer.

            The prompt you generate should tell the model to perform the following tasks based on provided input files:

            1.  **Read and Understand:** Instruct the model to meticulously read and fully understand the project idea described in a file named `idea.md`.
            2.  **Incorporate and Validate:** Instruct the model to read initial implementation plan files ({plan_files_str}) including integration file `integ.md`. The model should then verify that these initial plans align with the `idea.md` requirements and identify any inconsistencies or missing details.
            3.  **Extend and Detail:** Instruct the model to significantly extend, refine, and add greater detail to *each* of the implementation plan files ({plan_files_str}) and the integration plan (`integ.md`) based on the comprehensive requirements in `idea.md` and best practices for software architecture and development. This detailing should cover API specifications (endpoints, schemas, auth), service logic, data structures/schemas (with types, constraints, relationships), deployment specifics (manifest examples, config management), external service API usage/error handling, and inter-component communication flows (potentially using diagrams or detailed step-by-step descriptions).
            4.  **Generate Output:** Instruct the model that its final output should be the complete, updated content of *each* of the refined implementation and integration files ({plan_files_str}).
            5.  **Target Outcome:** Emphasize that the objective of the generated prompt's task is to produce a robust, accurate, and detailed set of implementation blueprints that are sufficiently clear and complete to allow for direct implementation of the described application.

            Your output should be *only* the text of the prompt described above. Do not include any conversational text or explanations outside of the prompt itself.
            
            6.  **Format Output:** Structure the entire output clearly using the following delimiters. **Crucially, place each component's plan and the integration plan between these delimiters.**

                ```
                <<<COMPONENT: [component_name_1]>>>
                # Implementation Plan: [Component Name 1]
                (Detailed Markdown plan for component 1...)

                <<<COMPONENT: [component_name_2]>>>
                # Implementation Plan: [Component Name 2]
                (Detailed Markdown plan for component 2...)

                <<<COMPONENT: [component_name_n]>>>
                # Implementation Plan: [Component Name N]
                (Detailed Markdown plan for component n...)

                <<<INTEGRATION>>>
                # Integration Plan
                (Detailed Markdown plan for integration...)
                ```

                *   Replace `[component_name_1]`, `[component_name_2]`, etc., with the actual lowercase names you identified (e.g., `backend`, `frontend` Etc').
                *   Ensure the content within each delimited section is valid Markdown.
                *   Do not include any text before the first delimiter or after the last plan.

            **Output the complete response containing all delimited sections.**
            
            **Integration plan (`integ.md`) and Implementation Plan (`impl_*.md`):**
            ```markdown

            {impl_content}

            ```
            """
    
    def _parse_and_write_features_descriptions(self, combined_output: str) -> list[str]:
        """
        Parses the AI's combined output string based on delimiters and writes
        individual feature markdown files.

        Args:
            combined_output: The raw string response from the AI model.
        Returns:
            A list of paths to the files written.

        Raises:
            ValueError: If parsing fails (e.g., delimiters not found).
            IOError: If writing files fails.
        """
        # Updated regex to capture content until the next delimiter or end of string
        feature_pattern = re.compile(r"<<<KEY_FEATURE:\s*(.*?)>>>\s*(.*?)(?=\s*<<<KEY_FEATURE|\Z)", re.DOTALL | re.IGNORECASE)
    
        features = feature_pattern.findall(combined_output)
        for feature_name, feature in features:
            feature_id = feature_name.strip().lower()
            feature_id = re.sub('[^0-9a-zA-Z]+', '_', feature_id)
            if feature_id[-1] == '_':
                feature_id = feature_id[:-1]

            written_files = []

            # Write feature files
           
            if not feature_name:
                self.logger.warning("Found component block with empty name, skipping.")
                continue
            file_name = f"feature_{feature_id}.md"
            file_path = os.path.join(self.docs_path, file_name) #feature_name,
            self.logger.info(f"Writing feature component plan to: {file_path}")
            feature_content = feature.strip()
            # Add a header if the AI didn't include one (optional, but good practice)
            
            feature_content = f"<<<KEY_FEATURE: `{feature_name}` ID: id_{feature_id} \n\n{feature_content}\n\n>>>"
            self._write_file(file_path, feature_content) # Raises IOError on failure
            written_files.append(file_path)

    
        if not written_files:
             raise ValueError("Parsing completed, but no valid features were extracted to write.")

        return written_files
        
    def _parse_and_write_feature_plans(self, combined_output: str) -> list[str]:
        """
        Parses the AI's combined output string based on delimiters and writes
        individual feature component and integration markdown files.

        Args:
            combined_output: The raw string response from the AI model.
        Returns:
            A list of paths to the files written.

        Raises:
            ValueError: If parsing fails (e.g., delimiters not found).
            IOError: If writing files fails.
        """
        # Updated regex to capture content until the next delimiter or end of string
        feature_pattern = re.compile(r"<<<FEATURE:\s*(.*?)>>>\s*(.*?)(?=\s*<<<FEATURE|\Z)", re.DOTALL | re.IGNORECASE)
        component_pattern = re.compile(r"<<<COMPONENT:\s*(.*?)>>>\s*(.*?)(?=\s*<<<|\Z)", re.DOTALL | re.IGNORECASE)
        integration_pattern = re.compile(r"<<<INTEGRATION>>>(.*)", re.DOTALL | re.IGNORECASE)

        features = feature_pattern.findall(combined_output)
        for feature_name, feature in features:
            feature_id = feature_name.lower()
            feature_id = re.sub('[^0-9a-zA-Z]+', '_', feature_id)
            if feature_id[-1] == '_':
                feature_id = feature_id[:-1]

            components = component_pattern.findall(feature)
            integration_match = integration_pattern.search(feature)

            if not components and not integration_match:
                raise ValueError("Could not find any <<<COMPONENT: ...>>> or <<<INTEGRATION>>> delimiters in the AI output.")

            written_files = []

            # Write component files
            for name, content in components:
                component_name = name.strip().lower()
                component_name = re.sub('[^0-9a-zA-Z]+', '_', component_name)
                if component_name[-1] == '_':
                    component_name = component_name[:-1]
            
                if not component_name:
                    self.logger.warning("Found component block with empty name, skipping.")
                    continue
                file_name = f"impl_{component_name}.md"
                file_path = os.path.join(self.docs_path, file_name) #feature_name,
                self.logger.info(f"Writing feature component plan to: {file_path}")
                plan_content = content.strip()
                # Add a header if the AI didn't include one (optional, but good practice)
                plan_content = f"<<<KEY_FEATURE: `{feature_name.replace('_',' ').strip()}` component `{component_name}` ID: id_{component_name}\n\n{plan_content}\n\n>>>"
                self._write_file(file_path, plan_content) # Raises IOError on failure
                written_files.append(file_path)

            # Write integration file
            if integration_match:
                file_name = f"integ_{feature_id}.md"
                file_path = os.path.join(self.docs_path, file_name)
                self.logger.info(f"Writing integration plan to: {file_path}")
                plan_content = integration_match.group(1).strip()
                # Add a header if the AI didn't include one
                plan_content = f"<<<KEY_FEATURE: `{feature_name.replace('_',' ').strip()}` ID: id_{feature_id} \n\n{plan_content}\n\n>>>"
                self._write_file(file_path, plan_content) # Raises IOError on failure
                written_files.append(file_path)
            else:
                self.logger.warning("No <<<INTEGRATION>>> section found in the AI output.")

        if not written_files:
             raise ValueError("Parsing completed, but no valid component or integration plans were extracted to write.")

        return written_files


    def _parse_and_write_plans(self, combined_output: str) -> list[str]:
        """
        Parses the AI's combined output string based on delimiters and writes
        individual component and integration markdown files.

        Args:
            combined_output: The raw string response from the AI model.

        Returns:
            A list of paths to the files written.

        Raises:
            ValueError: If parsing fails (e.g., delimiters not found).
            IOError: If writing files fails.
        """
        # Updated regex to capture content until the next delimiter or end of string
        component_pattern = re.compile(r"<<<COMPONENT:\s*(.*?)>>>\s*(.*?)(?=\s*<<<|\Z)", re.DOTALL | re.IGNORECASE)
        integration_pattern = re.compile(r"<<<INTEGRATION>>>(.*)", re.DOTALL | re.IGNORECASE)

        components = component_pattern.findall(combined_output)
        integration_match = integration_pattern.search(combined_output)

        if not components and not integration_match:
            raise ValueError("Could not find any <<<COMPONENT: ...>>> or <<<INTEGRATION>>> delimiters in the AI output.")

        written_files = []

        # Write component files
        for name, content in components:
            component_name = name.strip().lower()
            component_name = re.sub('[^0-9a-zA-Z]+', '_', component_name)
            if not component_name:
                self.logger.warning("Found component block with empty name, skipping.")
                continue
            file_name = f"impl_{component_name}.md"
            file_path = os.path.join(self.docs_path, file_name)
            self.logger.info(f"Writing component plan to: {file_path}")
            plan_content = content.strip()
            # Add a header if the AI didn't include one (optional, but good practice)
            if not plan_content.startswith("#"):
                 plan_content = f"# Implementation Plan: {component_name.capitalize()}\n\n{plan_content}"
            self._write_file(file_path, plan_content) # Raises IOError on failure
            written_files.append(file_path)

        # Write integration file
        if integration_match:
            file_name = "integ.md"
            file_path = os.path.join(self.docs_path, file_name)
            self.logger.info(f"Writing integration plan to: {file_path}")
            plan_content = integration_match.group(1).strip()
             # Add a header if the AI didn't include one
            if not plan_content.startswith("#"):
                 plan_content = f"# Integration Plan\n\n{plan_content}"
            self._write_file(file_path, plan_content) # Raises IOError on failure
            written_files.append(file_path)
        else:
            self.logger.warning("No <<<INTEGRATION>>> section found in the AI output.")

        if not written_files:
             raise ValueError("Parsing completed, but no valid component or integration plans were extracted to write.")

        return written_files

    def _create_update_prompt(self, existing_impl_content: str | None, modification_text: str, idea_content: str) -> str:
        """
        Creates the prompt for the generative AI model to update implementation plans.
        Note: This currently regenerates all plans based on the idea and modifications,
        using the old impl_*.md (if available) only as context for the previous state.
        A future improvement could involve reading and updating individual component files.
        """
        existing_plan_section = ""
        if existing_impl_content:
            existing_plan_section = f"""
**Previous Implementation Plan (impl_*.md - for context only):**
```markdown
{existing_impl_content}
```
"""

        prompt = f"""
Update and regenerate the implementation plans based on the provided modification instructions, the latest project concept, and the context from the previous plan (if provided). The output must follow the multi-component structure detailed below.

**Latest Project Concept (idea.md):**
```markdown
{idea_content}
```
{existing_plan_section}
**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze the latest concept, the modification instructions, and the previous plan context (if available).**
2.  **Identify the major components** required for the *updated* system (e.g., backend, frontend, database, deployment). Use simple, lowercase names.
3.  **Generate Updated Component Plans:** For EACH major component, generate a *complete and detailed* implementation plan reflecting the requested modifications and the latest concept. Follow the detailed structure specified below for component plans.
4.  **Generate Updated Integration Plan:** Create a *complete and detailed* integration plan (`integ.md`) reflecting the updated architecture and interactions. Follow the detailed structure specified below for the integration plan.
5.  **Output Format:** Structure the entire output using the delimiters `<<<COMPONENT: [component_name]>>>` for each component plan and `<<<INTEGRATION>>>` for the integration plan, exactly as specified in the initial creation instructions. Ensure the content within each section is valid Markdown.

**Component Plan Structure (Repeat for each component):**
*   Technology Stack
*   Project Structure (Detailed)
*   Core Modules/Classes/Functions (Detailed: purpose, methods/params/returns/types, attributes)
*   Data Structures
*   API Definitions (if applicable)
*   Error Handling
*   Testing Strategy
*   Setup/Run Instructions

**Integration Plan Structure:**
*   Overall Architecture Diagram/Description (Textual/ASCII)
*   Communication Flow (Protocols, Data Formats, Auth between components)
*   Shared Data Structures (Between components)
*   Cross-Cutting Concerns (Auth, Logging, Config)
*   Deployment Overview

**Output the complete response containing all delimited sections for the updated plans.** Do not include any introductory text or text after the final plan.
"""
        return prompt
