import logging
import re

# In a real app, this would be more comprehensive
PATTERNS_TO_MASK = {
    r"\b(\d{4}-?\d{4}-?\d{4}-?\d{4})\b": "[CARD_NUMBER]",
    r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b": "[EMAIL]",
}


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask(record.msg)
        if record.args:
            record.args = tuple(self.mask(arg) if isinstance(arg, str) else arg for arg in record.args)
        return True

    def mask(self, s: str) -> str:
        for pattern, replacement in PATTERNS_TO_MASK.items():
            s = re.sub(pattern, replacement, s)
        return s


def setup_logging():
    """Applies the masking filter to the root logger."""
    root_logger = logging.getLogger()
    # Ensure basicConfig is called, e.g., in your app's entry point before this.
    # FastAPI does this by default.
    for handler in root_logger.handlers:
        handler.addFilter(MaskingFilter())
