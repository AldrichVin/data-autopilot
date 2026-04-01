from fastapi import APIRouter, HTTPException

from config import R_AVAILABLE
from models.enums import Engine, SessionStatus
from models.schemas import CleanRequest, CleanResponse
from services import file_manager
from services.cleaning.python_engine import PythonCleaningEngine
from services.cleaning.r_engine import RCleaningEngine

router = APIRouter(prefix="/api/v1", tags=["clean"])


@router.post("/clean", response_model=CleanResponse)
async def clean_data(request: CleanRequest):
    try:
        file_manager.get_session(request.session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.engine == Engine.R and not R_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="R engine is not available on this server",
        )

    file_manager.update_session(request.session_id, status=SessionStatus.CLEANING)

    try:
        df = file_manager.load_raw_df(request.session_id)

        if request.engine == Engine.R:
            engine = RCleaningEngine()
        else:
            engine = PythonCleaningEngine()

        cleaned_df, report = engine.clean(df, request.options)
        file_manager.save_cleaned_df(request.session_id, cleaned_df)
        file_manager.update_session(
            request.session_id,
            status=SessionStatus.CLEANED,
            cleaning_report=report,
        )

        preview = cleaned_df.head(10).fillna("").to_dict(orient="records")

        return CleanResponse(
            session_id=request.session_id,
            engine_used=request.engine.value,
            cleaning_report=report,
            cleaned_preview=preview,
        )
    except Exception as e:
        file_manager.update_session(
            request.session_id, status=SessionStatus.ERROR, error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {e}")
