import os
import logging
from typing import Any, Dict, Tuple, Union

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    Response,
    abort
)

from .config import config

# Initialize Flask app
app = Flask(__name__, static_folder=config.STATIC_FOLDER)
app.config.from_object(config)

logger = logging.getLogger(__name__)

# --- Static File Serving & SPA Fallback ---

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path: str) -> Response:
    """
    Serves static files from the React build folder.
    Handles SPA routing by serving index.html for unknown paths.
    """
    static_folder_path = config.REACT_APP_BUILD_PATH

    if not static_folder_path.exists():
        logger.error(f"React build directory not found at {static_folder_path}")
        return jsonify({"error": "Server configuration error: Static assets not found."}), 500

    # If the path is empty or points to a directory, serve index.html
    if path == "" or path.endswith('/'):
        file_path = static_folder_path / "index.html"
    else:
        # Construct the full path to the requested file
        file_path = static_folder_path / path

    # Check if the requested path directly corresponds to an existing file
    if file_path.is_file():
        try:
            # Use send_from_directory for security (prevents path traversal)
            logger.debug(f"Serving static file: {file_path}")
            return send_from_directory(str(static_folder_path), path)
        except Exception as e:
            logger.error(f"Error sending file {file_path}: {e}")
            abort(500) # Let the generic 500 handler take over
    else:
        # If the specific file doesn't exist, assume it's a client-side route
        # and serve the main index.html file. React Router will handle the rest.
        index_path = static_folder_path / "index.html"
        if index_path.is_file():
            logger.debug(f"Path '{path}' not found, serving index.html for SPA routing.")
            return send_from_directory(str(static_folder_path), "index.html")
        else:
            # If index.html itself is missing, return a 404
            logger.warning(f"index.html not found in {static_folder_path}")
            abort(404) # Let the generic 404 handler take over


# --- API Routes ---

@app.route('/api/calculate', methods=['POST'])
def calculate() -> Tuple[Response, int]:
    """
    Handles calculation requests from the frontend (Optional/Future endpoint).
    Expects JSON: {"operand1": number, "operand2": number, "operator": string}
    Returns JSON: {"result": number} or {"error": string}
    """
    logger.info(f"Received request for /api/calculate from {request.remote_addr}")

    # 1. Check Content-Type
    if not request.is_json:
        logger.warning("Request Content-Type is not application/json")
        return jsonify({"error": "Invalid request format: Content-Type must be application/json"}), 415 # Unsupported Media Type

    # 2. Get JSON data
    data: Union[Dict[str, Any], None] = request.get_json()
    if data is None:
         logger.warning("Request body is empty or invalid JSON")
         return jsonify({"error": "Invalid request: Missing JSON body"}), 400

    # 3. Validate required fields
    required_fields = ["operand1", "operand2", "operator"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logger.warning(f"Missing fields in request: {missing_fields}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    operand1 = data.get("operand1")
    operand2 = data.get("operand2")
    operator = data.get("operator")

    # 4. Validate types and values
    errors: Dict[str, str] = {}
    if not isinstance(operand1, (int, float)):
        errors["operand1"] = "Must be a number."
    if not isinstance(operand2, (int, float)):
        errors["operand2"] = "Must be a number."
    if not isinstance(operator, str):
        errors["operator"] = "Must be a string."
    elif operator not in ['+', '-', '*', '/']:
        errors["operator"] = "Invalid operator. Must be one of +, -, *, /."

    if errors:
        logger.warning(f"Validation errors: {errors}")
        return jsonify({"error": "Validation failed", "details": errors}), 400

    # 5. Perform Calculation
    result: Union[int, float, None] = None
    try:
        op1_num = float(operand1) # Cast to float for consistent operations
        op2_num = float(operand2)

        if operator == '+':
            result = op1_num + op2_num
        elif operator == '-':
            result = op1_num - op2_num
        elif operator == '*':
            result = op1_num * op2_num
        elif operator == '/':
            if op2_num == 0:
                logger.warning("Division by zero attempted.")
                return jsonify({"error": "Division by zero is not allowed."}), 400
            result = op1_num / op2_num

        # Handle potential large numbers or precision issues if necessary
        # For now, standard float precision is used.

        logger.info(f"Calculation successful: {op1_num} {operator} {op2_num} = {result}")
        return jsonify({"result": result}), 200

    except ValueError:
        # Should be caught by earlier type checks, but as a safeguard
        logger.error("ValueError during calculation - likely invalid number format despite checks.")
        return jsonify({"error": "Internal error: Invalid numeric values provided."}), 400
    except Exception as e:
        logger.exception(f"Unexpected error during calculation: {e}") # Log full traceback
        return jsonify({"error": "An unexpected error occurred during calculation."}), 500


# --- Error Handlers ---

@app.errorhandler(404)
def not_found_error(error: Exception) -> Tuple[Response, int]:
    """Handles 404 Not Found errors."""
    logger.warning(f"404 Not Found: {request.path}")
    # Check if the request path looks like an API call
    if request.path.startswith('/api/'):
        return jsonify({"error": "API endpoint not found."}), 404
    else:
        # For non-API routes, it might be a typo or unhandled SPA route.
        # Let the main serve_static handle SPA fallback if possible,
        # otherwise return a generic 404 page or message.
        # Here we assume if it gets here, serve_static couldn't find index.html
        return jsonify({"error": "Resource not found."}), 404

@app.errorhandler(400)
def bad_request_error(error: Exception) -> Tuple[Response, int]:
    """Handles 400 Bad Request errors globally."""
    # error.description often contains the message from abort(400, description=...)
    # or from validation libraries. Default if not provided.
    message = getattr(error, 'description', "Bad request.")
    logger.warning(f"400 Bad Request: {message} (Path: {request.path})")
    # Check if the error response is already JSON (e.g., from our API route)
    if isinstance(message, dict):
         return jsonify(message), 400
    return jsonify({"error": message}), 400

@app.errorhandler(405)
def method_not_allowed_error(error: Exception) -> Tuple[Response, int]:
    """Handles 405 Method Not Allowed errors."""
    logger.warning(f"405 Method Not Allowed: {request.method} for {request.path}")
    return jsonify({"error": f"Method {request.method} not allowed for this endpoint."}), 405

@app.errorhandler(500)
def internal_server_error(error: Exception) -> Tuple[Response, int]:
    """Handles 500 Internal Server Error."""
    logger.exception(f"500 Internal Server Error: {error}") # Log the exception traceback
    return jsonify({"error": "An unexpected internal server error occurred."}), 500


# --- Main Entry Point (for development server) ---
# In production, use a WSGI server like Gunicorn:
# gunicorn --bind 0.0.0.0:5000 "src.app:app"

if __name__ == '__main__':
    # Use Flask's built-in server for development ONLY
    # Gunicorn (or similar) should be used in production
    logger.info("Starting Flask development server...")
    # Note: app.run() is blocking
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))