import argparse
from ast import arg
import logging
import os
import sys
import shutil
import asyncio
import re
import json

from dotenv import load_dotenv

from colorama import Fore, Style, init as colorama_init
import glob

# Initialize colorama
colorama_init(autoreset=True)

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils import slugify, load_config
# Import agents
from agents import (
    InnovatorAgent, ArchitectAgent, CoderAgent, ReviewerAgent, TesterAgent,
    DocumenterAgent, MarketAnalystAgent, ResearchAgent, BusinessAgent, ScoringAgent,
    IdeaGenAgent, CheckListTasksAgent, DiagramAgent, ImplTasksAgent
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


def handle_list_command(projects_dir: str):
    list_projects(projects_dir)

def handle_idea_list_gen_command(idea_subject_text: str, subject_name:str, num_ideas: int, project_name: str | None, projects_dir: str, wild_mode: bool):
    logger.info(f"Handling '--idea' action: Subject='{idea_subject_text[:50]} - Number of ideas to generate: {num_ideas}...', Project='{project_name}'")
    print(f"{AGENT_COLOR}Initializing IdeaGenAgent...{RESET_ALL}")
    project_path = get_project_path(project_name, projects_dir)

    idea_list_gen = IdeaGenAgent(project_name=project_name, project_path=project_path)
    try:
        idea_list_json_path = idea_list_gen.run(idea_subject_text=idea_subject_text, subject_name=subject_name, num_ideas=num_ideas, wild_mode=wild_mode)
        print(f"{SUCCESS_COLOR}Successfully processed idea subject for project '{project_name}'. Concept saved to: {idea_list_json_path}")
    except Exception as e: logger.error(f"IdeaGenAgent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error processing idea: {e}")

def clean_text(text):
    # Replace any character that is not a-z, A-Z, or 0-9 with an underscore
    return re.sub(r'[^a-zA-Z0-9]', '_', text)

def handle_idea_list_bulk_command(bulk_file: str, project_name: str | None, projects_dir: str, wild_mode: bool):
    with open(bulk_file, 'r') as f:
        data = json.load(f)

    startup_ideas = data.get("startup_ideas", [])
    for idea in startup_ideas:
        print(f"ID: {idea['id']}")
        print(f"Category: {idea['category']}")
        print(f"Title: {idea['title']}")
        print(f"Description: {idea['description']}")
        print("-" * 40)

        new_project_name = clean_text(f"{idea['id']}_{idea['title']}")
        new_projects_dir = os.path.join(projects_dir, clean_text(idea['category']))

        os.makedirs(new_projects_dir, exist_ok=True)
        handle_idea_command(idea['description'], project_name=new_project_name, projects_dir=new_projects_dir, wild_mode=wild_mode)
        handle_business_command(project_name=new_project_name, projects_dir=new_projects_dir)
        handle_scoring_command(project_name=new_project_name, projects_dir=new_projects_dir)

def handle_idea_command(idea_text: str, project_name: str | None, projects_dir: str, wild_mode: bool):
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
        idea_md_path = innovator.run(idea_text=idea_text, wild_mode=wild_mode)
        print(f"{SUCCESS_COLOR}Successfully processed idea for project '{project_name}'. Concept saved to: {idea_md_path}")
    except Exception as e: logger.error(f"Innovator Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error processing idea: {e}")

def handle_check_list_tasks_command(project_name: str | None, projects_dir: str):
    logger.info(f"Handling '--check-list-tasks', Project='{project_name}'")
    project_path = get_project_path(project_name, projects_dir)
    print(f"{AGENT_COLOR}Initializing CheckListTasks Agent...{RESET_ALL}")
    tasks = CheckListTasksAgent(project_name=project_name, project_path=project_path)
    try:
        tasks_md_path = tasks.run()
        print(f"{SUCCESS_COLOR}Successfully genrated check list tasks  for the project '{project_name}'. Check list report saved to: {tasks_md_path}")
    except Exception as e: logger.error(f"CheckListTasksAgent Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error geenrating check list tasks for project: {e}")


def handle_impl_tasks_command(project_name: str | None, projects_dir: str):
    logger.info(f"Handling '--impl-tasks', Project='{project_name}'")
    project_path = get_project_path(project_name, projects_dir)
    print(f"{AGENT_COLOR}Initializing ImplTasks Agent...{RESET_ALL}")
    tasks = ImplTasksAgent(project_name=project_name, project_path=project_path)
    try:
        impl_tasks_md_path = tasks.run()
        print(f"{SUCCESS_COLOR}Successfully genrated implemntation tasks  for the project '{project_name}'. Check list report saved to: {impl_tasks_md_path}")
    except Exception as e: logger.error(f"ImplTasksAgent Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error geenrating implementation tasks for project: {e}")


def handle_tests_command(project_name: str | None, projects_dir: str):
    logger.info(f"Handling '--tests', Project='{project_name}'")
    project_path = get_project_path(project_name, projects_dir)
    print(f"{AGENT_COLOR}Initializing Tester Agent...{RESET_ALL}")
    tester = TesterAgent(project_name=project_name, project_path=project_path)
    try:
        tests_path = tester.run()
        print(f"{SUCCESS_COLOR}Successfully genrated testing code for the project '{project_name}'. Tasks report saved to: {tests_path}")
    except Exception as e: logger.error(f"Tester Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error geenrating testing code for project: {e}")


def handle_diagrams_command(project_name: str | None, projects_dir: str):
    logger.info(f"Handling '--diagrams', Project='{project_name}'")
    project_path = get_project_path(project_name, projects_dir)
    print(f"{AGENT_COLOR}Initializing Diagram Agent...{RESET_ALL}")
    diagrams = DiagramAgent(project_name=project_name, project_path=project_path)
    try:
        diagrams_path = diagrams.run()
        print(f"{SUCCESS_COLOR}Successfully genrated diagrams for the project '{project_name}'. Tasks report saved to: {diagrams_path}")
    except Exception as e: logger.error(f"Diagram Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error geenrating diagrams for project: {e}")

def handle_business_command(project_name: str | None, projects_dir: str):
    logger.info(f"Handling '--business', Project='{project_name}'")
    project_path = get_project_path(project_name, projects_dir)
    print(f"{AGENT_COLOR}Initializing Business Agent...{RESET_ALL}")
    business = BusinessAgent(project_name=project_name, project_path=project_path)
    try:
        business_md_path = business.run()
        print(f"{SUCCESS_COLOR}Successfully genrated business perspective for project '{project_name}'. Business report saved to: {business_md_path}")
    except Exception as e: logger.error(f"Business Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error geenrating business perspective for project: {e}")

def handle_scoring_command(project_name: str | None, projects_dir: str):
    logger.info(f"Handling '--scoring', Project='{project_name}'")
    project_path = get_project_path(project_name, projects_dir)
    print(f"{AGENT_COLOR}Initializing Scoring Agent...{RESET_ALL}")
    scoring = ScoringAgent(project_name=project_name, project_path=project_path)
    try:
        scoring_md_path = scoring.run()
        print(f"{SUCCESS_COLOR}Successfully genrated business perspective scoring for project '{project_name}'. Score report saved to: {scoring_md_path}")
    except Exception as e: logger.error(f"Scoring Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error geenrating scoring business perspective for project: {e}")


def handle_analyze_idea_command(project_name: str, projects_dir: str):
    logger.info(f"Handling '--analyze-idea' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    idea_md_path = os.path.join(project_path, "docs", "idea.md")
    if not os.path.exists(idea_md_path): logger.error(f"Cannot analyze idea: 'docs/idea.md' not found."); print(f"{ERROR_COLOR}Error: 'docs/idea.md' not found."); return
    print(f"{AGENT_COLOR}Initializing Market Analyst Agent...{RESET_ALL}")
    analyst = MarketAnalystAgent(project_name=project_name, project_path=project_path)
    try:
        analysis_md_path = analyst.run()
        print(f"{SUCCESS_COLOR}Successfully analyzed idea for project '{project_name}'. Analysis saved to: {analysis_md_path}")
    except Exception as e: logger.error(f"Market Analyst Agent failed: {e}", exc_info=True); print(f"{ERROR_COLOR}Error analyzing idea: {e}")

def handle_docs_command(doc_type: str, project_name: str, projects_dir: str):
    logger.info(f"Handling '--generate-doc' action for project: {project_name}, type: {doc_type}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path): logger.error(f"Project '{project_name}' not found."); print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist."); return
    if not os.path.exists(os.path.join(project_path, "docs", "idea.md")): logger.warning(f"Cannot find 'docs/idea.md'. Context limited.")
    if not glob.glob(os.path.join(project_path, "docs", "impl_*.md")):
        logger.warning(f"Cannot find 'docs/impl_*.md'. Context limited.")
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


async def handle_build_features_command(project_name: str, projects_dir: str, execute_command_func):
    """Handles the --build-features command: Runs the Architect Agent to generate architecture docs for features."""
    logger.info(f"Handling '--build-features' action (Architect only) for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path):
        logger.error(f"Project '{project_name}' not found.")
        print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist.")
        return
    
    print(f"{STEP_COLOR}Running Architect Agent to generate architecture plan...{RESET_ALL}")
    architect = ArchitectAgent(project_name=project_name, project_path=project_path)
    try:
        feature_impl_paths = architect.run_features_impl()
        if not feature_impl_paths: # Check if the list is empty
             raise FileNotFoundError("Architect agent did not produce any implementation files.")
        print(f"{SUCCESS_COLOR}Architecture plan generated: {', '.join(feature_impl_paths)}{RESET_ALL}")
    except Exception as e:
        logger.error(f"Architect Agent failed during --build: {e}", exc_info=True)
        print(f"{ERROR_COLOR}Architecture generation failed: {e}")
        return

    logger.info(f"Architecture generation (--build) completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Architecture generation finished successfully for project '{project_name}'.{RESET_ALL}")


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

    print(f"{STEP_COLOR}Running Architect Agent to generate architecture plan...{RESET_ALL}")
    architect = ArchitectAgent(project_name=project_name, project_path=project_path)
    try:
        # Assuming architect.run() generates  impl_*.md and potentially other docs
        # Architect agent now returns a list of paths
        impl_paths = architect.run()
        if not impl_paths: # Check if the list is empty
             raise FileNotFoundError("Architect agent did not produce any implementation files.")
        # Optional: Check if all returned paths exist
        # if not all(os.path.exists(p) for p in impl_paths):
        #     raise FileNotFoundError("Architect agent returned paths to files that do not exist.")
        print(f"{SUCCESS_COLOR}Architecture plan generated: {', '.join(impl_paths)}{RESET_ALL}")
        # Optionally read and log content if needed for subsequent steps in a different flow
        # impl_content = architect._read_file(impl_md_path)
        # if not impl_content: raise IOError("Failed to read generated impl_*.md content.")
    except Exception as e:
        logger.error(f"Architect Agent failed during --build: {e}", exc_info=True)
        print(f"{ERROR_COLOR}Architecture generation failed: {e}")
        return

    logger.info(f"Architecture generation (--build) completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Architecture generation finished successfully for project '{project_name}'.{RESET_ALL}")

async def handle_enhance_build_command(project_name: str, projects_dir: str, features: bool, execute_command_func):
    """Handles the --enhance flag: Runs the Architect Agent to generate enhanced architecture docs."""
    logger.info(f"Handling '--enhance' action (Architect only) for project: {project_name}")
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
        # Assuming architect.run() generates docs
        # Architect agent now returns a list of paths
        out_paths = architect.run_enhance_features(features=features)
        if not out_paths: # Check if the list is empty
             raise FileNotFoundError("Architect agent did not produce any enhanced features or implementation files.")

        print(f"{SUCCESS_COLOR}Architecture enhance docs generated: {', '.join(out_paths)}{RESET_ALL}")
    except Exception as e:
        logger.error(f"Architect Agent failed during --enhance: {e}", exc_info=True)
        print(f"{ERROR_COLOR}Architecture enhance generation failed: {e}")
        return

    logger.info(f"Architecture generation (--build) completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Architecture generation finished successfully for project '{project_name}'.{RESET_ALL}")


# (Removed build pipeline steps: Dependencies, Coder, Reviewer, Tester, Documenter)

async def handle_code_command(project_name: str, projects_dir: str, execute_command_func):
    """Handles the --code command: Runs Coder Agent """
    logger.info(f"Handling '--code' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path):
        logger.error(f"Project '{project_name}' not found.")
        print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist.")
        return

    # Check for existence of *any* implementation plan files
    docs_path = os.path.join(project_path, "docs")
    try:
        plan_files_exist = any(
            (f.startswith("impl_") and f.endswith(".md"))
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
        logger.error(f"Cannot code: No implementation plan files (impl_*.md, integ.md, or impl_*.md) found in '{docs_path}'.")
        print(f"{ERROR_COLOR}Error: No implementation plan files found in '{docs_path}'. Please run --build first.")
        return
    
    # === Run Coder Agent ===
    print(f"{STEP_COLOR}Running Coder Agent...{RESET_ALL}")
    coder = CoderAgent(project_name=project_name, project_path=project_path)
    generated_files = []
    try:
        generated_files = coder.run()
        status_msg = "Code generated" 
        print(f"{SUCCESS_COLOR}{status_msg} for {len(generated_files)} file(s).{RESET_ALL}")
    except Exception as e:
        logger.error(f"Coder Agent failed: {e}", exc_info=True)
        print(f"{ERROR_COLOR} Code generation failed: {e}")
        return

    logger.info(f"Code generation (--code) completed for project '{project_name}'.")
    print(f"\n{SUCCESS_COLOR}Code generation finished successfully for project '{project_name}'.{RESET_ALL}")


async def handle_review_command(project_name: str, projects_dir: str, execute_command_func):
    """Handles the --review command: Runs Reviewer Agent and saves report to review.md."""
    logger.info(f"Handling '--review' action for project: {project_name}")
    project_path = get_project_path(project_name, projects_dir)
    if not os.path.exists(project_path) or not os.path.isdir(project_path):
        logger.error(f"Project '{project_name}' not found.")
        print(f"{ERROR_COLOR}Error: Project '{project_name}' does not exist.")
        return

    impl_md_path = os.path.join(project_path, "docs", "impl_*.md")
    if not os.path.exists(impl_md_path):
        logger.error(f"Cannot review: 'docs/impl_*.md' not found.")
        print(f"{ERROR_COLOR}Error: 'docs/impl_*.md' not found. Please run --build first.")
        return

    src_path = os.path.join(project_path, "src")
    if not os.path.exists(src_path) or not os.listdir(src_path):
         logger.warning(f"Source directory '{src_path}' is empty or missing. Review may be limited.")
         print(f"{WARN_COLOR}Warning: Project source directory is empty or missing.")
         # Decide if review should proceed or stop
         # return # Option: Stop if no code exists

    # Read implementation plan content
    impl_content = ""
    try:
        impl_files = glob.glob(impl_md_path)
        if not impl_files:
            logger.error("impl_*.md not found. Cannot proceed.")
            print(f"{ERROR_COLOR}Error: impl_*.md is required for review.")
            return

        for file in impl_files:
            try:
                impl_content += DocumenterAgent(project_name, project_path)._read_file(file) + "\n\n"
            except Exception as e:
                logger.error(f"Failed to read {file}: {e}")

        if not impl_content.strip():
            logger.error("No content read from impl_*.md files. Cannot proceed.")
            print(f"{ERROR_COLOR}Error: impl_*.md is required for review.")
            return

    except Exception as e:
        logger.error(f"Failed to read implementation plan: {e}", exc_info=True)
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
    action_group.add_argument('--subject', type=str, metavar='TEXT', help='Generate new list of projects ideas based on subject (requiers --num_ideas --subject_name)')
    action_group.add_argument('--bulk', type=str, metavar='TEXT', help='Generate new projects ideas based on subject json file')
    action_group.add_argument('--idea', type=str, metavar='TEXT', help='Generate new project idea')
    action_group.add_argument('--check-list-tasks', action='store_true', help='Generate check list tasks document for the project idea.md')
    action_group.add_argument('--impl-tasks', action='store_true', help='Generate implementation tasks document for the project impl_*.md')

    action_group.add_argument('--tests', action='store_true', help='Generate tests for the project soourc code')
    action_group.add_argument('--diagrams', action='store_true', help='Generate diagrams for the project source code and documents')

    action_group.add_argument('--business', action='store_true', help='Generate business docs (business.md) (requires --project)')
    action_group.add_argument('--scoring', action='store_true', help='Generate scoring docs (scoring.md) (requires --project)')
    action_group.add_argument('--research', action='store_true', help='Perform technical research for idea (requires --project)')
    action_group.add_argument('--analyze', action='store_true', help='Perform market analysis for idea (requires --project)')
    action_group.add_argument('--docs', type=str, metavar='TYPE', help=f"Generate specific doc (requires --project).\nTypes: {', '.join(sorted(DocumenterAgent.SUPPORTED_DOC_TYPES))}")
    #action_group.add_argument('--build', action='store_true', help='Generate architecture docs (impl_*.md) (requires --project)')
    action_group.add_argument('--build-features', action='store_true', help='Generate architecture docs from (features*.md) for all features - Generates (impl_[feature]_[component]*.md) (requires --project)')
    action_group.add_argument('--enhance-features', action='store_true', help='Generate feature docs (feature_*.md) from (idea.md) for all features (requires --project)')

    action_group.add_argument('--code', action='store_true', help='Generate code based on impl_*.md (requires --project)')
    action_group.add_argument('--review', action='store_true', help='Review generated code and create review.md (requires --project)')

    # --- Common Arguments ---
    parser.add_argument('--project', type=str, metavar='NAME', help='Project name (required for most actions)')
    parser.add_argument('--projects-dir', type=str, metavar='PATH', default=DEFAULT_PROJECTS_DIR,
                        help=f'Directory to store projects (default: {DEFAULT_PROJECTS_DIR})')

    parser.add_argument('--wild', action='store_true', default=False, help='Use wild mode - innovatiove and futuristic prompt')
    parser.add_argument('--num-ideas', type=int, metavar='NUMBER', help='Number of ideas to genenrate according to subject (required subject)')
    parser.add_argument('--subject-name', type=str, metavar='TEXT', help='subject name - new json file name')

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
        if args.list:
            handle_list_command(projects_dir)
        elif args.subject:
            handle_idea_list_gen_command(idea_subject_text=args.subject, subject_name=args.subject_name, 
                                        num_ideas=args.num_ideas, project_name="unknown",
                                        projects_dir=projects_dir, wild_mode=args.wild)
        elif args.bulk:
            handle_idea_list_bulk_command(bulk_file=args.bulk, project_name="unknown", projects_dir=projects_dir, wild_mode=args.wild)
        elif args.idea:
            handle_idea_command(idea_text=args.idea, project_name=project_name, projects_dir=projects_dir, wild_mode=args.wild)
        elif args.check_list_tasks:
            handle_check_list_tasks_command(project_name=project_name, projects_dir=projects_dir)
        elif args.impl_tasks:
            handle_impl_tasks_command(project_name=project_name, projects_dir=projects_dir)
        elif args.tests:
            handle_tests_command(project_name=project_name, projects_dir=projects_dir)
        elif args.diagrams:
            handle_diagrams_command(project_name=project_name, projects_dir=projects_dir)
        elif args.business:
            handle_business_command(project_name=project_name, projects_dir=projects_dir)
        elif args.scoring:
            handle_scoring_command(project_name=project_name, projects_dir=projects_dir)
        elif args.research:
            if not project_name: parser.error("--research requires --project NAME")
            handle_research_command(project_name=project_name, projects_dir=projects_dir)
        elif args.analyze:
            if not project_name: parser.error("--analyze requires --project NAME")
            handle_analyze_idea_command(project_name=project_name, projects_dir=projects_dir)
        elif args.docs:
            if not project_name: parser.error("--docs requires --project NAME")
            if args.docs not in DocumenterAgent.SUPPORTED_DOC_TYPES: parser.error(f"Invalid doc type '{args.docs}'. Supported: {', '.join(DocumenterAgent.SUPPORTED_DOC_TYPES)}")
            handle_docs_command(doc_type=args.docs, project_name=project_name, projects_dir=projects_dir)
        elif args.build_features:
            if not project_name: 
                parser.error("--build-features requires --project NAME")
            await handle_build_features_command(project_name=project_name, projects_dir=projects_dir, execute_command_func=execute_command_func)
        elif args.enhance_features:
            if not project_name: 
                parser.error("--enhance-features requires --project NAME")
            await handle_enhance_build_command(project_name=project_name, projects_dir=projects_dir, features=True, execute_command_func=execute_command_func)
        # elif args.build:
        #     if not project_name: 
        #         parser.error("--build requires --project NAME")
        #     await handle_build_command(project_name=project_name, projects_dir=projects_dir, execute_command_func=execute_command_func)
        elif args.code:
            if not project_name: parser.error("--code requires --project NAME")
            await handle_code_command(project_name=project_name, projects_dir=projects_dir, execute_command_func=execute_command_func)
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
