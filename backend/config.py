import subprocess
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    max_upload_size_mb: int = 50
    session_ttl_minutes: int = 30
    r_enabled: bool = True
    data_dir: Path = Path(__file__).parent / "data"

    model_config = {"env_prefix": "AUTOPILOT_"}


settings = Settings()


def check_r_available() -> bool:
    if not settings.r_enabled:
        return False
    try:
        result = subprocess.run(
            ["Rscript", "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


R_AVAILABLE = check_r_available()
