import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from models.enums import SessionStatus
from models.schemas import ChartSpec, VisualizeRequest, VisualizeResponse
from services import file_manager
from services.profiler import profile_dataframe
from services.visualization.chart_selector import select_charts
from services.visualization.matplotlib_gen import generate_matplotlib
from services.visualization.vegalite_gen import generate_vegalite

router = APIRouter(prefix="/api/v1", tags=["visualize"])


@router.post("/visualize", response_model=VisualizeResponse)
async def visualize_data(request: VisualizeRequest):
    try:
        file_manager.get_session(request.session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    file_manager.update_session(
        request.session_id, status=SessionStatus.VISUALIZING
    )

    try:
        df = file_manager.load_cleaned_df(request.session_id)
        profile = profile_dataframe(df)
        recommendations = select_charts(profile, df)

        charts: list[ChartSpec] = []
        for rec in recommendations:
            chart_id = uuid.uuid4().hex[:8]

            vegalite_spec = None
            matplotlib_url = None

            if "vegalite" in request.formats:
                vegalite_spec = generate_vegalite(rec, df)

            if "matplotlib" in request.formats:
                charts_dir = file_manager.charts_dir(request.session_id)
                png_path = charts_dir / f"{chart_id}.png"
                generate_matplotlib(rec, df, str(png_path))
                matplotlib_url = (
                    f"/api/v1/matplotlib/{request.session_id}/{chart_id}.png"
                )

            charts.append(
                ChartSpec(
                    chart_id=chart_id,
                    chart_type=rec.chart_type,
                    title=rec.title,
                    columns_used=rec.columns,
                    vegalite_spec=vegalite_spec,
                    matplotlib_url=matplotlib_url,
                    description=rec.description,
                )
            )

        tableau_url = None
        if "tableau" in request.formats:
            from services.visualization.tableau_gen import generate_tableau_package

            tableau_path = generate_tableau_package(
                df, profile, recommendations, request.session_id
            )
            if tableau_path:
                tableau_url = (
                    f"/api/v1/export/{request.session_id}/tableau"
                )

        file_manager.update_session(
            request.session_id, status=SessionStatus.COMPLETE
        )

        return VisualizeResponse(
            session_id=request.session_id,
            charts=charts,
            tableau_download_url=tableau_url,
        )
    except Exception as e:
        file_manager.update_session(
            request.session_id, status=SessionStatus.ERROR, error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Visualization failed: {e}")


@router.get("/matplotlib/{session_id}/{filename}")
async def serve_chart(session_id: str, filename: str):
    charts_dir = file_manager.charts_dir(session_id)
    filepath = charts_dir / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(filepath, media_type="image/png")
