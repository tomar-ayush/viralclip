from fastapi import APIRouter, HTTPException, Query, status

from app.trends.schema import TrendsResponse
from app.trends.service import trends_service

router = APIRouter(prefix="/trends", tags=["Trends"])


@router.get(
    "",
    response_model=TrendsResponse,
    summary="Fetch cached or live viral Google Trends",
)
async def get_viral_trends(
    geo: str = Query(
        default="US", description="Two letter ISO country code"
    ),
):
    try:
        return await trends_service.get_viral_trends(geo=geo.upper())
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trends: {e!s}",
        )
