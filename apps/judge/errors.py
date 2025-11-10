from __future__ import annotations

class JudgeError(Exception):
    """Base class for judge-related errors."""


class JudgeTimeout(JudgeError):
    pass


class JudgeBadSignature(JudgeError):
    pass


class JudgeHTTPError(JudgeError):
    def __init__(self, status_code: int, message: str | None = None):
        self.status_code = status_code
        super().__init__(message or f"HTTP error {status_code}")
