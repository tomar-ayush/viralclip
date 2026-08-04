from typing import List, Optional
from pydantic import BaseModel, Field


class TrendItem(BaseModel):
    title: str
    traffic: Optional[str] = None
    news_item_title: Optional[str] = None
    news_item_url: Optional[str] = None
    pub_date: Optional[str] = None


class TrendsResponse(BaseModel):
    source: str = "Google Trends RSS"
    items_count: int
    items: List[TrendItem]
