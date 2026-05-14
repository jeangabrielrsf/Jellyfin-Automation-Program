"""Custom exceptions."""


class ConfigurationError(Exception):
    """Raised when a required configuration value is missing from both DB and .env."""

    def __init__(self, key: str, message: str | None = None):
        self.key = key
        self.message = message or f"Missing required config: '{key}'. Set it via UI or .env"
        super().__init__(self.message)
