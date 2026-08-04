from fastapi import APIRouter, Query, HTTPException, status
from app.schemas.trend import TrendsResponse
from app.services.trends_service import trends_service

router = APIRouter(prefix="/trends", tags=["Trends"])


@router.get("", response_model=TrendsResponse, summary="Fetch cached or live viral Google Trends")
async def get_viral_trends(geo: str = Query(default="US", description="Two letter ISO country code")):
    """
    Fetches real-time viral search topics from Google Trends RSS feed.
    Results are cached in Redis for 1 hour.
    """
    try:
        return await trends_service.get_viral_trends(geo=geo.upper())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trends: {str(e)}"
        )
