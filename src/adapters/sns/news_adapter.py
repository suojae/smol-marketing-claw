"""News adapter — re-exports NewsClient."""

from src.news_client import NewsClient, NewsItem, NewsSearchResult

__all__ = ["NewsClient", "NewsItem", "NewsSearchResult"]
