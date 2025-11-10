# Runbook

This document provides instructions for setting up, running, and testing the DecisionOS gateway.

## 1. Installation

Ensure you have Python 3.11+ and `pip` installed.

```bash
# Install project dependencies in editable mode
pip install -e .
```

## 2. Running the API Server

The API server is a FastAPI application. Use `uvicorn` to run it.

```bash
# Run the server with auto-reload for development
uvicorn kai_decisionos.apps.gateway.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## 3. Running Tests

The project uses `pytest` for testing.

```bash
# Run all tests
pytest
```

To run specific tests, such as the security verification tests:

```bash
# Run the security-specific tests
pytest tests/test_security.py
```

## 4. Authentication

The application uses a dummy authentication system for development. The token is the user's email.

- **User Token**: `user@example.com`
- **Admin Token**: `admin@example.com`

Provide the token as a Bearer token in the `Authorization` header:

```
Authorization: Bearer user@example.com
```

## 5. Troubleshooting

- **401 Unauthorized**: Ensure you are providing a valid Bearer token in the `Authorization` header.
- **403 Forbidden**: You are authenticated, but you don't have the required role (e.g., `admin`) for the endpoint.
- **Module Not Found**: Make sure you have installed the project in editable mode (`pip install -e .`).