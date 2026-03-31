import io
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from services import file_manager

router = APIRouter(prefix="/api/v1", tags=["export"])


@router.get("/export/{session_id}/{format}")
async def export_data(session_id: str, format: str):
    try:
        file_manager.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    if format == "cleaned_csv":
        path = file_manager.cleaned_csv_path(session_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Cleaned data not found")
        return FileResponse(
            path,
            media_type="text/csv",
            filename=f"cleaned_{session_id}.csv",
        )

    if format == "tableau":
        tableau_zip = file_manager.session_dir(session_id) / "tableau_export.zip"
        if not tableau_zip.exists():
            raise HTTPException(
                status_code=404, detail="Tableau export not found"
            )
        return FileResponse(
            tableau_zip,
            media_type="application/zip",
            filename=f"tableau_{session_id}.zip",
        )

    if format == "charts":
        charts_dir = file_manager.charts_dir(session_id)
        png_files = list(charts_dir.glob("*.png"))
        if not png_files:
            raise HTTPException(status_code=404, detail="No charts found")

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for png in png_files:
                zf.write(png, png.name)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="charts_{session_id}.zip"'
            },
        )

    raise HTTPException(status_code=400, detail=f"Unknown format: {format}")
