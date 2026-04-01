from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import R_AVAILABLE, settings
from models.enums import SessionStatus
from models.schemas import StatusResponse
from routers import clean, export, upload, visualize
from services import file_manager

app = FastAPI(
    title="Data Autopilot",
    description="Automated data cleaning and visualization",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(clean.router)
app.include_router(visualize.router)
app.include_router(export.router)


@app.get("/api/v1/status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str):
    try:
        session = file_manager.get_session(session_id)
    except KeyError:
        return StatusResponse(
            session_id=session_id,
            status=SessionStatus.ERROR,
            error="Session not found",
        )
    return StatusResponse(
        session_id=session_id,
        status=session["status"],
        error=session.get("error"),
    )


@app.get("/api/v1/capabilities")
async def get_capabilities():
    return {
        "r_available": R_AVAILABLE,
        "max_upload_size_mb": settings.max_upload_size_mb,
        "engines": ["python"] + (["r"] if R_AVAILABLE else []),
        "viz_formats": ["vegalite", "matplotlib", "tableau"],
        "export_formats": ["cleaned_csv", "charts", "tableau", "report_html", "report_pdf"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
