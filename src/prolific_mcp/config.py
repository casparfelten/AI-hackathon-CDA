"""Configuration management for Prolific MCP server."""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration for Prolific API access."""

    def __init__(self):
        """Initialize configuration and validate required settings."""
        self.api_key: Optional[str] = os.getenv("PROLIFIC_API_KEY")
        self.base_url: str = os.getenv(
            "PROLIFIC_API_BASE_URL", "https://api.prolific.com/api/v1"
        )
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")

    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.api_key:
            raise ValueError(
                "PROLIFIC_API_KEY environment variable is required. "
                "Set it in your .env file or environment."
            )
    
    def validate_gemini(self) -> None:
        """Validate that Gemini API key is present."""
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Set it in your .env file or environment."
            )

    def get_auth_header(self) -> dict[str, str]:
        """Get authorization header for API requests."""
        self.validate()
        return {"Authorization": f"Token {self.api_key}"}


# Global config instance
config = Config()

