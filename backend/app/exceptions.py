"""Custom exceptions."""


class ConfigurationError(Exception):
    """Raised when a required configuration value is missing from both DB and .env."""

    def __init__(self, key: str, message: str | None = None):
        self.key = key
        self.message = message or f"Missing required config: '{key}'. Set it via UI or .env"
        super().__init__(self.message)


class StreamLimitError(Exception):
    """Raised when the maximum number of concurrent stream sessions is reached."""

    def __init__(self, max_sessions: int):
        self.max_sessions = max_sessions
        message = (
            f"Limite de {max_sessions} streams simultâneos atingido. "
            "Tente novamente mais tarde."
        )
        super().__init__(message)


class StreamTranscodeError(Exception):
    """Raised when ffmpeg fails to start or produce the HLS playlist."""

