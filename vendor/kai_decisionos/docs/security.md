# Security Controls

This document outlines the minimum security controls implemented in the DecisionOS gateway and how to verify them.

## 1. Authentication

- **Implementation**: A dummy OAuth2 bearer token system is in place for development. It is not secure for production. The token is the user's email.
- **Verification**: Send a request to a protected endpoint (e.g., `/decide`) without an `Authorization` header. The API must return a 401 Unauthorized error.

```bash
# This test in test_security.py verifies the behavior
pytest tests/test_security.py -k test_decide_endpoint_no_auth
```

## 2. Authorization (RBAC)

- **Implementation**: A Role-Based Access Control (RBAC) system is implemented as a FastAPI dependency. Routes are protected based on roles assigned to dummy users.
  - **Roles**: `user`, `admin`
  - **Endpoints**: 
    - `user` role required for `/decide`, `/consent`
    - `admin` role required for `/simulate`, `/explain`
- **Verification**: Attempt to access an admin-only endpoint (e.g., `/simulate`) with a user-level token (`user@example.com`). The API must return a 403 Forbidden error.

```bash
# This test in test_security.py verifies the behavior
pytest tests/test_security.py -k test_simulate_endpoint_wrong_role
```

## 3. Data Masking in Logs

- **Implementation**: A `MaskingFilter` is applied to the application's logger. It uses regular expressions to find and replace sensitive data patterns (e.g., emails, credit card numbers) in log messages before they are written.
- **Verification**: This is a development-level control. To verify, you can temporarily add a logging statement in an endpoint, call it with data that should be masked (e.g., an email in the payload), and check the console output to ensure the data is replaced with a placeholder like `[EMAIL]`.

## 4. Consent Management

- **Implementation**: A `/consent` endpoint is provided to simulate updating user consent preferences. It is authenticated but currently does not persist data.
- **Verification**: Call the `/consent` endpoint with a valid user token and a valid payload. The API should return a 200 OK status.

```bash
# This test in test_security.py verifies the behavior
pytest tests/test_security.py -k test_consent_endpoint_with_auth
```