import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import re
import subprocess
import sys
import shutil
from .base_agent import BaseAgent

class TesterAgent(BaseAgent):
    """
    Generates and executes unit/integration tests based on the implementation
    details (impl.md) and the generated source code.
    """

    def run(self, modification_text: str | None = None, update_mode: bool = False, impl_content: str | None = None) -> list[str]:
        """
        Executes the Tester agent's task: generating or updating test files.
        Does NOT execute the tests.

        Args:
            modification_text: Specific instructions for modifying existing tests
                               (used when update_mode is True).
            update_mode: If True, read existing tests and source code, apply modifications.
                         If False, generate new tests based on source code and impl.md.
            impl_content: Optional pre-read content of impl.md. If None, reads from file.

        Returns:
            A list of absolute paths to the generated or updated test files.
        """
        self.logger.info(f"Running Tester Agent for project: {self.project_name} (Update Mode: {update_mode})")
        if update_mode and not modification_text:
             raise ValueError("Modification text is required when running Tester in update mode.")
        # Read impl.md content if not provided
        if impl_content is None:
            impl_md_path = os.path.join(self.docs_path, "impl.md")
            self.logger.info(f"Reading implementation plan from: {impl_md_path}")
            impl_content = self._read_file(impl_md_path)
            if impl_content is None:
                self.logger.warning(f"Could not read impl.md for project {self.project_name}. Test generation context might be limited.")
                impl_content = "# Implementation Plan Not Available\nGenerate tests based solely on the provided source code."
        else:
             self.logger.info("Using provided implementation plan content.")
        # --- Read Context (Source Code, Existing Tests if updating) ---
        self.logger.info(f"Reading source code from: {self.src_path}")
        source_code_content = self._read_source_code()
        if not source_code_content:
             self.logger.warning(f"No source code found in {self.src_path}. Test generation/update might be ineffective.")
             # Allow proceeding, but AI might struggle

        existing_tests = None
        if update_mode:
            self.logger.info(f"Reading existing tests from: {self.tests_path}")
            existing_tests = self._read_existing_tests()
            if not existing_tests:
                 self.logger.warning(f"No existing tests found in {self.tests_path} to update.")
                 # Proceed, but it's effectively generation mode based on source + modification text

        # --- Generate or Update Test Cases ---
        self.logger.info("Attempting to generate or update test cases using AI.")
        generated_test_files_content = {}
        try:
            generated_test_files_content = self._generate_or_update_tests(
                impl_content=impl_content,
                source_code=source_code_content,
                existing_tests=existing_tests,
                modification_text=modification_text
            )
            log_action = "updated" if update_mode and existing_tests else "generated"
            self.logger.info(f"Successfully {log_action} content for {len(generated_test_files_content)} test file(s) using AI.")

        except (ValueError, ConnectionError, RuntimeError) as e:
            self.logger.error(f"Failed to generate/update tests using AI: {e}")
            raise RuntimeError(f"Tester Agent failed during test generation/update: {e}") # Re-raise to signal failure
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during test generation/update: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred during test generation/update: {e}")

        if not generated_test_files_content:
            self.logger.warning("AI did not generate any test file content.")
            # Return empty list, indicating no files were written/updated
            return []
        # --- Write Test Files ---
        self.logger.info(f"Writing generated test files to: {self.tests_path}")
        written_test_files = []
        try:
            self._ensure_dir_exists(self.tests_path)
            for file_name, code_content in generated_test_files_content.items():
                # Basic validation/sanitization
                safe_file_name = re.sub(r'[^\w\.\-_]', '', file_name)
                if not safe_file_name.startswith("test_"):
                    safe_file_name = f"test_{safe_file_name}" # Ensure it starts with test_
                if not safe_file_name.endswith(".py"):
                    safe_file_name += ".py"

                file_path = os.path.join(self.tests_path, safe_file_name)
                self._write_file(file_path, code_content)
                written_test_files.append(file_path)
                self.logger.info(f"Successfully wrote {file_path}")

        except Exception as e:
            # Error logged by _write_file or _ensure_dir_exists
            raise IOError(f"Tester Agent failed to write test files: {e}")
        if not written_test_files:
              self.logger.warning("Test content was generated but no valid test files could be written.")
              # Return empty list as no files were actually written
              return []

        # Return the list of successfully written file paths
        return written_test_files
    def _read_source_code(self) -> dict[str, str]:
        """Reads all .py files from the project's src directory."""
        code_files = {}
        if not os.path.isdir(self.src_path):
            self.logger.warning(f"Source directory not found: {self.src_path}")
            return code_files

        try:
            for filename in os.listdir(self.src_path):
                if filename.endswith(".py"):
                    file_path = os.path.join(self.src_path, filename)
                    content = self._read_file(file_path)
                    if content is not None:
                        # Store with path relative to project root (e.g., src/module.py)
                        relative_path = os.path.relpath(file_path, self.project_path)
                        code_files[relative_path] = content
        except Exception as e:
            self.logger.error(f"Error reading source code files from {self.src_path}: {e}", exc_info=True)
        return code_files

    def _read_existing_tests(self) -> dict[str, str]:
        """Reads all .py files from the project's tests directory."""
        test_files = {}
        if not os.path.isdir(self.tests_path):
            return test_files # Return empty if tests dir doesn't exist

        try:
            for filename in os.listdir(self.tests_path):
                if filename.endswith(".py") and filename.startswith("test_"):
                    file_path = os.path.join(self.tests_path, filename)
                    content = self._read_file(file_path)
                    if content is not None:
                        # Store with filename relative to tests/
                        test_files[filename] = content
        except Exception as e:
            self.logger.error(f"Error reading existing test files from {self.tests_path}: {e}", exc_info=True)
        return test_files

    def _generate_or_update_tests(self, impl_content: str, source_code: dict[str, str], existing_tests: dict[str, str] | None, modification_text: str | None) -> dict[str, str]:
        """Uses Generative AI to create or update pytest test cases."""
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("TesterAgent requires a configured Generative Model.")

        if existing_tests and modification_text:
             # Update mode
             prompt = self._create_update_test_prompt(impl_content, source_code, existing_tests, modification_text)
             self.logger.debug(f"Generated update prompt for Gemini (Tester):\n{prompt[:500]}...")
        else:
             # Create mode
             prompt = self._create_test_prompt(impl_content, source_code)
             self.logger.debug(f"Generated create prompt for Gemini (Tester):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to Gemini API for test generation...")
            # May need higher token limits for tests + source code context
            # generation_config = genai.types.GenerationConfig(max_output_tokens=8192)
            # response = model.generate_content(prompt, generation_config=generation_config)
            response = self.model.generate_content(prompt)
            generated_text = response.text
            self.logger.info("Received test generation response from Gemini API.")
            self.logger.debug(f"Generated Test Text (first 200 chars):\n{generated_text[:200]}...")

            test_files = self._parse_code_blocks(generated_text) # Use same parser as Coder
            if not test_files:
                self.logger.warning("AI response parsed, but no valid test code blocks found.")

            return test_files

        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Tester): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for test generation: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Gemini API call (Tester): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate tests using AI: {e}")

    def _create_test_prompt(self, impl_content: str, source_code: dict[str, str]) -> str: # For initial creation
        """Creates the prompt for the generative AI model to generate tests from scratch."""

        source_code_blocks = []
        for path, code in source_code.items():
            source_code_blocks.append(f"```python filename={path}\n{code}\n```")
        source_code_section = "\n\n".join(source_code_blocks)

        prompt = f"""
Generate Python unit tests using the `pytest` framework based on the following implementation plan and source code.

**Implementation Plan (from impl.md):**
```markdown
{impl_content}
```

**Source Code (from src/):**
{source_code_section}

**Instructions:**

1.  **Generate pytest test files.** Ensure filenames start with `test_` (e.g., `test_main.py`, `test_utils.py`).
2.  **Focus on testing the public functions/methods** defined in the source code and implementation plan.
3.  **Cover key functionalities and edge cases** described or implied in the plan.
4.  **Use `pytest` fixtures** for setup/teardown where appropriate (e.g., mocking external APIs, creating temporary files). Use `unittest.mock` for mocking.
5.  **Include necessary import statements** for `pytest`, `unittest.mock`, and the modules being tested (e.g., `from ..src import main_module`). Assume the tests run from the project root or that the `src` directory is in `PYTHONPATH`. Adjust imports like `from src.module import function`.
6.  **Write clear assertions** using `assert`.
7.  **Structure the output clearly.** Use Markdown code blocks prefixed with the intended filename relative to the `tests/` directory:

    ```python filename=tests/test_some_module.py
    # Contents of tests/test_some_module.py
    import pytest
    from unittest.mock import patch
    from src.some_module import main_function # Adjust import based on project structure

    def test_main_function_success():
        # ... test logic ...
        assert main_function(arg1="value") == "expected_result"

    @patch('src.some_module.external_call')
    def test_main_function_with_mock(mock_external_call):
        mock_external_call.return_value = "mocked_data"
        # ... test logic ...
        assert main_function(arg1="value2") == "expected_with_mock"
    ```

8.  **Generate only the test code files.** Do not add explanatory text outside the code blocks unless it's within the Python code itself.
9.  If the plan or code is ambiguous, make reasonable assumptions for testing and add a `# TODO:` comment if necessary.
"""
        return prompt

    def _create_update_test_prompt(self, impl_content: str, source_code: dict[str, str], existing_tests: dict[str, str], modification_text: str) -> str:
         """Creates the prompt for the generative AI model to update existing tests."""

         source_code_blocks = []
         for path, code in source_code.items():
              # Use path relative to project root (e.g., src/module.py)
              source_code_blocks.append(f"```python filename={path}\n{code}\n```")
         source_code_section = "\n\n".join(source_code_blocks) if source_code_blocks else "*(No source code found)*"

         existing_test_blocks = []
         for filename, code in existing_tests.items():
              # Use filename relative to tests/ (e.g., test_module.py)
              existing_test_blocks.append(f"```python filename=tests/{filename}\n{code}\n```")
         existing_tests_section = "\n\n".join(existing_test_blocks) if existing_test_blocks else "*(No existing tests found)*"


         prompt = f"""
Refine and update the following existing Python `pytest` tests based on the provided modification instructions. Ensure the tests align with the implementation plan and the current source code.

**Implementation Plan (impl.md):**
```markdown
{impl_content}
```

**Current Source Code (from src/):**
{source_code_section}

**Existing Tests (from tests/):**
{existing_tests_section}

**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze the existing tests, source code, implementation plan, and modification instructions.**
2.  **Apply the requested changes to the relevant test files.** This might involve adding new tests, modifying existing ones, removing obsolete tests, improving mocks, or fixing assertions based on the instructions or changes in source code.
3.  **Ensure the updated tests are valid `pytest` tests** and correctly target the current source code. Maintain good testing practices.
4.  **Output the complete, updated versions of ALL modified test files.** If a test file doesn't need changes based on the instructions, DO NOT include it in the output. If new test files are explicitly required, generate them.
5.  **Structure the output clearly.** Use Markdown code blocks prefixed with the intended filename relative to the `tests/` directory (e.g., `filename=tests/test_main.py`). Ensure filenames start with `test_`.

    ```python filename=tests/test_some_module.py
    # Updated contents of tests/test_some_module.py
    # ...
    ```
6.  **Focus only on generating the Python test code files.** Do not add explanatory text outside the code blocks.

**Generate the complete, updated Python test code blocks for all affected files below:**
"""
         return prompt
    def _parse_code_blocks(self, generated_text: str) -> dict[str, str]:
        """Parses the AI's response to extract test code blocks tagged with filenames."""
        # Regex to find ```python filename=path/to/test_file.py ... ``` blocks
        pattern = re.compile(r"```python\s+filename=(?P<filename>[^\s`]+)\s*\n(?P<code>.*?)\n```", re.DOTALL | re.IGNORECASE)
        files = {}
        matches = pattern.finditer(generated_text)
        found_blocks = False
        for match in matches:
            found_blocks = True
            filename = match.group("filename").strip()
            code = match.group("code").strip()

            # Ensure filename is plausible, starts with tests/, and code is not empty
            # Ensure filename is plausible, starts with tests/, ends with .py and code is not empty
            if filename and code and filename.startswith("tests/") and filename.endswith(".py"):
                relative_filename = filename[len("tests/"):] # Get path relative to tests/ dir
                if relative_filename and relative_filename.startswith("test_"): # Ensure it starts with test_
                    files[relative_filename] = code
                    self.logger.info(f"Parsed test code block for: {relative_filename}")
                else:
                    self.logger.warning(f"Ignoring test block with invalid filename (must start with 'test_'): {filename}")
            else:
                 self.logger.warning(f"Ignoring parsed block with invalid path (must be 'tests/test_*.py'), filename, or empty content: {filename}")

        if not found_blocks:
             self.logger.warning("No code blocks matching the expected format (```python filename=tests/test_*.py...) were found in the AI response.")
        return files

    def _run_tests(self) -> tuple[bool, str]:
        """Runs pytest using subprocess."""
        # Ensure pytest is available
        pytest_path = shutil.which("pytest")
        if not pytest_path:
            self.logger.error("pytest command not found in PATH. Cannot execute tests.")
            return False, "pytest command not found. Please install it (`pip install pytest`)."

        # Command to run pytest from the project's root directory
        # This helps pytest discover the 'src' directory for imports
        command = [pytest_path, "-v"] # Add '-v' for verbose output

        self.logger.debug(f"Executing command: {' '.join(command)} in cwd: {self.project_path}")

        try:
            process = subprocess.run(
                command,
                cwd=self.project_path, # Run pytest from the project root
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=False # Don't raise exception on non-zero exit (failure)
            )

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()
            output = f"--- STDOUT ---\n{stdout}\n\n--- STDERR ---\n{stderr}".strip()
            self.logger.debug(f"Pytest Output:\n{output}")

            if process.returncode == 0:
                self.logger.info("Pytest execution successful, all tests passed.")
                return True, output
            else:
                # Check for specific exit codes if needed (e.g., 5 means no tests found)
                if process.returncode == 5:
                     self.logger.warning("Pytest exited with code 5: No tests were collected.")
                     # Decide if this is a pass or fail. Let's treat as pass if test files were generated but empty/invalid.
                     # If no test files were generated at all, previous steps handled it.
                     return True, output + "\n\nWarning: Pytest found no tests to run."
                else:
                     self.logger.warning(f"Pytest execution failed with exit code {process.returncode}.")
                     return False, output

        except FileNotFoundError:
            self.logger.error(f"Failed to execute 'pytest'. Is it installed and in the PATH?")
            return False, "Failed to execute pytest. Check installation."
        except Exception as e:
            self.logger.error(f"An error occurred while running pytest: {e}", exc_info=True)
            return False, f"An unexpected error occurred during test execution: {e}"