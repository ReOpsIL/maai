import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import re
from .base_agent import BaseAgent

class CoderAgent(BaseAgent):
    """
    Generates Python code based on the implementation specifications (impl.md).
    """

    def run(self, feedback: str | None = None, modification_text: str | None = None, update_mode: bool = False, impl_content: str | None = None):
        """
        Executes the Coder agent's task: generating or updating Python source files.

        Args:
            feedback: Optional feedback from Reviewer/Tester agents (used in build loop).
            modification_text: Specific instructions for modifying existing code (used for explicit update command).
            update_mode: If True, read existing code and apply modifications.
                         If False, generate code based on impl.md and optional feedback.
            impl_content: Optional pre-read content of impl.md. If None, reads from file.
        """
        self.logger.info(f"Running Coder Agent for project: {self.project_name} (Update Mode: {update_mode})")
        if update_mode:
             if not modification_text:
                 raise ValueError("Modification text is required when running Coder in update mode.")
             self.logger.info(f"Incorporating modification instructions:\n{modification_text}")
        elif feedback:
            self.logger.info(f"Incorporating feedback from review/test:\n{feedback}")
        # Read impl.md content if not provided
        if impl_content is None:
            impl_md_path = os.path.join(self.docs_path, "impl.md")
            self.logger.info(f"Reading implementation plan from: {impl_md_path}")
            impl_content = self._read_file(impl_md_path)
            if impl_content is None:
                raise FileNotFoundError(f"Could not read impl.md for project {self.project_name}. Please ensure the Architect Agent ran successfully.")
        else:
             self.logger.info("Using provided implementation plan content.")

        existing_code = None
        if update_mode:
            self.logger.info(f"Reading existing source code from: {self.src_path}")
            existing_code = self._read_existing_code()
            if not existing_code:
                 self.logger.warning(f"No existing code found in {self.src_path} to update.")
                 # Decide if we should proceed or fail. Let's proceed but it might not be effective.
                 # raise FileNotFoundError(f"Cannot update code: No source files found in {self.src_path}")


        self.logger.info("Attempting to generate or update code using AI.")
        try:
            generated_code_files = self._generate_or_update_code(
                impl_content=impl_content,
                existing_code=existing_code,
                modification_text=modification_text,
                feedback=feedback # Pass feedback along for both modes potentially
            )
            log_action = "updated" if update_mode else "generated"
            self.logger.info(f"Successfully {log_action} content for {len(generated_code_files)} code file(s) using AI.")
        except (ValueError, ConnectionError, RuntimeError) as e:
            self.logger.error(f"Failed to generate/update code using AI: {e}")
            raise RuntimeError(f"Coder Agent failed: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during code generation/update: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in Coder Agent: {e}")

        self.logger.info(f"Writing generated code files to project path: {self.project_path}")
        written_files = []
        try:
            # The _write_file helper handles directory creation including nested ones
            for relative_path, code_content in generated_code_files.items():
                # Construct the full path within the project directory
                # relative_path might be 'main.py' or 'subdir/utils.py' etc.
                # Basic sanitization on the relative path components might be needed,
                # but os.path.join handles separators correctly.
                # We rely on the LLM providing valid relative paths within the project context.
                # Avoid writing outside the project! (os.path.join prevents absolute paths)

                # Simple check to prevent writing files like requirements.txt directly in root
                # Allow files directly in project root if they are common config/setup files
                allowed_root_files = ['.gitignore', '.flaskenv', 'requirements.txt', 'run.py', 'config.py'] # Extend as needed
                path_parts = relative_path.split(os.sep)

                if len(path_parts) == 1 and path_parts[0] not in allowed_root_files and not path_parts[0].endswith('.py'):
                     self.logger.warning(f"Skipping potentially misplaced root file: '{relative_path}'")
                     continue

                # Ensure path is relative and within project boundaries (rudimentary check)
                if ".." in path_parts or os.path.isabs(relative_path):
                     self.logger.warning(f"Skipping file with potentially unsafe path: '{relative_path}'")
                     continue

                full_path = os.path.join(self.project_path, relative_path)

                # Ensure the directory for the file exists before writing
                # _write_file handles this, but double-checking doesn't hurt if concerned
                # os.makedirs(os.path.dirname(full_path), exist_ok=True)

                self._write_file(full_path, code_content) # _write_file creates dirs
                written_files.append(full_path)
                self.logger.info(f"Successfully wrote {full_path}")

        except Exception as e:
            logger.error(f"Error during file writing process: {e}", exc_info=True)
            raise IOError(f"Failed to write code files for project {self.project_name}: {e}")

        if not written_files:
             self.logger.warning("Coder Agent finished but did not produce any valid Python files.")
             # Decide if this should be an error or just a warning
             # raise RuntimeError("Coder Agent failed to produce any code files.")


        return written_files # Return list of paths to generated files

    def _read_existing_code(self) -> dict[str, str]:
        """Reads all .py files from the project's src directory."""
        code_files = {}
        if not os.path.isdir(self.src_path):
            return code_files # Return empty if src dir doesn't exist

        try:
            for filename in os.listdir(self.src_path):
                if filename.endswith(".py"):
                    file_path = os.path.join(self.src_path, filename)
                    content = self._read_file(file_path)
                    if content is not None:
                        # Store with relative path within src/
                        code_files[filename] = content
        except Exception as e:
            self.logger.error(f"Error reading existing code files from {self.src_path}: {e}", exc_info=True)
            # Decide if this should be fatal or just return what was read so far
            # For now, return potentially partial results

        return code_files


    def _generate_or_update_code(self, impl_content: str, existing_code: dict[str, str] | None, modification_text: str | None, feedback: str | None) -> dict[str, str]:
        """Uses Generative AI to create or update the Python code."""
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("CoderAgent requires a configured Generative Model.")

        if existing_code and modification_text:
             # Prioritize explicit modification text for update mode
             prompt = self._create_update_prompt(impl_content, existing_code, modification_text)
             self.logger.debug(f"Generated update prompt for Gemini (Coder):\n{prompt[:500]}...")
        else:
             # Create mode (or build loop with feedback)
             prompt = self._create_prompt(impl_content, feedback) # Use original create prompt
             self.logger.debug(f"Generated create/feedback prompt for Gemini (Coder):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to Gemini API for code generation...")
            # Increase max output tokens if necessary for larger codebases
            # generation_config = genai.types.GenerationConfig(max_output_tokens=8192) # Example
            # response = model.generate_content(prompt, generation_config=generation_config)
            response = self.model.generate_content(prompt)

            generated_text = response.text
            self.logger.info("Received code generation response from Gemini API.")
            self.logger.debug(f"Generated Text (first 200 chars):\n{generated_text[:200]}...")

            # --- Parsing the generated text into files ---
            code_files = self._parse_code_blocks(generated_text)
            if not code_files:
                self.logger.warning("AI response parsed, but no valid code blocks found.")
                # Handle this case - maybe retry prompt or raise error?
                # For now, return empty dict, subsequent steps might fail.

            return code_files

        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Coder): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for code generation: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Gemini API call (Coder): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate code using AI: {e}")

    def _create_prompt(self, impl_content: str, feedback: str | None) -> str: # For initial creation or feedback loop
        """Creates the prompt for the generative AI model to generate code from scratch or based on feedback."""
        feedback_section = ""
        if feedback:
            feedback_section = f"""
**Incorporate the following feedback from the previous Review/Test cycle:**
```
{feedback}
```
Address these points specifically in the generated code.
"""

        prompt = f"""
Generate Python code for the project described in the following implementation plan (impl.md). Adhere strictly to the plan's specifications regarding modules, classes, methods, and overall architecture.

**Implementation Plan (from impl.md):**
```markdown
{impl_content}
```
{feedback_section}
**Instructions:**

1.  **Generate complete, runnable Python files.**
2.  **Use Python 3.9+ syntax, including type hints as specified in the plan.**
3.  **Implement all core modules, classes, and functions defined in the plan.** Include basic error handling (e.g., try-except blocks for file I/O or API calls if specified).
4.  **Add necessary import statements** at the beginning of each file.
5.  **Include basic docstrings** for classes and functions explaining their purpose.
6.  **Structure the output clearly.** Use Markdown code blocks prefixed with the intended filename like this:

    ```python filename=src/some_module.py
    # Contents of some_module.py
    import os

    def main():
        print("Hello from some_module!")

    if __name__ == "__main__":
        main()
    ```

    ```python filename=src/another_util.py
    # Contents of another_util.py
    def helper_function(x: int) -> int:
        \"\"\"A simple helper function.\"\"\"
        return x * 2
    ```

7.  **Ensure the generated filenames match the structure outlined in the implementation plan.** Place code meant for the project's source under `src/` (e.g., `filename=src/main.py`). Do NOT generate test files here; that's the Tester Agent's job.
8.  **Focus only on generating the Python source code files.** Do not add explanatory text outside the code blocks or comments unless it's within the Python code itself.
9.  If the plan is unclear on a specific detail, make a reasonable assumption and add a `# TODO:` comment explaining it.
"""
        return prompt

    def _create_update_prompt(self, impl_content: str, existing_code: dict[str, str], modification_text: str) -> str:
         """Creates the prompt for the generative AI model to update existing code."""

         existing_code_blocks = []
         for filename, code in existing_code.items():
              # Include filename relative to src/
              existing_code_blocks.append(f"```python filename=src/{filename}\n{code}\n```")
         existing_code_section = "\n\n".join(existing_code_blocks) if existing_code_blocks else "*(No existing code found)*"

         prompt = f"""
Refine and update the following existing Python source code based on the provided modification instructions. Ensure the changes align with the overall implementation plan.

**Implementation Plan (impl.md):**
```markdown
{impl_content}
```

**Existing Source Code (from src/):**
{existing_code_section}

**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze the existing code, the implementation plan, and the modification instructions.**
2.  **Apply the requested changes to the relevant Python files.** This might involve adding/removing functions, modifying logic, fixing bugs, refactoring, etc., as instructed.
3.  **Ensure the updated code remains consistent** with the implementation plan and standard Python practices (e.g., syntax, type hints).
4.  **Output the complete, updated versions of ALL modified files.** If a file doesn't need changes based on the instructions, DO NOT include it in the output. If new files are explicitly required by the instructions, generate them.
5.  **Structure the output clearly.** Use Markdown code blocks prefixed with the intended filename relative to the `src/` directory (e.g., `filename=src/main.py`).

    ```python filename=src/some_module.py
    # Updated contents of some_module.py
    # ...
    ```

    ```python filename=src/newly_added_module.py
    # Contents of newly_added_module.py
    # ...
    ```
6.  **Focus only on generating the Python source code files.** Do not add explanatory text outside the code blocks or comments unless it's within the Python code itself.

**Generate the complete, updated Python code blocks for all affected files below:**
"""
         return prompt
    def _parse_code_blocks(self, generated_text: str) -> dict[str, str]:
        """Parses the AI's response to extract code blocks tagged with filenames."""
        # Regex to find ```python filename=path/to/file.py ... ``` blocks
        # It captures the filename and the code content within the block.
        # Handles potential variations in whitespace and ensures non-greedy matching for content.
        pattern = re.compile(r"```python\s+filename=(?P<filename>[^\s`]+)\s*\n(?P<code>.*?)\n```", re.DOTALL | re.IGNORECASE)
        
        files = {}
        matches = pattern.finditer(generated_text)
        
        found_blocks = False
        for match in matches:
            found_blocks = True
            filename = match.group("filename").strip()
            code = match.group("code").strip()
            
            # Validate filename: must contain '/' or end with '.py' (or be a known config file)
            # Allow paths like 'src/module.py', 'utils/helper.py', 'main.py', 'requirements.txt'
            # Reject paths like 'src/' or 'my_dir'
            allowed_root_files = ['.gitignore', '.flaskenv', 'requirements.txt', 'run.py', 'config.py']
            is_valid_py = filename.endswith(".py")
            is_allowed_root = filename in allowed_root_files
            is_nested = os.sep in filename # Check for directory separators

            if filename and code and (is_valid_py or is_allowed_root or is_nested):
                 # Use the full relative path provided by the LLM as the key
                 # Clean up potential leading/trailing slashes just in case
                 clean_filename = filename.strip(os.sep)
                 # Prevent path traversal again
                 if ".." in clean_filename.split(os.sep) or os.path.isabs(clean_filename):
                      self.logger.warning(f"Ignoring parsed block with unsafe path: {filename}")
                      continue

                 files[clean_filename] = code
                 self.logger.info(f"Parsed code block for: {clean_filename}")
            else:
                 self.logger.warning(f"Ignoring parsed block with invalid filename/content: {filename}")

        if not found_blocks:
             self.logger.warning("No code blocks matching the expected format (```python filename=src/...) were found in the AI response.")
             # Attempt a simpler fallback if no structured blocks found?
             # Maybe assume the whole response is a single file if it looks like Python?
             # For now, we rely on the structured format.

        return files