import argparse
import logging
import os
import sys
import shutil
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai
from colorama import Fore, Style, init as colorama_init

# Initialize colorama
colorama_init(autoreset=True)

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils import slugify, load_config
# Import agents
from agents import (
    InnovatorAgent, ArchitectAgent, CoderAgent, ReviewerAgent, TesterAgent,
    DocumenterAgent, MarketAnalystAgent, ResearchAgent
)

# --- Constants ---
PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'projects'))
VENV_DIR_NAME = ".venv"

# --- Color Constants ---
STEP_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
ERROR_COLOR = Fore.RED
WARN_COLOR = Fore.YELLOW
INFO_COLOR = Fore.BLUE
AGENT_COLOR = Fore.MAGENTA
RESET_ALL = Style.RESET_ALL

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Orchestrator")

# --- Helper Functions ---

def get_project_path(project_name: str) -> str:
    return os.path.join(PROJECTS_DIR, project_name)

def ensure_project_structure(project_path: str):
    logger.info(f"Ensuring project structure exists at: {project_path}")
    try:
        os.makedirs(os.path.join(project_path, "docs"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "src"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "tests"), exist_ok=True)
        logger.debug(f"Standard directories ensured for {os.path.basename(project_path)}")
    except OSError as e:
        logger.error(f"Failed to create project structure at {project_path}: {e}")
        raise

def list_projects():
    logger.info(f"Listing projects in: {PROJECTS_DIR}")
    if not os.path.exists(PROJECTS_DIR):
        logger.warning(f"Projects directory '{PROJECTS_DIR}' does not exist.")
        print(f"{WARN_COLOR}No projects found (directory '{PROJECTS_DIR}' missing).")
        return
    try:
        projects = [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]
        if not projects: print(f"{INFO_COLOR}No projects found.")
        else:
            print(f"{INFO_COLOR}Available projects:")
            for project in sorted(projects): print(f"- {project}")
    except OSError as e: logger.error(f"Error listing projects in {PROJECTS_DIR}: {e}"); print(f"{ERROR_COLOR}Error accessing projects directory: {e}")

def _extract_dependencies(impl_content: str) -> list[str]:
    logger.info("Extracting dependencies from implementation plan using AI...")
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)
        config = load_config()
        model_name = config.get('llm', {}).get('model_name', 'gemini-pro')
        model = genai.GenerativeModel(model_name)
        logger.debug(f"Using model {model_name} for dependency extraction.")
    except Exception as e: logger.error(f"Failed to configure LLM for dependency extraction: {e}"); raise ConnectionError(f"LLM configuration failed: {e}")

    prompt = f"""
Analyze the following implementation plan (Markdown) and identify all necessary external Python packages that need to be installed using pip. Focus on libraries mentioned in the 'Technology Stack' or implied by components. List only base package names (e.g., `requests`, `pytest`, `Flask`). Do NOT include built-in modules (e.g., `os`, `sys`, `json`) or internal project modules. Format as a plain list, one package per line. If none, output "None".

**Implementation Plan:**
```markdown
{impl_content}
```

**Output:**
"""
    try:
        response = model.generate_content(prompt)
        dependencies_text = response.text.strip()
        logger.debug(f"LLM response for dependencies:\n{dependencies_text}")
        if not dependencies_text or dependencies_text.lower() == "none": return []
        dependencies = [line.strip() for line in dependencies_text.splitlines() if line.strip()]
        dependencies = [dep for dep in dependencies if dep and not dep.startswith(('```', '#', '*')) and '.' not in dep and ' ' not in dep]
        if 'pytest' not in dependencies and 'Testing Strategy' in impl_content and 'pytest' in impl_content: dependencies.append('pytest')
        dependencies = sorted(list(set(dependencies)))
        logger.info(f"Extracted dependencies: {dependencies}")
        return dependencies
    except Exception as e: logger.error(f"LLM call failed during dependency extraction: {e}"); logger.warning("Could not reliably extract dependencies using AI."); return []

def _generate_dependency_commands(project_path: str, impl_content: str) -> tuple[list[dict], str | None]:
    dependencies = _extract_dependencies(impl_content)
    requirements_path = os.path.join(project_path, "requirements.txt")
    if not dependencies:
        logger.info("No external dependencies identified. Skipping requirements.txt and venv setup.")
        if os.path.exists(requirements_path):
             try: os.remove(requirements_path)
             except OSError as e: logger.warning(f"Could not remove existing empty requirements.txt: {e}")
        return [], None
    logger.info(f"Writing dependencies to {requirements_path}")
    try:
        with open(requirements_path, 'w') as f:
            for dep in dependencies: f.write(f"{dep}\n")
    except IOError as e: logger.error(f"Failed to write requirements.txt: {e}"); raise
    python_executable = sys.executable or "python3"
    venv_path = os.path.join(project_path, VENV_DIR_NAME)
    venv_python_placeholder = os.path.join(VENV_DIR_NAME, "bin", "python")
    if sys.platform == 'win32': venv_python_placeholder = os.path.join(VENV_DIR_NAME, "Scripts", "python.exe")
    create_venv_cmd = f"{python_executable} -m venv {VENV_DIR_NAME}"
    upgrade_pip_cmd = f"{venv_python_placeholder} -m pip install --upgrade pip"
    install_cmd = f"{venv_python_placeholder} -m pip install -r requirements.txt"
    commands_to_run = [
        {"command": create_venv_cmd, "cwd": project_path, "message": f"{INFO_COLOR}Creating virtual environment ({VENV_DIR_NAME}) in {project_path}..."},
        {"command": upgrade_pip_cmd, "cwd": project_path, "message": f"{INFO_COLOR}Upgrading pip in virtual environment..."},
        {"command": install_cmd, "cwd": project_path, "message": f"{INFO_COLOR}Installing dependencies from {requirements_path} into {venv_path}..."}
    ]
    return commands_to_run, requirements_path

def _get_venv_python_path(project_path: str) -> str | None:
    venv_path = os.path.join(project_path, VENV_DIR_NAME)
    expected_path = ""
    if sys.platform == 'win32': expected_path = os.path.join(venv_path, 'Scripts', 'python.exe')
    else: expected_path = os.path.join(venv_path, 'bin', 'python')
    if os.path.exists(expected_path): return expected_path
    logger.warning(f"Standard venv python path not found ({expected_path}). Checking alternatives.")
    alt_paths = [ os.path.join(venv_path, 'bin', 'python3'), os.path.join(venv_path, 'Scripts', 'python.exe'), os.path.join(venv_path, 'bin', 'python') ]
    for path in alt_paths:
        if os.path.exists(path): logger.warning(f"Found venv python at non-standard location: {path}"); return path
    logger.error(f"Could not find python executable within the venv directory: {venv_path}")
    return None

# --- Command Handlers ---

def handle_list_command(): list_projects()
def handle_idea_command(idea_text: str, project_name: str | None):
    logger.info(f"Handling '--idea' action: Text='{idea_text[:50]}...', Project='{project_name}'")
    if not project_name:
        project_name = slugify(idea_text)
        if not project_name: logger.error("Could not generate valid project name."); print(f"{ERROR_COLOR}Error: Could not generate valid project name."); return
        logger.info(f"Generated project name: {project_name}")
    project_path = get_project_path(project_name)
    try: ensure_project_structure(project_path)
    except Exception: print(f"{ERROR_COLOR}Error: Failed to set up project structure for '{project_name}'."); return
    print(f"{AGENT_COLOR}Initializing Innovator Agent...{RESET_ALL}")
    innovator = InnovatorAgent(project_name=project_name, project_path=project_path)
    try:
        idea_md_path = innovator.run(idea_text=idea_text, update_mode=False)
        print(f"{SUCCESS_COLOR}Successfully processed idea for project '{project_name}'. Concept saved to: {idea_md_path}")
    except Exception as e: logger.error(f"Innovator Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error processing idea: {e}")

def handle_update_idea_command(modification_text: str, project_name: str):
    logger.info(f"Handling '--update-idea' action for project: {project_name}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot update idea: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    print(f"{AGENT_COLOR}Initializing Innovator Agent for update...{RESET_ALL}")
    innovator = InnovatorAgent(project_name=project_name, project_path=project_path)
    try:
        updated_idea_md_path = innovator.run(modification_text=modification_text, update_mode=True)
        print(f"{SUCCESS_COLOR}Successfully updated idea for project '{project_name}'. Concept saved to: {updated_idea_md_path}")
    except Exception as e: logger.error(f"Innovator Agent update failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error updating idea: {e}")

def handle_analyze_idea_command(project_name: str):
    logger.info(f"Handling '--analyze-idea' action for project: {project_name}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot analyze idea: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    print(f"{AGENT_COLOR}Initializing Market Analyst Agent...{RESET_ALL}")
    analyst = MarketAnalystAgent(project_name=project_name, project_path=project_path)
    try:
        analysis_md_path = analyst.run(update_mode=False)
        print(f"{SUCCESS_COLOR}Successfully analyzed idea for project '{project_name}'. Analysis saved to: {analysis_md_path}")
    except Exception as e: logger.error(f"Market Analyst Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error analyzing idea: {e}")

def handle_generate_doc_command(doc_type: str, project_name: str):
    logger.info(f"Handling '--generate-doc' action for project: {project_name}, type: {doc_type}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    if not os.path.exists(os.path.join(project_path, "docs", "idea.md")): logger.warning(f"Cannot find 'docs/idea.md'. Context limited.")
    if not os.path.exists(os.path.join(project_path, "docs", "impl.md")): logger.warning(f"Cannot find 'docs/impl.md'. Context limited.")
    if not os.path.isdir(os.path.join(project_path, "src")): logger.warning(f"Source directory 'src/' does not exist. Context limited.")
    print(f"{AGENT_COLOR}Initializing Documenter Agent...{RESET_ALL}")
    documenter = DocumenterAgent(project_name=project_name, project_path=project_path)
    try:
        generated_doc_path = documenter.run(doc_type=doc_type)
        print(f"{SUCCESS_COLOR}Successfully generated '{doc_type}' documentation for project '{project_name}'. Saved to: {generated_doc_path}")
    except Exception as e: logger.error(f"Documenter Agent failed for type '{doc_type}': {e}", exc_info=True); print(f"{ERROR_COLOR}Error generating documentation: {e}")

def handle_research_command(project_name: str):
    logger.info(f"Handling '--research' action for project: {project_name}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot research: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    print(f"{AGENT_COLOR}Initializing Research Agent...{RESET_ALL}")
    researcher = ResearchAgent(project_name=project_name, project_path=project_path)
    try:
        research_summary_path = researcher.run()
        print(f"{SUCCESS_COLOR}Successfully performed research for project '{project_name}'. Summary saved to: {research_summary_path}")
    except Exception as e: logger.error(f"Research Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error performing research: {e}")

async def handle_update_command(modification_text: str, project_name: str, execute_command_func):
    logger.info(f"Handling '--update' action for project: {project_name}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    impl_md_path = os.path.join(project_path, "docs", "impl.md")
    idea_content, impl_content = None, None
    base_reader = DocumenterAgent(project_name,"")
    if os.path.exists(idea_md_path): idea_content = base_reader._read_file(idea_md_path)
    if os.path.exists(impl_md_path): impl_content = base_reader._read_file(impl_md_path)
    if not idea_content: logger.warning("idea.md not found or empty. Update context limited.")
    if not impl_content: logger.error("impl.md not found or empty. Cannot proceed."); print(f"{ERROR_COLOR}Error: impl.md is required for update."); return

    # --- Step 1: Update Implementation Plan ---
    print(f"{STEP_COLOR}Step 1/4: Updating implementation plan...{RESET_ALL}")
    architect = ArchitectAgent(project_name=project_name, project_path=project_path)
    try:
        updated_impl_md_path = architect.run(modification_text=modification_text, update_mode=True)
        impl_content = architect._read_file(updated_impl_md_path) # Read updated content
        if not impl_content: raise IOError("Failed to read updated impl.md content.")
        print(f"{SUCCESS_COLOR}Implementation plan updated.{RESET_ALL}")
    except Exception as e: logger.error(f"Architect Agent update failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Update failed at Architect stage: {e}"); return

    # --- Step 2: Update Code ---
    print(f"{STEP_COLOR}Step 2/4: Updating code...{RESET_ALL}")
    coder = CoderAgent(project_name=project_name, project_path=project_path)
    updated_code_files = []
    try:
        updated_code_files = coder.run(modification_text=modification_text, update_mode=True, impl_content=impl_content)
        print(f"{SUCCESS_COLOR}Code update affected {len(updated_code_files)} file(s).{RESET_ALL}")
    except Exception as e: logger.error(f"Coder Agent update failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Update failed at Coder stage: {e}"); return

    # --- Step 3: Update Tests ---
    print(f"{STEP_COLOR}Step 3/4: Updating tests...{RESET_ALL}")
    tester = TesterAgent(project_name=project_name, project_path=project_path)
    updated_test_files = []
    try:
        updated_test_files = tester.run(modification_text=modification_text, update_mode=True, impl_content=impl_content)
        print(f"{SUCCESS_COLOR}Test update affected {len(updated_test_files)} file(s).{RESET_ALL}")
    except Exception as e: logger.error(f"Tester Agent update failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Update failed at Tester stage: {e}"); return

    # --- Step 4: Regenerate Project Overview Document ---
    print(f"{STEP_COLOR}Step 4/4: Regenerating project overview documentation...{RESET_ALL}")
    documenter = DocumenterAgent(project_name=project_name, project_path=project_path)
    try:
        docs_path = documenter.run(doc_type='project_overview')
        print(f"{SUCCESS_COLOR}Project overview documentation regenerated: {docs_path}{RESET_ALL}")
    except Exception as e: logger.error(f"Documenter Agent regeneration failed: {e}", exc_info=True); print(f"{WARN_COLOR}Warning: Update completed, but failed to regenerate documentation: {e}{RESET_ALL}")
    logger.info(f"Update process completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Update finished successfully for project '{project_name}'.{RESET_ALL}")


async def handle_build_command(project_name: str, execute_command_func):
    logger.info(f"Handling '--build' action for project: {project_name}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot build: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    logger.info(f"Starting build pipeline for project '{project_name}'...")
    pipeline_steps = 6

    # === Step 1: Architect Agent ===
    print(f"{STEP_COLOR}Step 1/{pipeline_steps}: Generating architecture plan...{RESET_ALL}")
    architect = ArchitectAgent(project_name=project_name, project_path=project_path)
    impl_md_path, impl_content = None, None
    try:
        impl_md_path = architect.run()
        impl_content = architect._read_file(impl_md_path)
        if not impl_content: raise IOError("Failed to read generated impl.md content.")
        print(f"{SUCCESS_COLOR}Architecture plan generated: {impl_md_path}{RESET_ALL}")
    except Exception as e: logger.error(f"Architect Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Build failed at Architect stage: {e}"); return
    if not impl_md_path or not os.path.exists(impl_md_path): logger.error(f"impl.md not found after Architect run."); print(f"{ERROR_COLOR}Build failed: Implementation plan not created."); return

    # === Step 2: Setup Dependencies & Virtual Environment ===
    logger.info("Setting up dependencies and virtual environment...")
    dependency_commands, requirements_path = [], None
    venv_python_path = None
    try:
        dependency_commands, requirements_path = _generate_dependency_commands(project_path, impl_content)
        if dependency_commands:
            print(f"{STEP_COLOR}Step 2/{pipeline_steps}: Setting up virtual environment ({VENV_DIR_NAME}) and dependencies...{RESET_ALL}")
            for cmd_info in dependency_commands:
                 print(f"{INFO_COLOR}Executing: {cmd_info['command']}{RESET_ALL}")
                 result = await execute_command_func(command=cmd_info['command'], cwd=cmd_info['cwd'])
                 stderr_output = result.get("stderr", "")
                 # Check for actual errors in stderr, ignoring common warnings
                 is_error = stderr_output and "warning" not in stderr_output.lower()
                 if is_error:
                     logger.error(f"Command failed: {cmd_info['command']}\nSTDERR:\n{stderr_output}")
                     print(f"{ERROR_COLOR}Build failed during dependency setup: {stderr_output}")
                     return
                 elif stderr_output: logger.warning(f"Command '{cmd_info['command']}' produced warnings:\n{stderr_output}")
                 logger.info(f"Command successful: {cmd_info['command']}")

            # Verify venv python path after commands
            venv_python_path = _get_venv_python_path(project_path)
            if not venv_python_path:
                await asyncio.sleep(1)
                venv_python_path = _get_venv_python_path(project_path)
                if not venv_python_path:
                    logger.error(f"Could not find python in venv at {os.path.join(project_path, VENV_DIR_NAME)}.")
                    print(f"{ERROR_COLOR}Build failed: Could not find venv python executable after setup attempt.")
                    return
            logger.info(f"Found venv python at: {venv_python_path}")
            print(f"{SUCCESS_COLOR}Virtual environment and dependencies installed.{RESET_ALL}")
        else: print(f"{STEP_COLOR}Step 2/{pipeline_steps}: No external dependencies identified. Skipping venv setup.{RESET_ALL}")
    except Exception as e: logger.error(f"Failed to setup dependencies: {e}", exc_info=True); print(f"{ERROR_COLOR}Build failed during dependency setup: {e}"); return

    # === Step 3: Coder Agent ===
    print(f"{STEP_COLOR}Step 3/{pipeline_steps}: Generating code...{RESET_ALL}")
    coder = CoderAgent(project_name=project_name, project_path=project_path)
    generated_files = []
    try:
        generated_files = coder.run(feedback=None, impl_content=impl_content)
        print(f"{SUCCESS_COLOR}Code generated for {len(generated_files)} file(s).{RESET_ALL}")
    except Exception as e: logger.error(f"Coder Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Build failed at Coder stage: {e}"); return

    # === Step 4: Coder-Reviewer Loop ===
    print(f"{STEP_COLOR}Step 4/{pipeline_steps}: Reviewing code (using AI)...{RESET_ALL}") # Updated message
    reviewer = ReviewerAgent(project_name=project_name, project_path=project_path)
    max_review_attempts, review_passed, feedback = 3, False, None
    for attempt in range(max_review_attempts):
        print(f"{INFO_COLOR}Review Attempt {attempt + 1}/{max_review_attempts}...{RESET_ALL}")
        try:
            # Pass impl_content to the AI reviewer
            review_passed, feedback = reviewer.run(generated_files=generated_files, impl_content=impl_content)
            if review_passed: print(f"{SUCCESS_COLOR}AI Code review passed.{RESET_ALL}"); break
            else:
                print(f"{WARN_COLOR}AI Code review found issues. Attempting to fix...{RESET_ALL}"); print(f"---\n{feedback}\n---")
                generated_files = coder.run(feedback=feedback, impl_content=impl_content) # Pass feedback to coder
                if not generated_files and attempt < max_review_attempts -1: logger.error("Coder produced no files after feedback."); print(f"{ERROR_COLOR}Error: Coder failed after feedback."); return
        except Exception as e: logger.error(f"Review/Coder loop failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Build failed during Review/Code cycle: {e}"); return
    if not review_passed: logger.error(f"Review failed after {max_review_attempts} attempts."); print(f"{ERROR_COLOR}Build failed: Review did not pass."); return

    # === Step 5: Tester Agent ===
    print(f"{STEP_COLOR}Step 5/{pipeline_steps}: Generating and running tests...{RESET_ALL}")
    tester = TesterAgent(project_name=project_name, project_path=project_path)
    test_files_generated = []
    try:
        test_files_generated = tester.run(impl_content=impl_content)
        print(f"{INFO_COLOR}Tests generated for {len(test_files_generated)} file(s).{RESET_ALL}")
        if test_files_generated:
             print(f"{INFO_COLOR}Running tests...{RESET_ALL}")
             if not venv_python_path:
                  venv_python_path = _get_venv_python_path(project_path)
                  if not venv_python_path: logger.error(f"Venv python not found before tests."); print(f"{ERROR_COLOR}Build failed: Cannot find venv python."); return
             pytest_cmd = f"{venv_python_path} -m pytest -v"
             logger.info(f"Executing test command: {pytest_cmd} in {project_path}")
             result = await execute_command_func(command=pytest_cmd, cwd=project_path)
             stdout_lower, stderr_lower = result.get("stdout", "").lower(), result.get("stderr", "").lower()
             process_returncode = result.get("returncode", 0)
             is_failure = False
             if result.get("stderr"): is_failure = True
             elif ("failed" in stdout_lower or "error" in stdout_lower) and " 0 errors" not in stdout_lower and " 0 error" not in stdout_lower: is_failure = True
             no_tests_ran = "no tests ran" in stdout_lower or ("collected 0 items" in stdout_lower and process_returncode == 5)

             if is_failure and not no_tests_ran:
                 logger.error(f"Pytest failed:\nSTDOUT:\n{result.get('stdout', '')}\nSTDERR:\n{result.get('stderr', '')}")
                 print(f"{ERROR_COLOR}Build failed: Tests did not pass.\nOutput:\n{result.get('stdout', '')}\n{result.get('stderr', '')}"); return
             elif no_tests_ran:
                  logger.warning("Pytest reported no tests were collected or ran.")
                  print(f"{WARN_COLOR}Tests passed (or no tests found).{RESET_ALL}")
             else:
                 logger.info("Pytest execution successful.")
                 print(f"{SUCCESS_COLOR}Tests passed.{RESET_ALL}")
        else: print(f"{WARN_COLOR}Skipping test execution (no tests generated).{RESET_ALL}")
    except Exception as e: logger.error(f"Tester Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Build failed during Test stage: {e}"); return

    # === Step 6: Documenter Agent ===
    print(f"{STEP_COLOR}Step 6/{pipeline_steps}: Generating project overview documentation...{RESET_ALL}")
    documenter = DocumenterAgent(project_name=project_name, project_path=project_path)
    try:
        docs_path = documenter.run(doc_type='project_overview')
        print(f"{SUCCESS_COLOR}Project overview documentation generated: {docs_path}{RESET_ALL}")
    except Exception as e: logger.error(f"Documenter Agent failed: {e}", exc_info=True); print(f"{WARN_COLOR}Warning: Build completed, but failed to generate documentation: {e}{RESET_ALL}")

    logger.info(f"Build pipeline completed successfully for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Build finished successfully for project '{project_name}'.{RESET_ALL}")


def handle_reset_command(project_name: str):
    logger.info(f"Handling '--reset' action for project: {project_name}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.warning(f"Project '{project_name}' not found."); print(f"{WARN_COLOR}Project '{project_name}' not found."); return
    files_to_delete = [ os.path.join(project_path, "docs", f"{dtype}.md") for dtype in DocumenterAgent.SUPPORTED_DOC_TYPES if dtype != 'project_overview' ] + [
        os.path.join(project_path, "docs", "project_docs.md"), os.path.join(project_path, "docs", "impl.md"),
        os.path.join(project_path, "docs", "market_analysis.md"), os.path.join(project_path, "docs", "research_summary.md"),
        os.path.join(project_path, "requirements.txt"),
    ]
    deleted_count = 0
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try: os.remove(file_path); logger.info(f"Deleted: {file_path}"); deleted_count += 1
            except OSError as e: logger.error(f"Error deleting {file_path}: {e}"); print(f"{ERROR_COLOR}Error deleting {os.path.basename(file_path)}: {e}")
    if deleted_count > 0: print(f"{SUCCESS_COLOR}Reset project '{project_name}': Removed generated documentation and requirements.")
    else: print(f"{INFO_COLOR}Project '{project_name}' already reset.")

def handle_scratch_command(project_name: str):
    logger.info(f"Handling '--scratch' action for project: {project_name}")
    project_path = get_project_path(project_name)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.warning(f"Project '{project_name}' not found."); print(f"{WARN_COLOR}Project '{project_name}' not found."); return
    files_to_delete = [ os.path.join(project_path, "docs", f"{dtype}.md") for dtype in DocumenterAgent.SUPPORTED_DOC_TYPES if dtype != 'project_overview' ] + [
        os.path.join(project_path, "docs", "project_docs.md"), os.path.join(project_path, "docs", "impl.md"),
        os.path.join(project_path, "docs", "market_analysis.md"), os.path.join(project_path, "docs", "research_summary.md"),
        os.path.join(project_path, "requirements.txt"),
    ]
    dirs_to_remove = [ os.path.join(project_path, "src"), os.path.join(project_path, "tests"), os.path.join(project_path, VENV_DIR_NAME) ]
    deleted_count, removed_dir_count = 0, 0
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try: os.remove(file_path); logger.info(f"Deleted: {file_path}"); deleted_count += 1
            except OSError as e: logger.error(f"Error deleting {file_path}: {e}"); print(f"{ERROR_COLOR}Error deleting {os.path.basename(file_path)}: {e}")
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            try: shutil.rmtree(dir_path); logger.info(f"Removed directory: {dir_path}"); removed_dir_count += 1
            except Exception as e: logger.error(f"Error removing {dir_path}: {e}"); print(f"{ERROR_COLOR}Error removing {os.path.basename(dir_path)}: {e}")
    if deleted_count > 0 or removed_dir_count > 0: print(f"{SUCCESS_COLOR}Scratched project '{project_name}'.")
    else: print(f"{INFO_COLOR}Project '{project_name}' already scratched.")

# --- Local Command Execution (Fallback for direct script run) ---
async def _execute_local_command(command: str, cwd: str | None = None, **kwargs) -> dict:
    """Executes a shell command locally using asyncio.create_subprocess_shell."""
    logger.info(f"Executing local command: '{command}' in cwd: {cwd or os.getcwd()}")
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()

        if process.returncode != 0:
            logger.error(f"Local command failed with exit code {process.returncode}")
            logger.error(f"STDERR:\n{stderr_str}")
            logger.error(f"STDOUT:\n{stdout_str}")
        else:
             logger.info(f"Local command finished successfully.")
             if stdout_str: logger.debug(f"STDOUT:\n{stdout_str}")
             if stderr_str: logger.warning(f"STDERR:\n{stderr_str}") # Log stderr even on success as warnings

        return {"stdout": stdout_str, "stderr": stderr_str, "returncode": process.returncode}

    except FileNotFoundError:
        err_msg = f"Error: Command not found for '{command}'. Ensure the executable is in PATH."
        logger.error(err_msg)
        return {"stdout": "", "stderr": err_msg, "returncode": -1}
    except Exception as e:
        err_msg = f"An unexpected error occurred executing local command '{command}': {e}"
        logger.error(err_msg, exc_info=True)
        return {"stdout": "", "stderr": err_msg, "returncode": -1}


# --- Main Execution ---

async def main(execute_command_func):
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"): logger.warning("GEMINI_API_KEY not found.")

    parser = argparse.ArgumentParser(
        description=f"{AGENT_COLOR}MAAI: Multi-Agent Coding CLI Application{RESET_ALL}",
        formatter_class=argparse.RawTextHelpFormatter
    )
    action_group = parser.add_mutually_exclusive_group(required=True)

    # --- Action Flags ---
    action_group.add_argument('--list', action='store_true', help='List projects')
    action_group.add_argument('--idea', type=str, metavar='TEXT', help='Generate new project idea')
    action_group.add_argument('--update-idea', type=str, metavar='TEXT', help='Update existing project idea (requires --project)')
    action_group.add_argument('--research', action='store_true', help='Perform technical research for idea (requires --project)')
    action_group.add_argument('--analyze-idea', action='store_true', help='Perform market analysis for idea (requires --project)')
    action_group.add_argument('--update', type=str, metavar='TEXT', help='Update impl, code, tests, docs based on instructions (requires --project)')
    action_group.add_argument('--generate-doc', type=str, metavar='TYPE', help=f"Generate specific doc (requires --project).\nTypes: {', '.join(sorted(DocumenterAgent.SUPPORTED_DOC_TYPES))}")
    action_group.add_argument('--build', action='store_true', help='Run full build pipeline (requires --project)')
    action_group.add_argument('--reset', action='store_true', help='Reset generated files (docs, reqs) (requires --project)')
    action_group.add_argument('--scratch', action='store_true', help='Reset + clear src/tests/venv (requires --project)')

    # --- Common Arguments ---
    parser.add_argument('--project', type=str, metavar='NAME', help='Project name (required for most actions)')

    args = parser.parse_args()
    logger.info(f"Parsed arguments: {vars(args)}")
    project_name = args.project

    # --- Dispatch ---
    try:
        if args.list: handle_list_command()
        elif args.idea: handle_idea_command(idea_text=args.idea, project_name=project_name)
        elif args.update_idea:
            if not project_name: parser.error("--update-idea requires --project NAME")
            handle_update_idea_command(modification_text=args.update_idea, project_name=project_name)
        elif args.research:
            if not project_name: parser.error("--research requires --project NAME")
            handle_research_command(project_name=project_name)
        elif args.analyze_idea:
            if not project_name: parser.error("--analyze-idea requires --project NAME")
            handle_analyze_idea_command(project_name=project_name)
        elif args.generate_doc:
            if not project_name: parser.error("--generate-doc requires --project NAME")
            if args.generate_doc not in DocumenterAgent.SUPPORTED_DOC_TYPES: parser.error(f"Invalid --doc-type '{args.generate_doc}'. Supported: {', '.join(DocumenterAgent.SUPPORTED_DOC_TYPES)}")
            handle_generate_doc_command(doc_type=args.generate_doc, project_name=project_name)
        elif args.reset:
            if not project_name: parser.error("--reset requires --project NAME")
            handle_reset_command(project_name=project_name)
        elif args.scratch:
            if not project_name: parser.error("--scratch requires --project NAME")
            handle_scratch_command(project_name=project_name)
        # Async handlers
        elif args.update:
            if not project_name: parser.error("--update requires --project NAME")
            await handle_update_command(modification_text=args.update, project_name=project_name, execute_command_func=execute_command_func)
        elif args.build:
            if not project_name: parser.error("--build requires --project NAME")
            await handle_build_command(project_name=project_name, execute_command_func=execute_command_func)
        else:
            logger.error("No valid action flag provided.")
            parser.print_help()
    except Exception as e:
         logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
         print(f"{ERROR_COLOR}An critical error occurred. Check logs for details: {e}")
         sys.exit(1)

if __name__ == "__main__":
    try:
        # When run directly, use the local subprocess executor.
        asyncio.run(main(execute_command_func=_execute_local_command))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)