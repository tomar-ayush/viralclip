from pydantic import BaseModel, Field


class TrendItem(BaseModel):
    title: str
    traffic: str | None = None
    news_item_title: str | None = None
    news_item_url: str | None = None
    pub_date: str | None = None


class TrendsResponse(BaseModel):
    source: str = "Google Trends RSS"
    items_count: int
    items: list[TrendItem]
