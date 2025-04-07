**Key Changes and Explanations:**

1.  **`run` Method Orchestration:**
    *   The `run` method now clearly distinguishes between `update_mode` and create mode.
    *   In **create mode**, it first calls `_generate_structure_list` and `_create_project_scaffolding`. Then it calls `_generate_or_update_code` to get the content.
    *   In **update mode**, it skips structure generation, reads existing files using the new `_read_all_code_files`, and calls `_generate_or_update_code` with `existing_code` and `modification_text`.
    *   The final step, writing files using `_write_code_files`, is common to both modes.

2.  **Structure Generation (`_generate_structure_list`, `_create_structure_prompt`):**
    *   New methods dedicated to asking the LLM for the structure text.
    *   The prompt specifically asks for a text tree format with indentation and directory markers (`/`).

3.  **Structure Parsing (`_parse_structure_text`):**
    *   Adapted from the scaffolder script's logic to parse the text tree.
    *   It handles indentation to determine hierarchy and builds relative paths.
    *   Includes basic error handling for unparseable lines or inconsistent indentation.
    *   Returns a list of `(relative_path, is_directory)` tuples.

4.  **Scaffolding Creation (`_create_project_scaffolding`):**
    *   Takes the parsed structure items.
    *   Uses `pathlib.Path` to create directories (`mkdir(parents=True, exist_ok=True)`) and empty files (`touch(exist_ok=True)`).
    *   Handles cases where paths might already exist (e.g., a file where a directory is expected).

5.  **Code Generation Prompts (`_create_code_generation_prompt`, `_create_update_prompt`):**
    *   The **create** prompt (`_create_code_generation_prompt`) now explicitly asks for *all* file contents (Python, requirements, README, etc.) in the specified Markdown block format, using filenames relative to the project root.
    *   The **update** prompt (`_create_update_prompt`) is enhanced:
        *   It now includes *all* files found by `_read_all_code_files` in the context.
        *   It tries to add language hints (like `python`, `text`, `markdown`) to the Markdown code blocks for existing code, which helps the LLM.
        *   It instructs the LLM to output *only* the changed/new files, using the correct relative paths and language hints.

6.  **Reading Existing Code (`_read_all_code_files`):**
    *   Modified to recursively read *all* files within the `start_path` (typically `self.project_path`), not just `.py` files in `src/`. This is crucial for the update prompt to have full context.
    *   Stores files using POSIX-style relative paths as keys for consistency with LLM interactions.

7.  **Parsing Code Blocks (`_parse_code_blocks`):**
    *   The regex is slightly updated to be more general and capture optional language hints (` ```[lang] filename=... ``` `).
    *   Continues to perform path safety checks (no `..`, no absolute paths).
    *   Uses POSIX paths internally.

8.  **Writing Code Files (`_write_code_files`):**
    *   A new helper method dedicated to iterating through the `generated_files` dictionary returned by `_parse_code_blocks`.
    *   Converts the POSIX-style relative path keys back to OS-specific paths using `os.path.join`.
    *   Uses the existing `_write_file` helper (which should handle directory creation).
    *   Returns a list of the full paths of the files successfully written.

9.  **Path Handling:** Emphasizes using `os.path.join` or `pathlib` for creating paths to ensure cross-platform compatibility. Internally uses POSIX separators (`/`) for keys in dictionaries passed to/from parsing/LLM steps for consistency.

10. **Dummy Model & Testing:** The `if __name__ == '__main__':` block includes a `DummyModel` within a `BaseAgent` mock to simulate Gemini responses for both structure and code generation/updates, allowing basic testing of the agent's flow without actual API calls.
