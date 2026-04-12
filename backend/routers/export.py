import io
import zipfile

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse

from services import file_manager

router = APIRouter(prefix="/api/v1", tags=["export"])


@router.get("/export/{session_id}/{format}")
async def export_data(
    session_id: str,
    format: str,
    title: str = Query("Data Analysis Report", description="Report title"),
):
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

    if format == "report_html":
        return _generate_html_report(session_id, title)

    if format == "report_pdf":
        return _generate_pdf_report(session_id, title)

    raise HTTPException(status_code=400, detail=f"Unknown format: {format}")


def _generate_html_report(session_id: str, title: str) -> HTMLResponse:
    from services.report_generator import build_report, render_html

    try:
        report = build_report(session_id, title=title)
        html = render_html(report)
        return HTMLResponse(
            content=html,
            headers={
                "Content-Disposition": f'attachment; filename="report_{session_id}.html"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")


def _generate_pdf_report(session_id: str, title: str) -> Response:
    from services.report_generator import build_report, render_html, render_pdf

    try:
        report = build_report(session_id, title=title)
        html = render_html(report)
        pdf_bytes = render_pdf(html, report=report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="report_{session_id}.pdf"'
            },
        )
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="PDF generation requires weasyprint. Install with: pip install weasyprint",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
