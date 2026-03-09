"""Wikipedia multilingual loader.

Fetches the summary and URL for a Wikipedia topic in the configured language.
Uses the `wikipedia` package which wraps the Wikipedia API.

Returns an empty dict on disambiguation or page-not-found errors so callers
can gracefully skip enrichment rather than crashing.
"""

from __future__ import annotations

import logging

import wikipedia

logger = logging.getLogger(__name__)


class WikiLoader:
    """Fetches Wikipedia article summaries in any supported language."""

    def __init__(self, language: str = "en") -> None:
        self.language = language

    def fetch(self, topic: str) -> dict:
        """Fetch Wikipedia summary for a topic.

        Args:
            topic: Search topic string (e.g. "Wheat", "stem borer").

        Returns:
            Dict with keys: title, summary, url.
            Empty dict if the page is ambiguous or not found.
        """
        wikipedia.set_lang(self.language)
        try:
            page = wikipedia.page(topic)
            return {
                "title": page.title,
                "summary": page.summary,
                "url": page.url,
            }
        except wikipedia.exceptions.DisambiguationError as exc:
            options = getattr(exc, "options", [])
            logger.debug("Wikipedia disambiguation for '%s': %s", topic, options[:3])
            return {}
        except wikipedia.exceptions.PageError:
            logger.debug("Wikipedia page not found: '%s'", topic)
            return {}
        except Exception as exc:
            logger.warning("Wikipedia fetch error for '%s': %s", topic, exc)
            return {}
