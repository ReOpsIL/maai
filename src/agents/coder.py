
import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import re
from pathlib import Path
import sys # Keep sys for potential future use, though not strictly needed in this snippet
from .base_agent import BaseAgent
import logging # Make sure logging is imported if not already

# Assume logger is configured elsewhere or replace with print/basic logging
logger = logging.getLogger(__name__)
# Configure basic logging if needed for standalone testing
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Helper: Structure Parsing Configuration (similar to scaffolder) ---
TREE_CHARS_PATTERN = r"^[│├└─ L|]+" # Regex to remove tree drawing characters
DIR_MARKER = '/' # Character indicating a directory in the structure text
# --- End Helper Configuration ---


class CoderAgent(BaseAgent):
    """
    Determines project structure, scaffolds directories/files, and generates
    Python code based on the implementation specifications (impl.md).
    Handles both initial creation and updates.
    """

    def run(self, feedback: str | None = None, modification_text: str | None = None, update_mode: bool = False, impl_content: str | None = None):
        """
        Executes the Coder agent's task: structuring the project and generating/updating source files.

        Args:
            feedback: Optional feedback from Reviewer/Tester agents (used in build loop).
            modification_text: Specific instructions for modifying existing code (used for explicit update command).
            update_mode: If True, read existing code and apply modifications based on modification_text.
                         If False, generate structure and code based on impl.md and optional feedback.
            impl_content: Optional pre-read content of impl.md. If None, reads from file.
        """
        self.logger.info(f"Running Coder Agent for project: {self.project_name} (Update Mode: {update_mode})")

        # 1. Read Implementation Plan (Common to both modes)
        if impl_content is None:
            impl_md_path = os.path.join(self.docs_path, "impl.md")
            self.logger.info(f"Reading implementation plan from: {impl_md_path}")
            impl_content = self._read_file(impl_md_path)
            if impl_content is None:
                raise FileNotFoundError(f"Could not read impl.md for project {self.project_name}. Please ensure the Architect Agent ran successfully.")
        else:
             self.logger.info("Using provided implementation plan content.")


        written_files = [] # Keep track of files actually written/updated

        if update_mode:
            # --- UPDATE MODE ---
            if not modification_text:
                 raise ValueError("Modification text is required when running Coder in update mode.")
            self.logger.info(f"Incorporating modification instructions:\n{modification_text}")

            self.logger.info(f"Reading existing source code from project path: {self.project_path}") # Read from project path, not just src
            existing_code = self._read_all_code_files(self.project_path) # Modified to read all files potentially
            if not existing_code:
                 self.logger.warning(f"No existing code found in {self.project_path} to update.")
                 # Allow continuing, LLM might generate files based on instructions anyway

            generated_content = self._generate_or_update_code(
                impl_content=impl_content,
                existing_code=existing_code,
                modification_text=modification_text,
                feedback=None # Feedback is typically for create/build loop, not direct update command
            )
            log_action = "updated"

        else:
            # --- CREATE MODE (Initial or with Feedback) ---
            if feedback:
                self.logger.info(f"Incorporating feedback from review/test:\n{feedback}")

            # 2. Generate and Create Project Structure (Only in Create Mode)
            self.logger.info("Phase 1: Determining and creating project structure...")
            try:
                # Ask Gemini for the structure based on the implementation plan
                structure_text = self._generate_structure_list(impl_content)
                # Parse the text and create directories/empty files
                scaffolded_files = self._create_project_scaffolding(structure_text)
                self.logger.info(f"Successfully scaffolded {len(scaffolded_files)} potential files/dirs.")
            except (ValueError, ConnectionError, RuntimeError, OSError) as e:
                self.logger.error(f"Failed to establish project structure: {e}", exc_info=True)
                raise RuntimeError(f"Coder Agent failed during structure generation: {e}")
            except Exception as e:
                 self.logger.error(f"An unexpected error occurred during structure generation: {e}", exc_info=True)
                 raise RuntimeError(f"An unexpected error occurred in Coder Agent structure phase: {e}")


            # 3. Generate Code Content
            self.logger.info("Phase 2: Generating code content for scaffolded files...")
            generated_content = self._generate_or_update_code(
                impl_content=impl_content,
                existing_code=None, # No existing code for initial creation
                modification_text=None,
                feedback=feedback # Pass feedback for generation
            )
            log_action = "generated"


        # 4. Write Generated/Updated Code Content (Common to both modes)
        if not generated_content:
             self.logger.warning(f"AI did not return any parseable code content. No files were {log_action}.")
             # Decide if this is an error. If structure was created, maybe it's okay?
             # For now, return empty list, but consider raising if critical.
             return [] # No files to write

        self.logger.info(f"Writing {log_action} code files to project path: {self.project_path}")
        written_files = self._write_code_files(generated_content)

        if not written_files:
             self.logger.warning(f"Coder Agent finished but did not produce/update any valid code files after parsing the response.")
             # Consider if this should be an error based on context.

        self.logger.info(f"Coder Agent finished. {len(written_files)} file(s) {log_action}.")
        return written_files

    # ===========================================
    # --- Structure Generation/Creation Phase ---
    # ===========================================

    def _generate_structure_list(self, impl_content: str) -> str:
        """Asks the LLM to generate the directory structure and file list text."""
        if not self.model:
            raise RuntimeError("Generative model not initialized.")

        prompt = self._create_structure_prompt(impl_content)
        self.logger.debug(f"Generated structure prompt for Gemini:\n{prompt[:500]}...")

        try:
            self.logger.info("Sending request to Gemini API for project structure...")
            response = self.model.generate_content(prompt)
            structure_text = response.text
            self.logger.info("Received structure response from Gemini API.")
            self.logger.debug(f"Structure Text (raw):\n{structure_text[:300]}...")
            if not structure_text or not structure_text.strip():
                raise ValueError("Gemini returned an empty response for the project structure.")
            return structure_text
        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Structure): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for structure generation: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Gemini API call (Structure): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate structure using AI: {e}")

    def _create_structure_prompt(self, impl_content: str) -> str:
        """Creates the prompt to ask the LLM for the project directory structure."""
        return f"""
Based on the following implementation plan (impl.md), generate the complete directory structure and file list for the project.

**Implementation Plan (from impl.md):**
```markdown
{impl_content}
```

**Instructions for Output Format:**

1.  **List all necessary directories and files.**
2.  **Use indentation (4 spaces)** to represent the hierarchy (subdirectories and files within directories).
3.  **Clearly mark directories** by appending a forward slash (`{DIR_MARKER}`) to their names.
4.  **Include all source files** (e.g., `.py`), configuration files (e.g., `requirements.txt`, `.gitignore`, `Dockerfile`), documentation files (`README.md`), etc., mentioned or implied by the plan.
5.  **Do NOT include generated code content here.** Only provide the file and directory names in a tree structure.
6.  Start the structure from the project's root directory. Assume the project name itself is the root.

**Example Output Format:**

```text
my_project_root/
    src/
        __init__.py
        main.py
        utils/
            __init__.py
            helpers.py
    tests/
        __init__.py
        test_main.py
    .gitignore
    README.md
    requirements.txt
    Dockerfile
```

**Generate the directory structure and file list now:**
"""

    def _parse_structure_text(self, structure_text: str) -> list[tuple[str, bool]]:
        """
        Parses the text-based tree structure into a list of (relative_path, is_directory) tuples.
        Adapted from the coder_agent_scaffolder script logic.
        """
        items = []
        lines = structure_text.strip().splitlines()
        if not lines:
            return items

        # Very basic indent detection (assumes first indented line sets the standard)
        indent_unit = 4 # Default or detect like in scaffolder
        first_indent = next((len(line) - len(line.lstrip(' ')) for line in lines if line.strip() and line[0] == ' '), 0)
        if first_indent > 0:
            indent_unit = first_indent # Simple assumption
            self.logger.debug(f"Detected indent unit: {indent_unit}")


        level_paths = { -1: "" } # Store parent path segments for each level

        for i, line in enumerate(lines):
            line_num = i + 1
            original_line = line
            line = line.rstrip() # Remove trailing whitespace

            if not line.strip():
                continue

            # --- Simple Parsing Logic (adjust if needed based on LLM output) ---
            leading_spaces = len(line) - len(line.lstrip(' '))
            level = 0
            if indent_unit > 0:
                 # Handle potential non-multiple indents gracefully
                 level = round(leading_spaces / indent_unit)

            # Clean name: remove tree chars, strip surrounding whitespace
            cleaned_name = re.sub(TREE_CHARS_PATTERN, '', line).strip()

            is_dir = cleaned_name.endswith(DIR_MARKER)
            item_name = cleaned_name.rstrip(DIR_MARKER) if is_dir else cleaned_name

            if not item_name:
                self.logger.warning(f"Line {line_num}: Could not parse item name from: '{original_line}'. Skipping.")
                continue

            # --- Build Relative Path ---
            parent_level = level - 1
            parent_rel_path = level_paths.get(parent_level)

            if parent_rel_path is None:
                 # Try to find the closest shallower level path if direct parent missing
                 closest_level = max((lvl for lvl in level_paths if lvl < level), default=-1)
                 parent_rel_path = level_paths.get(closest_level, "") # Fallback to root
                 self.logger.warning(f"Line {line_num}: Parent at level {parent_level} not found for '{item_name}'. Using path from level {closest_level} ('{parent_rel_path}') instead. Check indentation consistency.")
                 # Update effective level based on chosen parent for path building
                 level = closest_level + 1


            # Construct relative path using os.path.join for cross-platform compatibility
            # Ensure parent_rel_path is treated correctly if it's empty (root)
            current_rel_path = os.path.join(parent_rel_path, item_name) if parent_rel_path else item_name

            # Prevent path traversal issues early
            if ".." in item_name or os.path.isabs(item_name):
                 self.logger.warning(f"Skipping item with potentially unsafe name component: '{item_name}'")
                 continue

            items.append((current_rel_path, is_dir))

            if is_dir:
                level_paths[level] = current_rel_path
                # Clean deeper levels
                levels_to_remove = [lvl for lvl in level_paths if lvl > level]
                for lvl in levels_to_remove:
                    del level_paths[lvl]
            # --- End Simple Parsing Logic ---

        return items


    def _create_project_scaffolding(self, structure_text: str) -> list[str]:
        """
        Parses structure text and creates directories and empty files in self.project_path.
        Returns a list of relative paths of created files (not dirs).
        """
        base_path = Path(self.project_path).resolve()
        self.logger.info(f"Target base directory for scaffolding: {base_path}")

        if base_path.exists() and not base_path.is_dir():
            raise OSError(f"Base path '{base_path}' exists but is not a directory.")

        try:
            base_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(f"Could not create base directory '{base_path}': {e}")

        parsed_items = self._parse_structure_text(structure_text)
        created_files = [] # Track relative paths of files touched

        self.logger.info("--- Creating Scaffolding ---")
        for rel_path, is_dir in parsed_items:
            # Important: Ensure rel_path is treated as relative to base_path
            current_path = base_path / rel_path

            try:
                 display_path_rel = current_path.relative_to(base_path.parent)
            except ValueError:
                 display_path_rel = current_path # Fallback

            try:
                if is_dir:
                     if current_path.exists() and not current_path.is_dir():
                         self.logger.warning(f"Path exists but is a file, expected directory: {display_path_rel}. Skipping directory creation.")
                         continue
                     current_path.mkdir(parents=True, exist_ok=True)
                     # Log only if actually created something new? os.makedirs handles exist_ok
                     # self.logger.info(f"Ensured directory exists: {display_path_rel}")
                else: # It's a file
                     # Ensure parent directory exists first
                     parent_dir = current_path.parent
                     if not parent_dir.exists():
                         # This should ideally not happen if dirs are listed first in structure_text
                         # but create defensively.
                         parent_dir.mkdir(parents=True, exist_ok=True)
                         self.logger.info(f"Created missing parent directory: {parent_dir.relative_to(base_path.parent)}")

                     if current_path.exists():
                          if current_path.is_dir():
                              self.logger.warning(f"Path exists but is a directory, expected file: {display_path_rel}. Skipping file creation.")
                              continue
                          else:
                              # File exists, maybe log it? Don't overwrite here.
                              # self.logger.debug(f"File exists: {display_path_rel}")
                              pass # Content generation will handle overwriting
                     else:
                         current_path.touch(exist_ok=True) # Create empty file
                         self.logger.info(f"Created empty file: {display_path_rel}")

                     created_files.append(rel_path) # Add relative path of the file

            except OSError as e:
                 self.logger.error(f"Could not create '{display_path_rel}': {e}", exc_info=True)
                 # Decide whether to continue or raise. Let's continue for now.
            except Exception as e:
                 self.logger.error(f"Unexpected error creating '{display_path_rel}': {e}", exc_info=True)

        self.logger.info("--- Scaffolding Complete ---")
        return created_files


    # ===========================================
    # --- Code Generation/Update Phase ---
    # ===========================================

    def _read_all_code_files(self, start_path: str) -> dict[str, str]:
        """Recursively reads all files (not just .py) from a directory for the update prompt."""
        code_files = {}
        base_path = Path(start_path)
        if not base_path.is_dir():
            return code_files

        for item in base_path.rglob('*'): # Recursively find all items
            if item.is_file():
                try:
                    # Calculate path relative to the starting path
                    relative_path = str(item.relative_to(base_path))
                    # Use os specific separators for dictionary keys? Match LLM format?
                    # Let's use POSIX-style separators for keys, as often used in web/LLMs
                    relative_path_posix = relative_path.replace(os.sep, '/')

                    content = self._read_file(str(item)) # Read file using existing helper
                    if content is not None:
                        code_files[relative_path_posix] = content
                except Exception as e:
                    # Log error but continue reading other files
                    self.logger.error(f"Error reading file {item} for update context: {e}", exc_info=False) # Keep log brief

        return code_files


    def _generate_or_update_code(self, impl_content: str, existing_code: dict[str, str] | None, modification_text: str | None, feedback: str | None) -> dict[str, str]:
        """Uses Generative AI to create or update the code content for ALL files."""
        if not self.model:
            raise RuntimeError("Generative model not initialized.")

        is_update = bool(existing_code and modification_text)

        if is_update:
             prompt = self._create_update_prompt(impl_content, existing_code, modification_text)
             self.logger.debug(f"Generated update prompt for Gemini (Coder):\n{prompt[:500]}...")
        else:
             prompt = self._create_code_generation_prompt(impl_content, feedback) # Renamed from _create_prompt
             self.logger.debug(f"Generated create/feedback prompt for Gemini (Coder):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to Gemini API for code content generation/update...")
            # Consider increasing max output tokens if needed
            # generation_config = genai.types.GenerationConfig(max_output_tokens=16384) # Example
            # response = self.model.generate_content(prompt, generation_config=generation_config)
            response = self.model.generate_content(prompt)

            generated_text = response.text
            self.logger.info("Received code generation/update response from Gemini API.")
            self.logger.debug(f"Generated Text (first 200 chars):\n{generated_text[:200]}...")

            # --- Parsing the generated text into files ---
            # Use the existing robust parser
            code_files = self._parse_code_blocks(generated_text)
            if not code_files:
                 # This is more critical now, as it means no code was generated/updated
                 self.logger.warning("AI response parsed, but no valid code blocks (```python filename=...```) found.")
                 # Returning empty dict, the caller handles the warning/error.

            return code_files

        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Gemini API Error (Code Gen/Update): {e}", exc_info=True)
            raise ConnectionError(f"Gemini API request failed for code generation/update: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Gemini API call (Code Gen/Update): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate/update code using AI: {e}")

    def _create_code_generation_prompt(self, impl_content: str, feedback: str | None) -> str: # Renamed
        """Creates the prompt for the generative AI model to generate code for ALL files from scratch or based on feedback."""
        feedback_section = ""
        if feedback:
            feedback_section = f"""
**Incorporate the following feedback from the previous Review/Test cycle:**
```
{feedback}
```
Address these points specifically in the generated code for the relevant files.
"""

        prompt = f"""
Generate the complete, runnable code content for ALL necessary files for the project described in the following implementation plan (impl.md). Adhere strictly to the plan's specifications regarding modules, classes, methods, file structure, and overall architecture.

**Implementation Plan (from impl.md):**
```markdown
{impl_content}
```
{feedback_section}
**Instructions:**

1.  **Generate the full content for ALL required files.** This includes Python source files (`.py`), configuration files (`requirements.txt`, `.gitignore`, `Dockerfile`, etc.), `README.md`, and any other files specified or implied by the implementation plan.
2.  **Use Python 3.9+ syntax, including type hints** as specified in the plan for `.py` files.
3.  **Implement all core logic, classes, functions, etc.** defined in the plan. Include basic error handling where appropriate (e.g., file I/O, network requests).
4.  **Add necessary import statements** at the beginning of each Python file.
5.  **Include basic docstrings** for Python classes and functions.
6.  **Structure the output using Markdown code blocks.** Each block MUST be prefixed with the intended relative filename from the project root, like this:

    ```python filename=src/some_module.py
    # Contents of src/some_module.py
    import os

    def main():
        print("Hello from some_module!")

    if __name__ == "__main__":
        main()
    ```

    ```text filename=requirements.txt
    flask>=2.0
    requests
    ```

    ```markdown filename=README.md
    # My Project
    This project does X, Y, Z.
    ```

    ```text filename=.gitignore
    __pycache__/
    *.pyc
    .env
    ```
7.  **Ensure the `filename=` paths are relative to the project root** and match the structure outlined or implied in the implementation plan (e.g., `src/main.py`, `tests/test_app.py`, `README.md`).
8.  **Do NOT add explanatory text outside the formatted code blocks.** Focus solely on generating the file contents within their respective blocks.
9.  If the plan is unclear, make a reasonable assumption and add a `# TODO:` comment in the Python code or a note in other file types.
10. **Generate ALL files in a single response.**
"""
        return prompt

    def _create_update_prompt(self, impl_content: str, existing_code: dict[str, str], modification_text: str) -> str:
         """Creates the prompt for the generative AI model to update existing code based on instructions."""

         existing_code_blocks = []
         for filename, code in existing_code.items():
              # Determine language hint for markdown block
              lang = "python" # Default
              ext = os.path.splitext(filename)[1].lower()
              if ext == ".txt" or "requirements" in filename or ".gitignore" in filename or ".env" in filename:
                  lang = "text"
              elif ext == ".md":
                  lang = "markdown"
              elif ext == ".json":
                  lang = "json"
              elif ext == ".yaml" or ext == ".yml":
                  lang = "yaml"
              elif "dockerfile" in filename.lower():
                   lang = "dockerfile"
              # Add more language hints as needed

              # Use the relative path (posix style) as provided by _read_all_code_files
              existing_code_blocks.append(f"```{lang} filename={filename}\n{code}\n```")

         existing_code_section = "\n\n".join(existing_code_blocks) if existing_code_blocks else "*(No existing code found)*"

         prompt = f"""
Refine and update the following existing project files based on the provided modification instructions. Ensure the changes align with the overall implementation plan.

**Implementation Plan (impl.md):**
```markdown
{impl_content}
```

**Existing Project Files:**
{existing_code_section}

**User's Modification Instructions:**
"{modification_text}"

**Task:**

1.  **Analyze the existing files, the implementation plan, and the modification instructions.**
2.  **Apply the requested changes to the relevant files.** This might involve adding/removing functions/sections, modifying logic, fixing bugs, refactoring, updating dependencies, changing configurations, etc., as instructed.
3.  **Ensure the updated code/content remains consistent** with the implementation plan and appropriate syntax/formatting for each file type.
4.  **Output the complete, updated versions of ALL modified files.** If a file doesn't need changes based on the instructions, DO NOT include it in the output. If new files are explicitly required by the instructions and the plan, generate them.
5.  **Structure the output using Markdown code blocks.** Each block MUST be prefixed with the correct language hint (`python`, `text`, `markdown`, etc.) and the intended relative filename from the project root (e.g., `filename=src/main.py`, `filename=requirements.txt`).

    ```python filename=src/some_module.py
    # Updated contents of src/some_module.py
    # ...
    ```

    ```text filename=requirements.txt
    # Updated requirements
    flask>=2.1
    requests
    new_dependency==1.0
    ```

6.  **Focus only on generating the file contents.** Do not add explanatory text outside the formatted code blocks.

**Generate the complete, updated code/content blocks for all affected files below:**
"""
         return prompt

    # ===========================================
    # --- File Parsing and Writing ---
    # ===========================================

    def _parse_code_blocks(self, generated_text: str) -> dict[str, str]:
        """
        Parses the AI's response to extract code blocks tagged with filenames.
        Uses a more general regex to capture various language hints.
        """
        # Regex to find ```lang filename=path/to/file ... ``` blocks
        # Captures optional language hint, filename, and code content.
        pattern = re.compile(
            r"```(?P<lang>\w+)?\s+filename=(?P<filename>[^\s`]+)\s*\n" # Start fence, lang (optional), filename
            r"(?P<code>.*?)\n"                                         # Code content (non-greedy)
            r"```",                                                    # End fence
            re.DOTALL | re.IGNORECASE
        )

        files = {}
        matches = pattern.finditer(generated_text)
        found_blocks = False
        for match in matches:
            found_blocks = True
            # Use POSIX paths for keys internally for consistency
            filename = match.group("filename").strip().replace(os.sep, '/')
            code = match.group("code").strip()

            # Basic validation and path safety checks
            if not filename or not code:
                 self.logger.warning(f"Ignoring parsed block with empty filename or code.")
                 continue

            # Clean up potential leading/trailing slashes from filename
            clean_filename = filename.strip('/')

            # Prevent path traversal and absolute paths
            path_parts = clean_filename.split('/')
            if ".." in path_parts or os.path.isabs(clean_filename):
                 self.logger.warning(f"Ignoring parsed block with unsafe path: {filename}")
                 continue

            # Check if filename seems plausible (e.g., has an extension or is a known config)
            # This is a heuristic check, might need refinement
            if '.' not in path_parts[-1] and clean_filename not in ['.gitignore', 'Dockerfile']: # Allow extensionless files like Dockerfile
                 if len(path_parts) == 1: # Allow simple names like 'run' if needed, but maybe warn?
                      self.logger.debug(f"Parsed block for potentially extensionless root file: {clean_filename}")
                 elif not clean_filename.endswith('/'): # If it ends with /, it was likely meant as a dir by mistake
                     self.logger.warning(f"Ignoring parsed block with potentially invalid filename (no extension?): {clean_filename}")
                     continue

            files[clean_filename] = code
            self.logger.info(f"Parsed content block for: {clean_filename}")


        if not found_blocks:
             self.logger.warning("No code/content blocks matching the expected format (```[lang] filename=...```) were found in the AI response.")

        return files

    def _write_code_files(self, generated_files: dict[str, str]) -> list[str]:
        """Writes the generated code content to the appropriate files."""
        written_files_list = []
        base_path = Path(self.project_path).resolve()

        for relative_path_posix, code_content in generated_files.items():
            # Convert POSIX path key back to OS-specific path for writing
            relative_path_os = os.path.join(*relative_path_posix.split('/'))
            full_path = base_path / relative_path_os

            try:
                 display_path_rel = full_path.relative_to(base_path.parent)
            except ValueError:
                 display_path_rel = full_path

            try:
                # Ensure the parent directory exists (critical step)
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the file content
                self._write_file(str(full_path), code_content) # Use existing helper
                written_files_list.append(str(full_path)) # Store full path of written file
                self.logger.info(f"Successfully wrote content to {display_path_rel}")

            except OSError as e:
                self.logger.error(f"Error writing file '{display_path_rel}': {e}", exc_info=True)
                # Decide whether to continue or raise. Let's log and continue.
            except Exception as e:
                 self.logger.error(f"Unexpected error writing file '{display_path_rel}': {e}", exc_info=True)

        return written_files_list
