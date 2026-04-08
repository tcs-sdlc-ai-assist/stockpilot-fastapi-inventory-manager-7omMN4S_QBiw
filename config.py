import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY: str
    DEFAULT_ADMIN_USERNAME: str
    DEFAULT_ADMIN_PASSWORD: str
    DEFAULT_ADMIN_DISPLAY_NAME: str
    DATABASE_URL: str

    def __init__(self) -> None:
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "")
        self.DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
        self.DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin1234")
        self.DEFAULT_ADMIN_DISPLAY_NAME = os.environ.get("DEFAULT_ADMIN_DISPLAY_NAME", "Administrator")
        self.DATABASE_URL = os.environ.get(
            "DATABASE_URL",
            f"sqlite+aiosqlite:///{Path(__file__).resolve().parent / 'stockpilot.db'}",
        )

        if not self.SECRET_KEY:
            self.SECRET_KEY = "stockpilot-insecure-default-change-me"

        self._validate()

    def _validate(self) -> None:
        missing: list[str] = []
        required_fields = {
            "SECRET_KEY": self.SECRET_KEY,
            "DEFAULT_ADMIN_USERNAME": self.DEFAULT_ADMIN_USERNAME,
            "DEFAULT_ADMIN_PASSWORD": self.DEFAULT_ADMIN_PASSWORD,
            "DEFAULT_ADMIN_DISPLAY_NAME": self.DEFAULT_ADMIN_DISPLAY_NAME,
            "DATABASE_URL": self.DATABASE_URL,
        }
        for field_name, value in required_fields.items():
            if not value or not value.strip():
                missing.append(field_name)
        if missing:
            raise ValueError(
                f"Missing required configuration variables: {', '.join(missing)}"
            )


settings = Settings()