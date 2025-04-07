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
# Default projects directory, can be overridden by command-line argument
DEFAULT_PROJECTS_DIR = os.path.expanduser('~/projects')
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

def get_project_path(project_name: str, projects_dir: str) -> str:
    """Constructs the full path for a given project name within the specified projects directory."""
    return os.path.join(projects_dir, project_name)

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

def list_projects(projects_dir: str):
    """Lists projects found within the specified projects directory."""
    logger.info(f"Listing projects in: {projects_dir}")
    if not os.path.exists(projects_dir):
        logger.warning(f"Projects directory '{projects_dir}' does not exist.")
        print(f"{WARN_COLOR}No projects found (directory '{projects_dir}' missing).")
        return
    try:
        projects = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
        if not projects: print(f"{INFO_COLOR}No projects found.")
        else:
            print(f"{INFO_COLOR}Available projects:")
            for project in sorted(projects): print(f"- {project}")
    except OSError as e: logger.error(f"Error listing projects in {projects_dir}: {e}"); print(f"{ERROR_COLOR}Error accessing projects directory: {e}")

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

def handle_list_command(projects_dir: str): list_projects(projects_dir)
def handle_idea_command(idea_text: str, project_name: str | None, projects_dir: str):
    logger.info(f"Handling '--idea' action: Text='{idea_text[:50]}...', Project='{project_name}'")
    if not project_name:
        project_name = slugify(idea_text)
        if not project_name: logger.error("Could not generate valid project name."); print(f"{ERROR_COLOR}Error: Could not generate valid project name."); return
        logger.info(f"Generated project name: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    try: ensure_project_structure(project_path)
    except Exception: print(f"{ERROR_COLOR}Error: Failed to set up project structure for '{project_name}'."); return
    print(f"{AGENT_COLOR}Initializing Innovator Agent...{RESET_ALL}")
    innovator = InnovatorAgent(project_name=project_name, project_path=project_path)
    try:
        idea_md_path = innovator.run(idea_text=idea_text, update_mode=False)
        print(f"{SUCCESS_COLOR}Successfully processed idea for project '{project_name}'. Concept saved to: {idea_md_path}")
    except Exception as e: logger.error(f"Innovator Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error processing idea: {e}")

def handle_update_idea_command(modification_text: str, project_name: str, projects_dir: str):
    logger.info(f"Handling '--update-idea' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot update idea: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    print(f"{AGENT_COLOR}Initializing Innovator Agent for update...{RESET_ALL}")
    innovator = InnovatorAgent(project_name=project_name, project_path=project_path)
    try:
        updated_idea_md_path = innovator.run(modification_text=modification_text, update_mode=True)
        print(f"{SUCCESS_COLOR}Successfully updated idea for project '{project_name}'. Concept saved to: {updated_idea_md_path}")
    except Exception as e: logger.error(f"Innovator Agent update failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error updating idea: {e}")

def handle_analyze_idea_command(project_name: str, projects_dir: str):
    logger.info(f"Handling '--analyze-idea' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot analyze idea: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    print(f"{AGENT_COLOR}Initializing Market Analyst Agent...{RESET_ALL}")
    analyst = MarketAnalystAgent(project_name=project_name, project_path=project_path)
    try:
        analysis_md_path = analyst.run(update_mode=False)
        print(f"{SUCCESS_COLOR}Successfully analyzed idea for project '{project_name}'. Analysis saved to: {analysis_md_path}")
    except Exception as e: logger.error(f"Market Analyst Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error analyzing idea: {e}")

def handle_generate_doc_command(doc_type: str, project_name: str, projects_dir: str):
    logger.info(f"Handling '--generate-doc' action for project: {project_name}, type: {doc_type}")
    project_path = get_project_path(project_name, projects_dir)
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

def handle_research_command(project_name: str, projects_dir: str):
    logger.info(f"Handling '--research' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot research: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    print(f"{AGENT_COLOR}Initializing Research Agent...{RESET_ALL}")
    researcher = ResearchAgent(project_name=project_name, project_path=project_path)
    try:
        research_summary_path = researcher.run()
        print(f"{SUCCESS_COLOR}Successfully performed research for project '{project_name}'. Summary saved to: {research_summary_path}")
    except Exception as e: logger.error(f"Research Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error performing research: {e}")

async def handle_update_command(modification_text: str, project_name: str, projects_dir: str, execute_command_func):
    logger.info(f"Handling '--update' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
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


async def handle_build_command(project_name: str, projects_dir: str, execute_command_func):
    """Handles the --build command: Runs the Architect Agent to generate architecture docs."""
    logger.info(f"Handling '--build' action (Architect only) for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path):
        logger.error(f"Project '{project_name}' not found.")
        print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist.")
        return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path):
        logger.error(f"Cannot build architecture: 'docs/idea.md' not found.")
        print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found. Please generate the idea first.")
        return

    print(f"{STEP_COLOR}Running Architect Agent to generate/update architecture plan...{RESET_ALL}")
    architect = ArchitectAgent(project_name=project_name, project_path=project_path)
    try:
        # Assuming architect.run() generates or updates impl.md and potentially other docs
        # Architect agent now returns a list of paths
        impl_paths = architect.run()
        if not impl_paths: # Check if the list is empty
             raise FileNotFoundError("Architect agent did not produce any implementation files.")
        # Optional: Check if all returned paths exist
        # if not all(os.path.exists(p) for p in impl_paths):
        #     raise FileNotFoundError("Architect agent returned paths to files that do not exist.")
        print(f"{SUCCESS_COLOR}Architecture plan generated/updated: {', '.join(impl_paths)}{RESET_ALL}")
        # Optionally read and log content if needed for subsequent steps in a different flow
        # impl_content = architect._read_file(impl_md_path)
        # if not impl_content: raise IOError("Failed to read generated impl.md content.")
    except Exception as e:
        logger.error(f"Architect Agent failed during --build: {e}", exc_info=True)
        print(f"{ERROR_COLOR}Architecture generation failed: {e}")
        return

    logger.info(f"Architecture generation (--build) completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Architecture generation finished successfully for project '{project_name}'.{RESET_ALL}")


# (Removed build pipeline steps: Dependencies, Coder, Reviewer, Tester, Documenter)

async def handle_code_command(project_name: str, fix: bool, projects_dir: str, execute_command_func):
    """Handles the --code command: Runs Coder Agent, optionally with --fix using review.md."""
    logger.info(f"Handling '--code' action for project: {project_name}, Fix mode: {fix}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path):
        logger.error(f"Project '{project_name}' not found.")
        print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist.")
        return

    # Check for existence of *any* implementation plan files
    docs_path = os.path.join(project_path, "docs")
    try:
        plan_files_exist = any(
            (f.startswith("impl_") and f.endswith(".md")) or f == "integ.md" or f == "impl.md"
            for f in os.listdir(docs_path)
            if os.path.isfile(os.path.join(docs_path, f))
        )
    except FileNotFoundError:
        logger.error(f"Documentation directory not found: {docs_path}")
        print(f"{ERROR_COLOR}Error: Documentation directory '{docs_path}' not found.")
        return
    except Exception as e:
        logger.error(f"Error checking for implementation plans in {docs_path}: {e}", exc_info=True)
        print(f"{ERROR_COLOR}Error checking for implementation plans: {e}")
        return

    if not plan_files_exist:
        logger.error(f"Cannot code: No implementation plan files (impl_*.md, integ.md, or impl.md) found in '{docs_path}'.")
        print(f"{ERROR_COLOR}Error: No implementation plan files found in '{docs_path}'. Please run --build first.")
        return

    # CoderAgent now reads the implementation plan(s) internally.
    # No need to read impl_content here anymore.

    feedback_content = None
    if fix:
        review_md_path = os.path.join(project_path, "docs", "review.md")
        if not os.path.exists(review_md_path):
            logger.error(f"Cannot apply fix: 'docs/review.md' not found.")
            print(f"{ERROR_COLOR}Error: 'docs/review.md' not found. Please run --review first.")
            return
        try:
            temp_reader = DocumenterAgent(project_name, project_path) # Reusing agent for its read method
            feedback_content = temp_reader._read_file(review_md_path)
            if not feedback_content:
                 logger.warning(f"Review file '{review_md_path}' is empty. Proceeding without feedback.")
                 print(f"{WARN_COLOR}Warning: Review file is empty.")
            else:
                 print(f"{INFO_COLOR}Applying fixes based on 'docs/review.md'...{RESET_ALL}")
        except Exception as e:
            logger.error(f"Failed to read review file '{review_md_path}': {e}", exc_info=True)
            print(f"{ERROR_COLOR}Error reading review file: {e}")
            return

    # === Run Coder Agent ===
    print(f"{STEP_COLOR}Running Coder Agent...{RESET_ALL}")
    coder = CoderAgent(project_name=project_name, project_path=project_path)
    generated_files = []
    try:
        # Pass impl_content=None, CoderAgent will read the files itself
        generated_files = coder.run(feedback=feedback_content, impl_content=None)
        status_msg = "Code generated" if not fix else "Code fixed"
        print(f"{SUCCESS_COLOR}{status_msg} for {len(generated_files)} file(s).{RESET_ALL}")
    except Exception as e:
        logger.error(f"Coder Agent failed: {e}", exc_info=True)
        fail_msg = "Code generation" if not fix else "Code fixing"
        print(f"{ERROR_COLOR}{fail_msg} failed: {e}")
        return

    # === Notify Architect Agent if fixing based on review ===
    if fix and feedback_content:
        print(f"{STEP_COLOR}Checking if architecture needs update based on review feedback...{RESET_ALL}")
        architect = ArchitectAgent(project_name=project_name, project_path=project_path)
        try:
            # Run architect in update mode, passing review feedback as modification text
            # The architect agent needs to be designed to handle this input appropriately.
            updated_impl_path = architect.run(modification_text=f"Review feedback:\n{feedback_content}\n\nUpdate the architecture if necessary based on this feedback and the potentially changed code.", update_mode=True)
            print(f"{SUCCESS_COLOR}Architecture check completed. Plan potentially updated: {updated_impl_path}{RESET_ALL}")
        except Exception as e:
            logger.error(f"Architect Agent check/update failed after code fix: {e}", exc_info=True)
            print(f"{WARN_COLOR}Warning: Code fixed, but failed to check/update architecture: {e}{RESET_ALL}")

    logger.info(f"Code generation/fixing (--code) completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Code generation/fixing finished successfully for project '{project_name}'.{RESET_ALL}")


async def handle_review_command(project_name: str, projects_dir: str, execute_command_func):
    """Handles the --review command: Runs Reviewer Agent and saves report to review.md."""
    logger.info(f"Handling '--review' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path):
        logger.error(f"Project '{project_name}' not found.")
        print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist.")
        return

    impl_md_path = os.path.join(project_path, "docs", "impl.md")
    if not os.path.exists(impl_md_path):
        logger.error(f"Cannot review: 'docs/impl.md' not found.")
        print(f"{ERROR_COLOR}Error: 'docs/impl.md' not found. Please run --build first.")
        return

    src_path = os.path.join(project_path, "src")
    if not os.path.exists(src_path) or not os.listdir(src_path):
         logger.warning(f"Source directory '{src_path}' is empty or missing. Review may be limited.")
         print(f"{WARN_COLOR}Warning: Project source directory is empty or missing.")
         # Decide if review should proceed or stop
         # return # Option: Stop if no code exists

    # Read implementation plan content
    impl_content = None
    try:
        temp_reader = DocumenterAgent(project_name, project_path)
        impl_content = temp_reader._read_file(impl_md_path)
        if not impl_content: raise IOError("Implementation plan file is empty.")
    except Exception as e:
        logger.error(f"Failed to read implementation plan '{impl_md_path}': {e}", exc_info=True)
        print(f"{ERROR_COLOR}Error reading implementation plan: {e}")
        return

    # === Run Reviewer Agent ===
    print(f"{STEP_COLOR}Running Reviewer Agent...{RESET_ALL}")
    reviewer = ReviewerAgent(project_name=project_name, project_path=project_path)
    review_md_path = os.path.join(project_path, "docs", "review.md")
    try:
        # Assuming reviewer.run now handles writing the review to 'docs/review.md'
        # and potentially returns a summary or status.
        # We might need to adjust the ReviewerAgent's run method signature and logic.
        # For now, let's assume it takes impl_content and writes the file.
        # The original run returned (passed, feedback), we might need to adapt.
        # Let's call it assuming it performs the review and writes the file.
        # We might need to modify the agent later.
        review_result = reviewer.run(impl_content=impl_content) # Pass impl_content

        # Check if the review file was created
        if os.path.exists(review_md_path):
            print(f"{SUCCESS_COLOR}Code review completed. Report saved to: {review_md_path}{RESET_ALL}")
            # Optionally print summary if reviewer.run returns one
            # if isinstance(review_result, str): print(review_result)
        else:
             logger.error(f"Reviewer agent ran but did not create '{review_md_path}'.")
             print(f"{ERROR_COLOR}Review failed: Report file was not generated.")
             return

    except Exception as e:
        logger.error(f"Reviewer Agent failed: {e}", exc_info=True)
        print(f"{ERROR_COLOR}Code review failed: {e}")
        return

    logger.info(f"Review (--review) completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Review finished successfully for project '{project_name}'.{RESET_ALL}")



def handle_reset_command(project_name: str, projects_dir: str):
    logger.info(f"Handling '--reset' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
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

def handle_scratch_command(project_name: str, projects_dir: str):
    logger.info(f"Handling '--scratch' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
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
    action_group.add_argument('--analyze', action='store_true', help='Perform market analysis for idea (requires --project)')
    action_group.add_argument('--update', type=str, metavar='TEXT', help='Update impl, code, tests, docs based on instructions (requires --project)')
    action_group.add_argument('--generate-doc', type=str, metavar='TYPE', help=f"Generate specific doc (requires --project).\nTypes: {', '.join(sorted(DocumenterAgent.SUPPORTED_DOC_TYPES))}")
    action_group.add_argument('--build', action='store_true', help='Generate/update architecture docs (impl.md) (requires --project)')
    action_group.add_argument('--code', action='store_true', help='Generate/update code based on impl.md (requires --project)')
    action_group.add_argument('--fix', action='store_true', help='Generate/update code based on impl.md (requires --project)')
    action_group.add_argument('--review', action='store_true', help='Review generated code and create review.md (requires --project)')
    action_group.add_argument('--reset', action='store_true', help='Reset generated files (docs, reqs) (requires --project)')
    action_group.add_argument('--scratch', action='store_true', help='Reset + clear src/tests/venv (requires --project)')

    # --- Common Arguments ---
    parser.add_argument('--project', type=str, metavar='NAME', help='Project name (required for most actions)')
    parser.add_argument('--projects-dir', type=str, metavar='PATH', default=DEFAULT_PROJECTS_DIR,
                        help=f'Directory to store projects (default: {DEFAULT_PROJECTS_DIR})')
    args = parser.parse_args()
    logger.info(f"Parsed arguments: {vars(args)}")
    project_name = args.project
    # Determine the effective projects directory
    projects_dir = os.path.abspath(args.projects_dir)
    logger.info(f"Using projects directory: {projects_dir}")
    # Ensure the projects directory exists if we're not just listing
    if not args.list and not os.path.exists(projects_dir):
        try:
            os.makedirs(projects_dir)
            logger.info(f"Created projects directory: {projects_dir}")
        except OSError as e:
            logger.error(f"Failed to create projects directory '{projects_dir}': {e}")
            print(f"{ERROR_COLOR}Error: Could not create projects directory '{projects_dir}'.")
            sys.exit(1)
    # --- Dispatch ---
    try:
        if args.list: handle_list_command(projects_dir)
        elif args.idea: handle_idea_command(idea_text=args.idea, project_name=project_name, projects_dir=projects_dir)
        elif args.update_idea:
            if not project_name: parser.error("--update-idea requires --project NAME")
            handle_update_idea_command(modification_text=args.update_idea, project_name=project_name, projects_dir=projects_dir)
        elif args.research:
            if not project_name: parser.error("--research requires --project NAME")
            handle_research_command(project_name=project_name, projects_dir=projects_dir)
        elif args.analyze:
            if not project_name: parser.error("--analyze requires --project NAME")
            handle_analyze_idea_command(project_name=project_name, projects_dir=projects_dir)
        elif args.generate_doc:
            if not project_name: parser.error("--generate-doc requires --project NAME")
            if args.generate_doc not in DocumenterAgent.SUPPORTED_DOC_TYPES: parser.error(f"Invalid --doc-type '{args.generate_doc}'. Supported: {', '.join(DocumenterAgent.SUPPORTED_DOC_TYPES)}")
            handle_generate_doc_command(doc_type=args.generate_doc, project_name=project_name, projects_dir=projects_dir)
        elif args.reset:
            if not project_name: parser.error("--reset requires --project NAME")
            handle_reset_command(project_name=project_name, projects_dir=projects_dir)
        elif args.scratch:
            if not project_name: parser.error("--scratch requires --project NAME")
            handle_scratch_command(project_name=project_name, projects_dir=projects_dir)
        # Async handlers
        elif args.update:
            if not project_name: parser.error("--update requires --project NAME")
            await handle_update_command(modification_text=args.update, project_name=project_name, projects_dir=projects_dir, execute_command_func=execute_command_func)
        elif args.build:
            if not project_name: parser.error("--build requires --project NAME")
            await handle_build_command(project_name=project_name, projects_dir=projects_dir, execute_command_func=execute_command_func)
        elif args.code:
            if not project_name: parser.error("--code requires --project NAME")
            await handle_code_command(project_name=project_name, fix=args.fix, projects_dir=projects_dir, execute_command_func=execute_command_func)
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