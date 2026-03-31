import shutil
import uuid
from pathlib import Path

import pandas as pd

from config import settings
from models.enums import SessionStatus


_sessions: dict[str, dict] = {}


def create_session(filename: str) -> str:
    session_id = uuid.uuid4().hex[:12]
    session_dir = settings.data_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    _sessions[session_id] = {
        "filename": filename,
        "status": SessionStatus.UPLOADED,
        "error": None,
    }
    return session_id


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        raise KeyError(f"Session {session_id} not found")
    return _sessions[session_id]


def update_session(session_id: str, **kwargs: object) -> None:
    session = get_session(session_id)
    session.update(kwargs)


def session_dir(session_id: str) -> Path:
    return settings.data_dir / session_id


def raw_csv_path(session_id: str) -> Path:
    return session_dir(session_id) / "raw.csv"


def cleaned_csv_path(session_id: str) -> Path:
    return session_dir(session_id) / "cleaned.csv"


def charts_dir(session_id: str) -> Path:
    d = session_dir(session_id) / "charts"
    d.mkdir(exist_ok=True)
    return d


def save_upload(session_id: str, contents: bytes) -> Path:
    path = raw_csv_path(session_id)
    path.write_bytes(contents)
    return path


def load_raw_df(session_id: str) -> pd.DataFrame:
    return pd.read_csv(raw_csv_path(session_id))


def load_cleaned_df(session_id: str) -> pd.DataFrame:
    return pd.read_csv(cleaned_csv_path(session_id))


def save_cleaned_df(session_id: str, df: pd.DataFrame) -> Path:
    path = cleaned_csv_path(session_id)
    df.to_csv(path, index=False)
    return path


def cleanup_session(session_id: str) -> None:
    d = session_dir(session_id)
    if d.exists():
        shutil.rmtree(d)
    _sessions.pop(session_id, None)
