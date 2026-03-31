from fastapi import APIRouter, HTTPException, UploadFile

from config import settings
from models.enums import SessionStatus
from models.schemas import UploadResponse
from services import file_manager
from services.profiler import profile_dataframe

router = APIRouter(prefix="/api/v1", tags=["upload"])

MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum is {settings.max_upload_size_mb}MB",
        )

    session_id = file_manager.create_session(file.filename)

    try:
        file_manager.save_upload(session_id, contents)
        df = file_manager.load_raw_df(session_id)
        profile = profile_dataframe(df)
        file_manager.update_session(session_id, status=SessionStatus.PROFILED)

        preview = df.head(10).fillna("").to_dict(orient="records")

        return UploadResponse(
            session_id=session_id,
            filename=file.filename,
            rows=len(df),
            columns=len(df.columns),
            profile=profile,
            preview=preview,
        )
    except Exception as e:
        file_manager.update_session(
            session_id, status=SessionStatus.ERROR, error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")
