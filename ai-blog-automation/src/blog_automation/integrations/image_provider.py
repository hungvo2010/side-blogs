"""Polymorphic image search — Unsplash, Pexels, Pixabay.

Switch via IMAGE_PROVIDER env var (unsplash, pexels, pixabay).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ImageResult:
    url: str
    thumbnail: str = ""
    author: str = ""
    source: str = ""  # unsplash / pexels / pixabay
    width: int = 0
    height: int = 0


# ═════════════════════════════════════════════════════════════════════════
# Abstract base
# ═════════════════════════════════════════════════════════════════════════


class ImageProvider(ABC):
    """Polymorphic interface for image search providers."""

    name: str = "base"

    @abstractmethod
    def search(self, query: str, count: int = 5) -> list[ImageResult]:
        """Search for images by keyword."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API key is set."""


# ═════════════════════════════════════════════════════════════════════════
# Unsplash (50 req/hour free)
# ═════════════════════════════════════════════════════════════════════════


class UnsplashProvider(ImageProvider):
    name = "unsplash"
    _base = "https://api.unsplash.com"

    def __init__(self, access_key: str = ""):
        import os

        self.key = access_key or os.getenv("UNSPLASH_ACCESS_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.key)

    def search(self, query: str, count: int = 5) -> list[ImageResult]:
        if not self.key:
            logger.warning("Unsplash not configured")
            return []

        r = requests.get(
            f"{self._base}/search/photos",
            params={"query": query, "per_page": min(count, 30)},
            headers={"Authorization": f"Client-ID {self.key}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for img in data.get("results", []):
            results.append(
                ImageResult(
                    url=img["urls"]["regular"],
                    thumbnail=img["urls"]["thumb"],
                    author=img["user"]["name"],
                    source="unsplash",
                    width=img["width"],
                    height=img["height"],
                )
            )
        return results


# ═════════════════════════════════════════════════════════════════════════
# Pexels (200 req/hour free)
# ═════════════════════════════════════════════════════════════════════════


class PexelsProvider(ImageProvider):
    name = "pexels"
    _base = "https://api.pexels.com/v1"

    def __init__(self, api_key: str = ""):
        import os

        self.key = api_key or os.getenv("PEXELS_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.key)

    def search(self, query: str, count: int = 5) -> list[ImageResult]:
        if not self.key:
            logger.warning("Pexels not configured")
            return []

        r = requests.get(
            f"{self._base}/search",
            params={"query": query, "per_page": min(count, 80)},
            headers={"Authorization": self.key},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for img in data.get("photos", []):
            results.append(
                ImageResult(
                    url=img["src"]["large"],
                    thumbnail=img["src"]["small"],
                    author=img["photographer"],
                    source="pexels",
                    width=img["width"],
                    height=img["height"],
                )
            )
        return results


# ═════════════════════════════════════════════════════════════════════════
# Pixabay (free, API key required)
# ═════════════════════════════════════════════════════════════════════════


class PixabayProvider(ImageProvider):
    name = "pixabay"
    _base = "https://pixabay.com/api"

    def __init__(self, api_key: str = ""):
        import os

        self.key = api_key or os.getenv("PIXABAY_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.key)

    def search(self, query: str, count: int = 5) -> list[ImageResult]:
        if not self.key:
            logger.warning("Pixabay not configured")
            return []

        r = requests.get(
            self._base,
            params={
                "key": self.key,
                "q": query,
                "per_page": min(count, 200),
                "image_type": "photo",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for img in data.get("hits", []):
            results.append(
                ImageResult(
                    url=img["largeImageURL"],
                    thumbnail=img["previewURL"],
                    author=img["user"],
                    source="pixabay",
                    width=img["imageWidth"],
                    height=img["imageHeight"],
                )
            )
        return results


# ═════════════════════════════════════════════════════════════════════════
# Factory
# ═════════════════════════════════════════════════════════════════════════

_providers: dict[str, type[ImageProvider]] = {
    "unsplash": UnsplashProvider,
    "pexels": PexelsProvider,
    "pixabay": PixabayProvider,
}


def get_image_provider(name: str | None = None) -> ImageProvider:
    """Return configured image provider.

    Args:
        name: One of unsplash/pexels/pixabay, or None to read
              IMAGE_PROVIDER env var (default: pexels).

    Returns:
        ImageProvider instance.
    """
    import os

    provider_name = name or os.getenv("IMAGE_PROVIDER", "pexels")
    cls = _providers.get(provider_name, PexelsProvider)
    instance = cls()

    if not instance.is_configured():
        logger.warning(
            f"Image provider '{provider_name}' not configured. "
            f"Set {instance.name.upper()}_API_KEY or UNSPLASH_ACCESS_KEY."
        )

    return instance
