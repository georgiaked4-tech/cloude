from src.core.config import ExchangeConfig, NewsConfig
from src.data.news import NewsClient


def make_client(min_relevance: int = 1) -> NewsClient:
    news = NewsConfig(
        feeds=[], keywords=["bitcoin", "etf", "sec"], min_relevance=min_relevance
    )
    return NewsClient(news, ExchangeConfig())


def test_relevance_counts_configured_keywords_case_insensitively() -> None:
    client = make_client()
    assert client.relevance("SEC approves Bitcoin ETF", "") == 3
    assert client.relevance("Bitcoin rally", "") == 1
    assert client.relevance("Weather report", "nothing relevant") == 0


def test_threshold_filters_out_irrelevant_news() -> None:
    client = make_client(min_relevance=2)
    assert client.relevance("Bitcoin rally", "") < client.news.min_relevance
    assert client.relevance("SEC and Bitcoin", "") >= client.news.min_relevance
