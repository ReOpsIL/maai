import os
from .base_agent import BaseAgent
from .coder import CoderAgent

class ImplTasksAgent(BaseAgent):
    """
    Source code and flow ImplTasks generator.
    """

    def run(self):
        """
        Executes the ImplTasks agent's task: creating the tasks_*.md files.

        """
        self.logger.info(f"Running ImplTasks Agent for project: {self.project_name})")

        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            # Or raise a specific exception
            raise RuntimeError("ImplTasksAgent requires a configured Generative Model.")

        coder = CoderAgent(project_name=self.project_name, project_path=self.project_path)
        all_content, _ = coder.get_all_content()
        if not all_content:
            self.logger.warning(f"No project markdown documents found in {self.src_path}.")
            raise RuntimeError(f"ImplTasks Agent failed during ImplTasks generation: project markdown documents found in project path") 
       
        # --- Generate or Update Test Cases ---
        self.logger.info("Attempting to generate impl.. tasks using AI.")
        generated_tasks_files_content = ""
        try:
            create_tasks_prompt = self._create_impl_tasks_prompt(all_content)

            generated_tasks_files_content = self.model.generate_content(create_tasks_prompt)
            if not generated_tasks_files_content:
                raise RuntimeError(f"ImplTasks Agent failed during  impl.. tasks generation)") 
    
            self.logger.info("Received ImplTasks generation response from LLM API.")
            self.logger.debug(f"Generated Text (first 200 chars):\n{generated_tasks_files_content[:200]}...")

            # --- Parsing the generated text into files ---
            # Use the existing robust parser
            generated_content = coder._parse_code_blocks(generated_tasks_files_content)
            if not generated_content:
                # This is more critical now, as it means no code was generated 
                raise RuntimeError(f"AI response parsed, but no valid code blocks (<<<FILENAME: ...) found.") # Re-raise to signal failure

            impl_tasks_files = coder._write_code_files(generated_content)
          
            log_action =  "generated"
            self.logger.info(f"Succesfully {log_action} content for {len(impl_tasks_files)} impl tasks file(s) using AI.")
            
            return impl_tasks_files

        except (ValueError, ConnectionError, RuntimeError) as e:
            self.logger.error(f"Failed to generate ImplTasks using AI: {e}")
            raise RuntimeError(f"ImplTasks Agent failed during ImplTasks generation: {e}") # Re-raise to signal failure
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during ImplTasks generation: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred during ImplTasks generation: {e}")


    def _create_impl_tasks_prompt(self, files_content: str) -> str: 
        """Creates a ImplTasks prompt for the generative AI model."""

        prompt = f"""
        Given the following implementation documents `(impl_*.md)`, extract and generate a comprehensive, step-by-step task list. 
        
        Instructions:
        1. Generate tasks lists `(task_*.md)` for **ALL** implementation files.
        2. **Details and granduarity:** Each task should be as detailed and granular as possible to ensure full coverage of the implementation. 
        3. **Developer oriented task list:** The resulting task list files should be suitable for direct execution (either by a software developer for manual tasks or by an LLM-based coding agent for code generation) and 
            should leave no part of the implementation incomplete or unspecified. 
        4. **Full covarege:** Ensure that no steps, configurations, validations, or edge cases are omitted.
        5. **Task file name:** Task list file name `(task_*.md)` should be generated according to implementation file names `(impl_*.md)`
        6. **Mandatory Output Format:** The output structure is critical. You *must* follow the format specified below for *every* generated task list file `(tasks_*.md)`.
            *   Enclose each implementation complete tasks list within a fenced code block.
            *   **Prefix** each code block with `<<<FILENAME: path/to/[task list name].md` on its own line. Use a relevant path and filename (e.g., `tasks/task_aaa.md`, `tasks/task_bbb.md`).
            *   **Postfix** each code block with `>>>` on its own line.

        The implementation documents:

        ```
        {files_content}
        ```

        **Required tasks output Format example:**

        <<<FILENAME: tasks/task_aaa.md

            **Task List: Algorithm Cost & Reimbursement Input Backend (id_algorithm_cost_reimbursement_input_backend)**

            **Phase 1: Project Setup & Dependencies**

            1.  **Navigate to Project Root:**
                *   Action: Change directory to the root of your backend project.
                *   Command (example): `cd /path/to/your/project/backend/`

            2.  **Verify Python Version:**
                *   Action: Ensure Python 3.9+ is installed and active in the environment.
                *   Command (example): `python --version`
                *   Expected: Output showing Python 3.9.x or higher.

            3.  **Create/Update `requirements.txt`:**
                *   Action: Add or update `backend/requirements.txt` with necessary dependencies.
                *   Content to add/ensure:
                    ```
                    fastapi # Assuming FastAPI based on router usage
                    uvicorn[standard] # For running FastAPI
                    pydantic
                    sqlalchemy
                    psycopg2-binary # PostgreSQL adapter
                    alembic # For database migrations
                    pytest # For testing
                    httpx # For TestClient in integration tests
                    # Add any other existing dependencies
                    ```
                *   Verification: `requirements.txt` is updated.

            4.  **Install/Update Dependencies:**
                *   Action: Install or update dependencies from `requirements.txt`.
                *   Command (example): `pip install -r requirements.txt` (preferably within a virtual environment)
                *   Verification: All packages install successfully.

            5.  **Initialize Alembic (if not already set up):**
                *   Action: If Alembic is not yet used for migrations in this project, initialize it.
                *   Command (example): `alembic init alembic` (run in `backend/`)
                *   Configuration:
                    *   Update `alembic.ini` to point to your database URL (`sqlalchemy.url = postgresql://user:password@host/dbname`).
                    *   Update `alembic/env.py` to import your SQLAlchemy models (`from src.db.models import Base` and set `target_metadata = Base.metadata`).

            **Phase 2: Database Model & Migration**

            1.  **Locate/Create `backend/src/db/models.py`:**
                *   Action: Ensure the file `backend/src/db/models.py` exists.
                *   Verification: File is present.

            2.  **Update `Scenario` SQLAlchemy Model:**
                *   Action: Modify the `Scenario` model in `backend/src/db/models.py`.
                *   Details:
                    *   Import `JSONB` from `sqlalchemy.dialects.postgresql`.
                    *   Import `Column`, `Integer`, `String`, etc., from `sqlalchemy` if not already.
                    *   Add the new column: `algorithm_costs_reimbursement = Column(JSONB, nullable=True, default=lambda: {{}})`
                        *   `nullable=True`: Allows existing scenarios to not have this data initially.
                        *   `default=lambda: {{}}`: Provides a default empty JSON object for new scenarios if no data is provided. Consider if a more structured default is needed.
                *   Example Snippet (conceptual):
                    ```python
                    from sqlalchemy import Column, Integer, String, Float, DateTime # ... and other types
                    from sqlalchemy.dialects.postgresql import JSONB
                    from sqlalchemy.ext.declarative import declarative_base

                    Base = declarative_base()

                    class Scenario(Base):
                        __tablename__ = "scenarios"
                        id = Column(Integer, primary_key=True, index=True)
                        # ... other existing columns ...
                        algorithm_costs_reimbursement = Column(JSONB, nullable=True, default=lambda: {{}})
                        # ... other existing columns ...
                    ```
                *   Verification: `algorithm_costs_reimbursement` column is added to the `Scenario` model definition.

            3.  **Create Database Migration Script:**
                *   Action: Generate a new Alembic migration script.
                *   Command (example): `alembic revision -m "add_algorithm_costs_reimbursement_to_scenarios"`
                *   Verification: A new migration file is created in `alembic/versions/`.

            4.  **Edit Migration Script:**
                *   Action: Edit the newly generated migration script.
                *   Details:
                    *   In the `upgrade()` function, add `op.add_column('scenarios', sa.Column('algorithm_costs_reimbursement', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{{}}'::jsonb")))`.
                        *   Using `server_default` ensures the database handles the default for existing NULLs if desired, or for direct DB inserts. `sa.text("'{{}}'::jsonb")` is a common way to set a JSONB default.
                    *   In the `downgrade()` function, add `op.drop_column('scenarios', 'algorithm_costs_reimbursement')`.
                *   Verification: Migration script correctly defines adding and dropping the column.

            5.  **Apply Database Migration:**
                *   Action: Run the migration to update the database schema.
                *   Pre-requisite: Ensure PostgreSQL database is running and accessible.
                *   Command (example): `alembic upgrade head`
                *   Verification:
                    *   Command completes successfully.
                    *   Inspect the `scenarios` table in PostgreSQL to confirm the `algorithm_costs_reimbursement` column (of type JSONB) exists.
        >>>
        
        <<<FILENAME: tasks/task_bbb.md

            **Task List: Algorithm Cost & Reimbursement Input Backend (id_blind_cost_reimbursement_input_backend)**

            **Phase 1: Core Logic - Validation Model**

            1.  **Locate/Create `backend/src/core/validation.py`:**
                *   Action: Ensure the file `backend/src/core/validation.py` exists.
                *   Verification: File is present.

            2.  **Define `AlgorithmCostReimbursementData` Pydantic Model:**
                *   Action: Implement the Pydantic model in `backend/src/core/validation.py`.
                *   Details:
                    ```python
                    from pydantic import BaseModel, Field

                    class AlgorithmCostReimbursementData(BaseModel):
                        acquisition_cost: float = Field(..., ge=0, description="Acquisition cost of the algorithm/software.")
                        annual_maintenance_cost: float = Field(..., ge=0, description="Annual maintenance or subscription cost.")
                        cost_per_scan: float = Field(..., ge=0, description="Cost incurred per scan processed by the algorithm.")
                        implementation_costs: float = Field(..., ge=0, description="One-time costs for implementation and setup.")
                        training_costs: float = Field(..., ge=0, description="One-time costs for training staff.")
                        estimated_reimbursement_per_scan: float = Field(..., ge=0, description="Estimated direct reimbursement received per scan when using the algorithm.")
                        amortization_period: int = Field(..., ge=1, description="Amortization period for upfront costs in years (must be 1 or greater).")
                        estimated_radiologist_hourly_cost: float = Field(..., ge=0, description="Estimated hourly cost of a radiologist for workflow calculations.")

                        class Config:
                            orm_mode = True # If you intend to return this model directly from an ORM object
                            # Consider adding example data for OpenAPI docs
                            schema_extra = {{
                                "example": {{
                                    "acquisition_cost": 50000.00,
                                    "annual_maintenance_cost": 10000.00,
                                    "cost_per_scan": 5.00,
                                    "implementation_costs": 2000.00,
                                    "training_costs": 3000.00,
                                    "estimated_reimbursement_per_scan": 10.00,
                                    "amortization_period": 5,
                                    "estimated_radiologist_hourly_cost": 150.00
                                }}
                            }}
                    ```
                *   Verification: Model is defined with all specified fields, types, and validation constraints (`ge=0`, `ge=1`).

            **Phase 2: Core Logic - Calculations**

            1.  **Locate/Create `backend/src/core/calculations.py`:**
                *   Action: Ensure the file `backend/src/core/calculations.py` exists.
                *   Verification: File is present.

            2.  **Update `CalculationEngine` (or relevant calculation module/class):**
                *   Action: Modify the `CalculationEngine` to incorporate the new cost and reimbursement data.
                *   Details:
                    *   The engine must now be able to access `algorithm_costs_reimbursement` data (likely passed in or retrieved from a `Scenario` object).
                    *   It will also need `Total Scans Processed by AI` (from Market/Adoption module) and `Impact on Radiologist Reading Time` (from AI Performance module). How these are passed to the engine is critical. Assume they are available as input parameters or attributes of an object passed to the calculation methods.

            3.  **Implement `Amortized Implementation Cost` Calculation:**
                *   Action: Add logic to calculate this within `CalculationEngine`.
                *   Formula: `(implementation_costs + training_costs + acquisition_cost) / amortization_period`
                *   Input: `implementation_costs`, `training_costs`, `acquisition_cost`, `amortization_period` (from `AlgorithmCostReimbursementData`).
                *   Edge Cases:
                    *   `amortization_period` is guaranteed to be `>= 1` by Pydantic, so no division by zero from that.
                    *   Handle cases where costs are zero.
                *   Example Snippet (conceptual):
                    ```python
                    # Inside CalculationEngine class or relevant function
                    def calculate_amortized_implementation_cost(self, costs_data: AlgorithmCostReimbursementData) -> float:
                        if costs_data.amortization_period == 0: # Should be caught by Pydantic (ge=1)
                            return float('inf') # Or handle as error
                        total_upfront_costs = (
                            costs_data.implementation_costs +
                            costs_data.training_costs +
                            costs_data.acquisition_cost
                        )
                        return total_upfront_costs / costs_data.amortization_period
                    ```   
        >>>
        """
    
        return prompt
