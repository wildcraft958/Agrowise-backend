"""Tests for WikiLoader — rag/wiki_loader.py."""

from unittest.mock import MagicMock, patch

import pytest

from agromind.rag.wiki_loader import WikiLoader


class TestWikiLoaderInit:
    def test_default_language_is_english(self):
        loader = WikiLoader()
        assert loader.language == "en"

    def test_custom_language(self):
        loader = WikiLoader(language="hi")
        assert loader.language == "hi"


class TestWikiLoaderFetch:
    @pytest.fixture
    def loader(self):
        return WikiLoader(language="en")

    def test_fetch_returns_dict(self, loader):
        mock_page = MagicMock()
        mock_page.summary = "Wheat is a cereal grain."
        mock_page.title = "Wheat"
        mock_page.url = "https://en.wikipedia.org/wiki/Wheat"

        with patch("agromind.rag.wiki_loader.wikipedia") as mock_wiki:
            mock_wiki.page.return_value = mock_page
            mock_wiki.exceptions.DisambiguationError = Exception
            mock_wiki.exceptions.PageError = Exception
            result = loader.fetch("Wheat")

        assert isinstance(result, dict)
        assert "title" in result
        assert "summary" in result
        assert "url" in result

    def test_fetch_content_matches_mock(self, loader):
        mock_page = MagicMock()
        mock_page.summary = "Wheat is a cereal grain."
        mock_page.title = "Wheat"
        mock_page.url = "https://en.wikipedia.org/wiki/Wheat"

        with patch("agromind.rag.wiki_loader.wikipedia") as mock_wiki:
            mock_wiki.page.return_value = mock_page
            mock_wiki.exceptions.DisambiguationError = Exception
            mock_wiki.exceptions.PageError = Exception
            result = loader.fetch("Wheat")

        assert result["title"] == "Wheat"
        assert "cereal" in result["summary"]

    def test_fetch_disambiguation_returns_empty(self, loader):
        with patch("agromind.rag.wiki_loader.wikipedia") as mock_wiki:
            mock_wiki.exceptions.DisambiguationError = ValueError
            mock_wiki.exceptions.PageError = LookupError
            mock_wiki.page.side_effect = ValueError("Disambiguation")
            result = loader.fetch("Mercury")

        assert result == {}

    def test_fetch_page_not_found_returns_empty(self, loader):
        with patch("agromind.rag.wiki_loader.wikipedia") as mock_wiki:
            mock_wiki.exceptions.DisambiguationError = ValueError
            mock_wiki.exceptions.PageError = LookupError
            mock_wiki.page.side_effect = LookupError("Not found")
            result = loader.fetch("XYZNonExistentPage12345")

        assert result == {}

    def test_fetch_sets_language(self):
        loader_hi = WikiLoader(language="hi")
        mock_page = MagicMock()
        mock_page.summary = "गेहूँ एक अनाज है।"
        mock_page.title = "गेहूँ"
        mock_page.url = "https://hi.wikipedia.org/wiki/गेहूँ"

        with patch("agromind.rag.wiki_loader.wikipedia") as mock_wiki:
            mock_wiki.exceptions.DisambiguationError = Exception
            mock_wiki.exceptions.PageError = Exception
            mock_wiki.page.return_value = mock_page
            result = loader_hi.fetch("गेहूँ")

        # language must be set before fetching
        mock_wiki.set_lang.assert_called_with("hi")
        assert result["title"] == "गेहूँ"
