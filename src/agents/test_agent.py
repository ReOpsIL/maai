import os

import re
import subprocess
import sys
import shutil
import glob
from .base_agent import BaseAgent
from .coder import CoderAgent


class TesterAgent(BaseAgent):
    """
    Generates and executes unit/integration tests based on the implementation
    details (impl_*.md) and the generated source code.
    """

    def run(self) -> list[str]:
        """
        Executes the Tester agent's task: generating or updating test files.
        Does NOT execute the tests.

        Args:
            impl_content: Optional pre-read content of impl_*.md. If None, reads from file.

        Returns:
            A list of absolute paths to the generated  test files.
        """
        self.logger.info(f"Running Tester Agent for project: {self.project_name}")
       
        coder = CoderAgent(project_name=self.project_name, project_path=self.project_path)
        all_content, _ = coder.get_all_content()
        
        # --- Read Context (Source Code, Existing Tests if updating) ---
        self.logger.info(f"Reading source code from: {self.src_path}")
        source_code = coder.read_all_code_files()
        if not source_code:
            self.logger.warning(f"No source code found in {self.src_path}.")
            raise RuntimeError(f"Tester Agent failed during test generation: No source code found in project path") 
       
        # --- Generate or Update Test Cases ---
        self.logger.info("Attempting to generate test cases using AI.")
        generated_test_files_content = ""
        try:
            generated_test_files_content = self._generate(
                all_content=all_content,
                source_code=source_code
            )

            self.logger.info("Received tests generation response from LLM API.")
            self.logger.debug(f"Generated Text (first 200 chars):\n{generated_test_files_content[:200]}...")

            # --- Parsing the generated text into files ---
            # Use the existing robust parser
            generated_content = coder._parse_code_blocks(generated_test_files_content)
            if not test_files:
                 # This is more critical now, as it means no code was generated 
                 self.logger.warning("AI response parsed, but no valid code blocks (```python filename=...```) found.")
                 # Returning empty dict, the caller handles the warning/error.

            test_files = coder._write_code_files(generated_content)

            log_action =  "generated"
            self.logger.info(f"Successfully {log_action} content for {len(generated_test_files_content)} test file(s) using AI.")

            return test_files

        except (ValueError, ConnectionError, RuntimeError) as e:
            self.logger.error(f"Failed to generate tests using AI: {e}")
            raise RuntimeError(f"Tester Agent failed during test generation: {e}") # Re-raise to signal failure
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during test generation: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred during test generation: {e}")

    def _generate(self, impl_content: str, source_code: str) -> dict[str, str]:
        """Uses Generative AI to create or update pytest test cases."""
        # Model initialization is now handled by BaseAgent
        if not self.model:
            self.logger.error("Generative model not initialized in BaseAgent. Cannot proceed.")
            raise RuntimeError("TesterAgent requires a configured Generative Model.")

        # Create mode
        prompt = self._create_test_prompt(impl_content, source_code)
        self.logger.debug(f"Generated create prompt for LLM (Tester):\n{prompt[:500]}...")
        try:
            self.logger.info("Sending request to LLM API for test generation...")
            # May need higher token limits for tests + source code context
            # generation_config = genai.types.GenerationConfig(max_output_tokens=8192)
            # response = model.generate_content(prompt, generation_config=generation_config)
            generated_text = self.model.generate_content(prompt)
            self.logger.info("Received test generation response from LLM API.")
            self.logger.debug(f"Generated Test Text (first 200 chars):\n{generated_text[:200]}...")

            return generated_text
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM API call (Tester): {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate tests using AI: {e}")

    def _create_test_prompt(self, md_content: str, source_code: str) -> str: # For initial creation
        """Creates the prompt for the generative AI model to generate tests from scratch."""

        prompt = f"""
        **Act as a Test Automation Engineer.** Your task is to generate unit test code based on the provided project documentation and source code.
**Input:**

1.  **Project Documentation (Markdown):** Contains project idea, features, integration details, and implementation plans.
    ```markdown
    {md_content}
    ```

2.  **Project Source Code:** The existing source code generated for the project.
    ```markdown
    {source_code}
    ```

**Instructions:**

1.  **Analyze Language & Platform:** First, analyze the provided source code and markdown documents to determine the primary programming language(s) (e.g., Python, Java, Kotlin, JavaScript, TypeScript, Swift, etc.) and target platform(s) (e.g., Backend Service, Android App, iOS App, Web Frontend).

2.  **Select Testing Framework:** Based on the identified language(s) and platform(s), select the standard and appropriate unit testing framework. Use established conventions:
    *   **Python:** `pytest`
    *   **Java (Backend/Android):** `JUnit 4` or `JUnit 5` (prefer 5 if unsure)
    *   **Kotlin (Backend/Android):** `JUnit 4` or `JUnit 5` (often used with libraries like `mockk`)
    *   **JavaScript/TypeScript (Node.js/Web):** `Jest` or `Vitest` (prefer `Jest` if unsure or React is used, `Vitest` for Vite projects)
    *   **Swift (iOS):** `XCTest`
    *   *If the framework choice isn't obvious, state the chosen framework and briefly justify it before the code blocks.*

3.  **Select Mocking Library:** Use standard mocking libraries appropriate for the chosen language and framework:
    *   **Python:** `unittest.mock` (built-in)
    *   **Java:** `Mockito`
    *   **Kotlin:** `Mockito-Kotlin` or `Mockk` (prefer `Mockk` if Kotlin is primary)
    *   **JavaScript/TypeScript (Jest/Vitest):** Built-in mocking capabilities (`jest.mock()`, `vi.mock()`)
    *   **Swift:** May involve protocol-based mocking or libraries like `Cuckoo` or `SwiftyMocky`. Use protocols if simple.

4.  **Generate Unit Test Files:** Create test files following the standard naming and location conventions for the selected framework/language/platform:
    *   `pytest`: `tests/test_*.py`
    *   `JUnit (Maven/Gradle)`: `src/test/java/your/package/path/*Test.java` or `src/test/kotlin/your/package/path/*Test.kt`
    *   `Jest/Vitest`: `src/**/__tests__/*.test.js` or `src/**/*.spec.ts` (or similar common patterns)
    *   `XCTest`: Within the designated Test target in Xcode, typically `YourProjectTests/YourFileTests.swift`

5.  **Testing Scope:** Focus on testing the public functions, methods, classes, components, or interfaces defined in the source code and described in the implementation plan or features documents. Aim for *unit* tests, isolating the code under test.

6.  **Coverage:** Write tests to cover:
    *   Key functionalities and expected ("happy path") outcomes.
    *   Common edge cases (e.g., empty inputs, null values, zero values).
    *   Potential error conditions or exception handling described or implied.

7.  **Setup/Teardown & Mocking:**
    *   Use standard mechanisms for test setup/teardown (e.g., `setUp/tearDown` methods, `@BeforeEach/@AfterEach` annotations, `pytest` fixtures, `beforeEach/afterEach` in JS).
    *   Use the selected mocking library to mock dependencies (external API calls, database interactions, complex objects, platform APIs like Android SDK classes where feasible in unit tests) to isolate the unit under test.

8.  **Imports:** Include necessary import statements for the testing framework, mocking libraries, and the specific code modules/classes/functions being tested. Follow language and project structure conventions. Assume tests can access the source code (e.g., adjust Python imports like `from src.module import function`, use correct Java/Kotlin package imports, etc.).
9.  **Assertions:** Write clear assertions using the standard assertion functions provided by the chosen testing framework (e.g., `assert` in pytest, `assertEquals`/`assertTrue`/`assertThrows` in JUnit, `expect().toBe()`/`expect().toHaveBeenCalledWith()` in Jest/Vitest, `XCTAssertEqual`/`XCTAssertTrue` in XCTest).
10. **Output Structure:** Structure the output clearly using Markdown code blocks. **Crucially, prefix (<<<FILENAME ...) each code block with the intended filename relative to the project root or conventional test source root and close each code block with postfix (>>>).**

    *Example (Python/pytest):*
    <<<FILENAME: tests/test_some_module.py
    # Contents of tests/test_some_module.py
    import pytest
    from unittest.mock import patch, MagicMock
    from src.some_module import process_data # Adjust import

    # ... tests ...
    >>>

    *Example (Java/JUnit5/Mockito):*
    <<<FILENAME: src/test/java/com/example/service/DataProcessorTest.java
    package com.example.service;

    import com.example.repository.DataRepository;
    import org.junit.jupiter.api.Test;
    import org.junit.jupiter.api.extension.ExtendWith;
    import org.mockito.InjectMocks;
    import org.mockito.Mock;
    import org.mockito.junit.jupiter.MockitoExtension;

    import static org.junit.jupiter.api.Assertions.*;
    import static org.mockito.Mockito.*;

    @ExtendWith(MockitoExtension.class)
    class DataProcessorTest {{

        @Mock
        private DataRepository mockRepository;

        @InjectMocks
        private DataProcessor systemUnderTest;

        @Test
        void testProcessData_Success() {{
            // Given
            when(mockRepository.fetchData(anyString())).thenReturn("Sample Data");

            // When
            String result = systemUnderTest.processData("id123");

            // Then
            assertEquals("Processed: Sample Data", result);
            verify(mockRepository).fetchData("id123");
        }}
        // ... other tests ...
    }}
    >>>

    *Example (TypeScript/Jest):*
    <<<FILENAME: src/services/__tests__/apiClient.test.ts
    import {{ fetchData }} from '../apiClient';
    import axios from 'axios'; // Assuming axios is used

    jest.mock('axios');
    const mockedAxios = axios as jest.Mocked<typeof axios>;

    describe('apiClient', () => {{
      it('fetchData should return data on success', async () => {{
        // Given
        const mockData = {{ id: 1, name: 'Test Item' }};
        mockedAxios.get.mockResolvedValue({{ data: mockData }});

        // When
        const result = await fetchData('/items/1');

        // Then
        expect(result).toEqual(mockData);
        expect(mockedAxios.get).toHaveBeenCalledWith('/items/1');
      }});
      // ... other tests ...
    }});
    >>>

11. **Code Only:** Generate only the test code files within the formatted Markdown code blocks. Do not add explanatory text outside the code blocks unless it's a comment within the code itself.
12. **Ambiguity:** If the documentation or source code is ambiguous regarding specific behaviors needed for testing, make reasonable assumptions, 
implement the test based on that assumption, and add a comment (e.g., `# TODO: Verify this assumption` or `// TODO: Clarify expected behavior for null input`).
 Generate the unit tests now based on the provided inputs and these instructions.
"""
        return prompt

  
