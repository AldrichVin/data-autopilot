from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import AIAnalysis, AIChartInsight
from services import file_manager

router = APIRouter(prefix="/api/v1", tags=["enrich"])


class EnrichRequest(BaseModel):
    session_id: str
    executive_summary: str = ""
    chart_insights: list[AIChartInsight] = []
    recommendations: str = ""


@router.post("/enrich")
async def enrich_with_ai(request: EnrichRequest):
    try:
        file_manager.get_session(request.session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    ai_analysis = AIAnalysis(
        executive_summary=request.executive_summary,
        chart_insights=request.chart_insights,
        recommendations=request.recommendations,
    )
    file_manager.update_session(request.session_id, ai_analysis=ai_analysis)
    return {"status": "ok", "session_id": request.session_id}
