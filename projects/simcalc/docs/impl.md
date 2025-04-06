```markdown
# Implementation Plan: Kid-Friendly Web Calculator (Pink Edition)

This plan outlines the steps and components required to build the Kid-Friendly Web Calculator application based on the provided project concept.

## 1. Overall Architecture

The application will primarily be a single-page application (SPA) built with React. Basic calculations (+, -, *, /) will be handled client-side within the React application for immediate feedback and simplicity. A minimal Python Flask backend will serve the static React application files and provide a foundation for potential future API endpoints (e.g., for themes, gamification).

**Components:**

1.  **Frontend (React App):** The user interface, including buttons, display, and logic for performing calculations. Responsible for rendering the pink-themed design, handling user input, managing calculation state, displaying results and errors, and playing optional sounds.
2.  **Backend (Flask API - Minimal):** Primarily responsible for serving the built React application's static files (HTML, CSS, JS). A placeholder API endpoint for calculation can be included but might not be used initially if calculations remain client-side.
3.  **Web Server (Development):** Node.js development server (via Create React App) for the frontend, Flask development server for the backend.
4.  **Web Server (Production):** A production-grade server like Gunicorn + Nginx (or platform-specific services like Vercel/Netlify for frontend, Heroku/PythonAnywhere for backend) will host the application.

**Interaction Flow:**

```mermaid
graph TD
    U[User] --> FE[React Frontend (Browser)]
    FE -->|Button Clicks, Input| FE_Logic{Client-Side Calc Logic}
    FE_Logic --> FE_State{React State}
    FE_State --> FE_UI{UI Update (Display, Feedback)}
    FE_UI --> U
    U --> BrowserNav[Browser Navigation]
    BrowserNav --> BE[Flask Backend]
    BE -->|Serves Static Files| FE
    subgraph Client-Side
        FE
        FE_Logic
        FE_State
        FE_UI
    end
    subgraph Server-Side (Initial: Serving Only)
        BE
    end

    %% Optional Backend Calculation Flow (Future Enhancement or Alternative)
    %% FE -->|API Request /calculate| BE_API[Flask API Endpoint]
    %% BE_API -->|Processes Calculation| BE_Logic{Backend Calc Logic}
    %% BE_Logic --> BE_API
    %% BE_API -->|API Response| FE
```

*   **Initial Implementation:** User interacts with React frontend. All calculations happen client-side. Flask backend serves the initial HTML/JS/CSS bundle.
*   **Future/Alternative:** User interacts with React frontend. Button clicks trigger API calls to the Flask backend's `/calculate` endpoint. Backend performs the calculation and returns the result to the frontend for display.

## 2. Technology Stack

*   **Frontend:**
    *   **Framework/Library:** React.js (v18+) (using Create React App or Vite for setup)
    *   **Language:** JavaScript (ES6+) or TypeScript (Optional)
    *   **Styling:** CSS3 / CSS Modules. Emphasis on **pink color palettes** and child-friendly aesthetics. (Consider styled-components or Tailwind CSS for easier theming if future themes are prioritized).
    *   **State Management:** React Context API or `useState`/`useReducer` hooks.
    *   **HTTP Client (If Backend Calc):** `fetch` API or `axios`.
    *   **Audio:** HTML5 Audio API for sound effects.
*   **Backend:**
    *   **Language:** Python (v3.9+)
    *   **Framework:** Flask (v2.x+)
    *   **WSGI Server (Production):** Gunicorn
*   **Testing:**
    *   **Frontend:** Jest, React Testing Library
    *   **Backend:** pytest
*   **Package Managers:** npm (or yarn) for frontend, pip for backend.

## 3. Project Structure

```
kid-calculator-pink/
├── backend/                    # Flask Backend
│   ├── src/
│   │   ├── __init__.py
│   │   ├── app.py              # Flask app initialization, routes
│   │   └── config.py           # Configuration settings (if needed)
│   ├── tests/                  # Backend tests
│   │   └── test_app.py
│   ├── venv/                   # Python virtual environment (add to .gitignore)
│   ├── requirements.txt        # Backend dependencies
│   └── Dockerfile              # Optional: for containerization
│
├── frontend/                   # React Frontend
│   ├── public/
│   │   ├── index.html
│   │   └── assets/             # Static assets (images, sounds - pink themed)
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   │   ├── Button.js       # Calculator button component (number, operator, clear)
│   │   │   ├── Display.js      # Calculation display screen
│   │   │   └── Calculator.js   # Main calculator container component
│   │   ├── hooks/              # Custom hooks (e.g., useCalculatorLogic)
│   │   ├── styles/             # Global styles, variables (define pink theme here)
│   │   │   └── main.css
│   │   ├── App.js              # Main application component
│   │   ├── index.js            # Entry point
│   │   └── reportWebVitals.js
│   ├── tests/                  # Frontend tests
│   │   └── App.test.js
│   ├── node_modules/           # Frontend dependencies (add to .gitignore)
│   ├── package.json
│   ├── package-lock.json
│   └── README.md               # Frontend-specific README
│
├── .gitignore
├── README.md                   # Main project README
└── docker-compose.yml          # Optional: for running both services easily
```

## 4. Core Modules/Classes

### Frontend (React Components - `frontend/src/components/`)

1.  **`Calculator.js` (Container Component)**
    *   **Purpose:** Main container holding the calculator UI. Manages the overall calculator state.
    *   **State:** `displayValue` (string), `firstOperand` (number | null), `operator` (string | null), `waitingForSecondOperand` (boolean), `error` (string | null), `isMuted` (boolean).
    *   **Methods/Handlers:**
        *   `handleDigitClick(digit: string)`: Appends digit to `displayValue`.
        *   `handleOperatorClick(nextOperator: string)`: Stores `firstOperand` and `operator`, sets `waitingForSecondOperand`. Handles chained operations.
        *   `handleEqualsClick()`: Performs calculation using `firstOperand`, `operator`, and current `displayValue` (as second operand). Updates `displayValue` with result.
        *   `handleClearClick()`: Resets all state to initial values.
        *   `handleDecimalClick()`: Adds a decimal point if not already present.
        *   `handleToggleMute()`: Toggles the `isMuted` state.
        *   `playSound(soundType: string)`: Plays corresponding sound effect if not muted.
    *   **Renders:** `Display` component and multiple `Button` components.

2.  **`Display.js`**
    *   **Purpose:** Renders the calculator's display screen.
    *   **Props:** `value: string` (the content to display - numbers, results, or errors).
    *   **Styling:** Large, clear font. **Pink-themed** background/text color.

3.  **`Button.js`**
    *   **Purpose:** Renders individual calculator buttons (numbers 0-9, operators +, -, *, /, =, Clear).
    *   **Props:** `label: string` (text on the button), `onClick: () => void` (handler function), `type: 'number' | 'operator' | 'equals' | 'clear'` (for styling/logic), `isLarge?: boolean` (optional, e.g., for '0' or '=').
    *   **Styling:** Large, rounded buttons. **Predominantly pink and complementary colors**. Clear visual feedback on press (e.g., slight size/color change). Different styles for different button types (e.g., operators vs. numbers).

### Backend (Flask - `backend/src/app.py`)

1.  **Flask App Instance (`app`)**
    *   **Purpose:** The main Flask application object.
    *   **Configuration:** Set up to serve static files from the React build directory.

2.  **Routes:**
    *   **`@app.route('/', defaults={'path': ''})`**
    *   **`@app.route('/<path:path>')`**
        *   **Purpose:** Serves the `index.html` file from the React build folder for the root route and any other client-side routes, enabling React Router (if used later).
        *   **Logic:** Checks if a static file matching `path` exists in the static folder. If yes, serves it. Otherwise, serves `index.html`.
    *   **`@app.route('/api/calculate', methods=['POST'])` (Optional/Future)**
        *   **Purpose:** Handle calculation requests if moved to the backend.
        *   **Input:** JSON body like `{ "operand1": number, "operand2": number, "operator": string }`
        *   **Output:** JSON response like `{ "result": number }` or `{ "error": string }`
        *   **Logic:** Parses input, performs calculation, handles errors (like division by zero), returns result.

## 5. Data Structures

*   **Frontend State (React):** Managed within the `Calculator.js` component using `useState` or `useReducer`. Key state variables listed in section 4.
*   **API Payload (Optional - If backend calc):**
    *   Request (`POST /api/calculate`):
        ```json
        {
          "operand1": 10,
          "operand2": 5,
          "operator": "+"
        }
        ```
    *   Response (Success):
        ```json
        {
          "result": 15
        }
        ```
    *   Response (Error):
        ```json
        {
          "error": "Division by zero is not allowed."
        }
        ```

## 6. API Interaction

*   **Initial:** No API interaction required for core calculator functionality (client-side calculation). The Flask backend only serves static files.
*   **Optional/Future:** If calculations are moved to the backend:
    *   **API Used:** Internal Flask API created within the project.
    *   **Endpoint:** `POST /api/calculate`
    *   **Data Format:** JSON (as described in section 5).
    *   **Authentication:** None required for this simple API.

## 7. Error Handling Strategy

*   **Frontend (React):**
    *   **Invalid Operations (e.g., Division by Zero):** The client-side calculation logic will detect these. Display a user-friendly message (e.g., "Oops! Can't divide by zero!") in the `Display` component by updating the `error` state. Clear the error on the next valid input or clear action.
    *   **Input Errors (e.g., multiple decimals):** Logic within input handlers will prevent invalid states (e.g., ignore second decimal point press).
    *   **API Errors (If backend calc used):** Use `try...catch` blocks around `fetch` or `.catch()` with `axios`. Update the `error` state with a generic message like "Calculation error" or a specific message from the API response.
*   **Backend (Flask - If API used):**
    *   **Invalid Input:** Validate incoming data in the `/api/calculate` route. Return a `400 Bad Request` response with a JSON error message.
    *   **Calculation Errors (e.g., Division by Zero):** Catch specific Python exceptions (e.g., `ZeroDivisionError`). Return a `400 Bad Request` or `422 Unprocessable Entity` response with a JSON error message.
    *   **General Server Errors:** Use Flask's error handling mechanisms (`@app.errorhandler`) to catch unexpected errors and return a generic `500 Internal Server Error` response. Log errors for debugging.

## 8. Testing Strategy

*   **Frontend (React):**
    *   **Tools:** Jest, React Testing Library.
    *   **Unit Tests:** Test individual components (`Button`, `Display`) for correct rendering based on props. Test utility functions or custom hooks (e.g., calculation logic if extracted).
    *   **Integration Tests:** Test the `Calculator` component interactions. Simulate button clicks and verify that the display updates correctly, state changes as expected, and calculations produce the correct results. Test sequences of operations (e.g., `5 + 3 = 8`). Test error conditions (division by zero). Test clear functionality. Test mute functionality.
    *   **Focus Areas:** User input handling, calculation logic, state updates, display rendering, error message display, theme application (visual check or snapshot tests).
*   **Backend (Flask):**
    *   **Tools:** `pytest`.
    *   **Unit Tests:** Test any utility functions or calculation logic classes if separated from routes.
    *   **Integration Tests:** Test the Flask API endpoints (if implemented). Use `pytest` fixtures and Flask's test client to send mock requests to `/api/calculate` and assert the correctness of responses (results and error handling). Test the static file serving routes.
    *   **Focus Areas:** API request parsing, calculation logic (if backend), error handling (division by zero, invalid input), response formatting, static file serving.
```