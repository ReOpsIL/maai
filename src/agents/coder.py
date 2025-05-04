
import os


import re
from pathlib import Path
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

source_code_extensions = [
    # Java / Kotlin / Android
    ".java", ".class", ".jar", ".kt", ".kts", ".xml", ".gradle", ".pro", ".aidl", ".smali", ".dex",

    # iOS / Swift / Objective-C
    ".swift", ".m", ".h", ".mm", ".plist", ".xib", ".storyboard", ".xcconfig", ".entitlements",

    # JavaScript / TypeScript / Web
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".html", ".htm",
    ".css", ".scss", ".sass", ".less", ".ejs", ".hbs", ".pug", ".jade", ".twig", ".liquid", ".md",

    # Node.js / Config
    ".env", ".yml", ".yaml",

    # Flutter / Dart
    ".dart",

    # React Native / Cross-platform
    # (Already included: .js, .jsx, .ts, .tsx, .json)

    # Xamarin / C#
    ".cs", ".xaml",

    # C / C++
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".ino",

    # Rust
    ".rs",  # Plus Cargo.toml and Cargo.lock (not extensions)

    # Python
    ".py", ".pyi", ".ipynb",

    # Go
    ".go",  # go.mod and go.sum are not extensions

    # Ruby
    ".rb", ".erb",

    # PHP
    ".php", ".phtml",

    # Shell / Scripting
    ".sh", ".bash", ".bat", ".ps1",

    # Perl
    ".pl", ".pm",

    # Lisp / Clojure
    ".lisp", ".el", ".scm", ".clj",

    # Julia
    ".jl",

    # Assembly
    ".asm", ".s", ".S",

    # Misc Config / Meta Files
    ".toml", ".ini", ".cfg"
]

programing_extensions = [
    # Java / Kotlin / Android
    ".java",  ".kt", 
    # iOS / Swift / Objective-C
    ".swift", ".m", ".h", ".mm", 

    # JavaScript / TypeScript / Web
    ".js", ".jsx", ".ts", ".tsx", 

    # Flutter / Dart
    ".dart",

    # Xamarin / C#
    ".cs", ".xaml",

    # C / C++
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx",

    # Rust
    ".rs",  

    # Python
    ".py",

    # Go
    ".go",  

    # Ruby
    ".rb",

    # PHP
    ".php", 

    # Perl
    ".pl",

    # Julia
    ".jl"
]

class CoderAgent(BaseAgent):
    """
    Determines project structure, scaffolds directories/files, and generates
    Python code based on the implementation specifications (impl_*.md).
    Handles initial creation.
    """
    def get_idea_content(self):        
        self.logger.info(f"Reading ideas from idea.md")
        file_path = os.path.join(self.docs_path, "idea.md")
        content = self._read_file(file_path)
        if content is not None:
            content = f"# --- Content from: idea.md ---\n\n{content}\n\n# --- End of: idea.md ---"
        else:
            self.logger.warning(f"Could not read content from idea file: idea.md")
            raise Exception("FATAL error - Stopping!")

        if not content:
            raise FileNotFoundError(f"Failed to read content from idea file: idea.md")

        return content

    def get_feature_content(self):
        self.logger.info(f"Reading features from files in: {self.docs_path}")

        all_files = []
        try:
            all_files = os.listdir(self.docs_path)
            feature_files = [
                f for f in all_files
                if f.startswith("feature_") and f.endswith(".md")
            ]

        except FileNotFoundError:
                self.logger.error(f"Documentation directory not found: {self.docs_path}")
                raise FileNotFoundError(f"Documentation directory not found: {self.docs_path}")
        except Exception as e:
                self.logger.error(f"Error listing files in {self.docs_path}: {e}", exc_info=True)
                raise RuntimeError(f"Could not list files in documentation directory: {e}")

        if not feature_files:
            self.logger.error(f"No feature files (feature*.md) found in {self.docs_path}.")
            raise FileNotFoundError(f"No feature files found for project {self.project_name} in {self.docs_path}. Ensure the Architect Agent ran successfully.")

        combined_content = []
        combined_files = feature_files
        self.logger.info(f"Reading features content from: {', '.join(combined_files)}")
        for filename in combined_files:
            file_path = os.path.join(self.docs_path, filename)
            content = self._read_file(file_path)
            if content is not None:
                combined_content.append(f"# --- Content from: {filename} ---\n\n{content}\n\n# --- End of: {filename} ---")
            else:
                self.logger.warning(f"Could not read content from file: {file_path}")
                raise Exception("FATAL error - Stopping!")

        if not combined_content:
                raise FileNotFoundError(f"Failed to read content from files: {', '.join(combined_files)}")

        content = "\n\n".join(combined_content)
        self.logger.info(f"Successfully combined content from {len(combined_files)} file(s). Total length: {len(content)} chars.")
        return content, combined_content

    def get_all_content(self):
        self.logger.info(f"Searching for features, implementation and integration files in: {self.docs_path}")
        
        all_files = ["idea.md"]

        try:
            all_files = os.listdir(self.docs_path)
            feature_files = [
                f for f in all_files
                if f.startswith("feature_") and f.endswith(".md")
            ]

            impl_files = [
                f for f in all_files
                if f.startswith("impl_") and f.endswith(".md")
            ]

            integ_files = [
                f for f in all_files
                if f.startswith("integ_") and f.endswith(".md")
            ]

        except FileNotFoundError:
                self.logger.error(f"Documentation directory not found: {self.docs_path}")
                raise FileNotFoundError(f"Documentation directory not found: {self.docs_path}")
        except Exception as e:
                self.logger.error(f"Error listing files in {self.docs_path}: {e}", exc_info=True)
                raise RuntimeError(f"Could not list files in documentation directory: {e}")

        if not feature_files:
            self.logger.error(f"No feature files (feature*.md) found in {self.docs_path}.")
            raise FileNotFoundError(f"No feature files found for project {self.project_name} in {self.docs_path}. Ensure the Architect Agent ran successfully.")

        if not impl_files:
            self.logger.error(f"No implementation plan files (impl*.md) found in {self.docs_path}.")
            raise FileNotFoundError(f"No implementation plan files found for project {self.project_name} in {self.docs_path}. Ensure the Architect Agent ran successfully.")

        if not integ_files:
            self.logger.error(f"No integration plan files (integ*.md, integ.md) found in {self.docs_path}.")
            raise FileNotFoundError(f"No integrationfiles found for project {self.project_name} in {self.docs_path}. Ensure the Architect Agent ran successfully.")

        combined_content = []
        combined_files = feature_files+impl_files+integ_files
        self.logger.info(f"Reading implementation plans from: {', '.join(combined_files)}")
        for filename in combined_files:
            file_path = os.path.join(self.docs_path, filename)
            content = self._read_file(file_path)
            if content is not None:
                combined_content.append(f"# --- Content from: {filename} ---\n\n{content}\n\n# --- End of: {filename} ---")
            else:
                self.logger.warning(f"Could not read content from file: {file_path}")
                raise Exception("FATAL error - Stopping!")

        if not combined_content:
                raise FileNotFoundError(f"Failed to read content from files: {', '.join(combined_files)}")

        content = "\n\n".join(combined_content)
        self.logger.info(f"Successfully combined content from {len(combined_files)} file(s). Total length: {len(content)} chars.")
        return content, combined_content

    def run(self):
        """
        Executes the Coder agent's task: structuring the project and generating/updating source files.

        Args:
            feedback: Optional feedback from Reviewer/Tester agents (used in build loop).
            impl_content: Optional pre-read content of impl_*.md. If None, reads from file.
        """
        self.logger.info(f"Running Coder Agent for project: {self.project_name} )")

        # 1. Read Implementation Plan (Common to both modes)
        all_content, _ = self.get_all_content()

        written_files = [] # Keep track of files actually written

    
        # --- CREATE MODE ---
    
        # # 2. Generate and Create Project Structure (Only in Create Mode)
        # self.logger.info("Phase 1: Determining and creating project structure...")
        # try:
        #     # Ask Gemini for the structure based on the implementation plan
        #     structure_text = self._generate_structure_list(all_content)
        #     # Parse the text and create directories/empty files
        #     scaffolded_files = self._create_project_scaffolding(structure_text)
        #     self.logger.info(f"Successfully scaffolded {len(scaffolded_files)} potential files/dirs.")
        # except (ValueError, ConnectionError, RuntimeError, OSError) as e:
        #     self.logger.error(f"Failed to establish project structure: {e}", exc_info=True)
        #     raise RuntimeError(f"Coder Agent failed during structure generation: {e}")
        # except Exception as e:
        #         self.logger.error(f"An unexpected error occurred during structure generation: {e}", exc_info=True)
        #         raise RuntimeError(f"An unexpected error occurred in Coder Agent structure phase: {e}")


        # 3. Generate Code Content
        self.logger.info("Phase 1: Generating code content ...")
        generated_content = self._generate(
            all_content=all_content
        )
        log_action = "generated"


        # 4. Write Generated Code Content (Common to both modes)
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
        self.logger.debug(f"Generated structure prompt for LLM:\n{prompt[:500]}...")

        try:
            self.logger.info("Sending request to LLM API for project structure...")
            structure_text = self.model.generate_content(prompt)
            self.logger.info("Received structure response from LLM API.")
            self.logger.debug(f"Structure Text (raw):\n{structure_text[:300]}...")
            if not structure_text or not structure_text.strip():
                raise ValueError("Gemini returned an empty response for the project structure.")
            return structure_text
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM API call (Structure): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate structure using AI: {e}")

    def _create_structure_prompt(self, impl_content: str) -> str:
        """Creates the prompt to ask the LLM for the project directory structure."""
        return f"""
Based on the following feature descriptions (feature_*.md), implementation plan (impl_*.md) and integration plan (integ_*.md), generate the complete directory structure and file list for the project.

**Feature descriptions (feature_*.md), Integration plans (`integ_*.md`) and Implementation Plans (`impl_*.md`):**
```markdown

{impl_content}

```

**Instructions for Output Format:**

1.  **List all necessary directories and files.**
2.  **Use indentation (4 spaces)** to represent the hierarchy (subdirectories and files within directories).
3.  **Clearly mark directories** by appending a forward slash (`{DIR_MARKER}`) to their names.
4.  **Include all source files** (e.g., {','.join(source_code_extensions)}), configuration files (e.g., `requirements.txt`, `.gitignore`, `Dockerfile`), documentation files (`README.md`), etc., mentioned or implied by the plan.
5.  **Do NOT include generated code content here.** Only provide the file and directory names in a tree structure.
6.  Start the structure from the project's root directory. Assume the project name itself is the root.

**Example Output Format fro python files, could be the same fot :**

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


    def read_all_code_files(self) -> str:
        """Recursively reads all files (not just .py) from project directory."""
        base_path = Path(self.project_pat)

        all_source_code = ""

        for item in base_path.rglob('*'): # Recursively find all items
            if item.is_file():
                try:
                    if Path(item).suffix not in programing_extensions:
                         continue
                    
                    # Calculate path relative to the starting path
                    relative_path = str(item.relative_to(base_path))
                    # Use os specific separators for dictionary keys? Match LLM format?
                    # Let's use POSIX-style separators for keys, as often used in web/LLMs
                    relative_path_posix = relative_path.replace(os.sep, '/')

                    content = self._read_file(str(item)) # Read file using existing helper
                    all_source_code += f"<<<FILENAME: {relative_path_posix}\n\n"
                    all_source_code += content + "\n\n"
                    all_source_code += ">>>"

                 
                except Exception as e:
                    # Log error but continue reading other files
                    self.logger.error(f"Error reading file {item} for update context: {e}", exc_info=False) # Keep log brief

        return all_source_code


    def _generate(self, all_content: str) -> dict[str, str]:
        """Uses Generative AI to create the code content for ALL files."""
        if not self.model:
            raise RuntimeError("Generative model not initialized.")


        prompt = self._create_code_generation_prompt(all_content) # Renamed from _create_prompt
        self.logger.debug(f"Generated create prompt for LLM (Coder):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to LLM API for code content generation ...")
            # Consider increasing max output tokens if needed
            # generation_config = genai.types.GenerationConfig(max_output_tokens=16384) # Example
            # response = self.model.generate_content(prompt, generation_config=generation_config)
            generated_text = self.model.generate_content(prompt)
            self.logger.info("Received code generation response from LLM API.")
            self.logger.debug(f"Generated Text (first 200 chars):\n{generated_text[:200]}...")

            # --- Parsing the generated text into files ---
            # Use the existing robust parser
            code_files = self._parse_code_blocks(generated_text)
            if not code_files:
                 # This is more critical now, as it means no code was generated 
                 self.logger.warning("AI response parsed, but no valid code blocks (```python filename=...```) found.")
                 # Returning empty dict, the caller handles the warning/error.

            return code_files
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM API call (Code Gen): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate code using AI: {e}")

    def _create_code_generation_prompt(self, impl_content: str) -> str:
        """Creates the prompt for the generative AI model to generate code for ALL files from scratch or based on feedback."""
    
        prompt = f"""
Generate the complete, runnable code content for ALL necessary files for the project described in the provided project details. 
The project might involve various programming languages (like Python, JavaScript, TypeScript, Java, Kotlin, etc.) and platforms (like backend, web frontend, Android, etc.).
Adhere strictly to the plan's specifications regarding languages, frameworks, modules, classes, methods, file structure, and overall architecture.

** Project Details (incorporating idea, features, integration, and implementation plans):**
```markdown
{impl_content}
```
**Instructions:**

1.  **Generate the full content for ALL required files.** This includes source code files (e.g., `.py`, `.js`, `.ts`, `.java`, `.kt`, `.html`, `.css`), configuration files (e.g., `requirements.txt`, `package.json`, `build.gradle`, `AndroidManifest.xml`, `tsconfig.json`, `Dockerfile`, `.gitignore`), documentation (`README.md`), tests, and any other files specified or implied by the project details.
2.  **Adhere to the language, version, and style conventions specified or implied in the plan.**
    *   For **Python**: Use Python 3.11+ syntax with type hints if specified.
    *   For **JavaScript/TypeScript**: Use modern standards (e.g., ES6+/latest TypeScript) and specified frameworks (React, Vue, Angular, Node.js, etc.).
    *   For **Java/Kotlin (Android/Backend)**: Use the specified Java/Kotlin versions and adhere to platform conventions (Android SDK, Spring Boot, etc.).
    *   For **Web**: Use HTML5, CSS3, and follow specified preprocessor/framework guidelines.
    *   If language specifics are unclear in the plan, use common modern standards and best practices for that language/platform.
3.  **Implement all core logic, classes, functions, UI layouts, components, etc.** defined in the plan. Include basic error handling where appropriate (e.g., file I/O, network requests, user input validation, null checks).
4.  **Include necessary import/require/include statements** at the beginning of each source file, appropriate for the language and module system used (e.g., Python imports, ES modules, CommonJS, Java imports, Kotlin imports).
5.  **Include basic documentation comments** for primary functions, classes, and methods in the respective languages (e.g., Python docstrings, JSDoc, JavaDoc, KDoc). For configuration or markup files, add comments where clarification is needed.
6.  **Structure the output using Markdown code blocks.** Each block MUST be prefixed with the intended relative filename from the project root, like this:

    *Example Structure:*
    ```
    <<<FILENAME: src/main.py
    # Python example
    import os

    def main() -> None:
        \"\"\"Main entry point.\"\"\"
        print("Hello from Python!")

    if __name__ == "__main__":
        main()
    >>>

    <<<FILENAME: static/js/app.js
    // JavaScript example
    document.addEventListener('DOMContentLoaded', () => {{
      console.log('Hello from JavaScript!');
    }});
    >>>

    <<<FILENAME: app/src/main/java/com/example/myapp/MainActivity.java
    // Java/Android example
    package com.example.myapp;

    import androidx.appcompat.app.AppCompatActivity;
    import android.os.Bundle;
    import android.util.Log;

    public class MainActivity extends AppCompatActivity {{
        private static final String TAG = "MainActivity";

        @Override
        protected void onCreate(Bundle savedInstanceState) {{
            super.onCreate(savedInstanceState);
            setContentView(R.layout.activity_main);
            Log.d(TAG, "Hello from Android!");
        }}
    }}
    >>>

    <<<FILENAME: templates/index.html
    <!-- HTML example -->
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Web App</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <h1>Hello from HTML!</h1>
        <script src="/static/js/app.js"></script>
    </body>
    </html>
    >>>

    <<<FILENAME: requirements.txt
    # Python dependencies
    flask>=2.0
    requests
    >>>

    <<<FILENAME: package.json
    {{
      "name": "my-web-app",
      "version": "1.0.0",
      "description": "",
      "main": "server.js",
      "scripts": {{
        "start": "node server.js"
      }},
      "dependencies": {{
        "express": "^4.17.1"
      }}
    }}
    >>>

    <<<FILENAME: README.md
    # My Project
    This project implements [features] using [technology stack].
    Follow setup instructions...
    >>>

    <<<FILENAME: .gitignore
    # General ignores
    __pycache__/
    *.pyc
    node_modules/
    build/
    .env
    *.log
    >>>
    ```
7.  **Ensure the `<<<FILENAME:` paths are relative to the project root** and accurately reflect the structure outlined or implied in the project plan (e.g., `src/main.py`, `app/src/main/res/layout/activity_main.xml`, `public/index.html`, `README.md`).
8.  **Do NOT add any explanatory text, introductions, or summaries outside the formatted code blocks.** Focus solely on generating the file contents within their respective `<<<FILENAME: ...>>> ... >>>` blocks.
9.  If the plan is unclear on a specific implementation detail, make a reasonable assumption aligned with the overall architecture and add a `# TODO:` or `<!-- TODO: -->` comment (or equivalent for the language) explaining the assumption or the need for clarification.
10. **Generate ALL specified and implied files in a single, complete response.** Ensure the generated code is runnable or buildable given the correct environment and dependencies.
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
        # pattern = re.compile(
        #     r"```(?P<lang>\w+)?\s+filename=(?P<filename>[^\s`]+)\s*\n" # Start fence, lang (optional), filename
        #     r"(?P<code>.*?)\n"                                         # Code content (non-greedy)
        #     r"```",                                                    # End fence
        #     re.DOTALL | re.IGNORECASE
        # )

        pattern = re.compile(
            r"<<<FILENAME:\s+(?P<filename>[^\s`]+)\s*\n" # Start fence, filename
            r"(?P<code>.*?)\n"                                         # Code content (non-greedy)
            r">>>",                                                    # End fence
            re.DOTALL | re.IGNORECASE
        )

        files_pattern = re.compile(r"<<<FILENAME:\s*(.*?)>>>\s*(.*?)(?=\s*<<<FILENAME|\Z)", re.DOTALL | re.IGNORECASE)


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
             self.logger.warning("No code/content blocks matching the expected format (<<<FILENAME: ...>>>) were found in the AI response.")

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
