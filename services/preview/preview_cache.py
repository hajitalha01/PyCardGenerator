"""Cache for rendered preview backgrounds.

Stores the rendered background image (template background +
static images) for each card side so that field-only value
changes can be composited without re-rendering the full
background.  Invalidation occurs only when the template
changes.
"""

from __future__ import annotations

from PIL import Image


class PreviewCache:
    """Caches rendered background images per template + side.

    Usage::

        cache = PreviewCache()

        # On template change
        cache.invalidate()

        # Before rendering a side, check the cache
        bg = cache.get_background(template_id, "front")
        if bg is None:
            bg = render_background(...)
            cache.set_background(template_id, "front", bg)
    """

    def __init__(self) -> None:
        """Initialise an empty cache."""
        self._bg_front: Image.Image | None = None
        self._bg_back: Image.Image | None = None
        self._template_id: int | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_background(
        self, template_id: int, side: str
    ) -> Image.Image | None:
        """Retrieve a cached background image.

        Args:
            template_id: The template's unique identifier.
            side: ``'front'`` or ``'back'``.

        Returns:
            The cached background image, or ``None`` if no cached
            entry exists for this template.
        """
        if template_id != self._template_id:
            return None
        return self._bg_front if side == "front" else self._bg_back

    def set_background(
        self, template_id: int, side: str, image: Image.Image
    ) -> None:
        """Store a background image in the cache.

        Args:
            template_id: The template's unique identifier.
            side: ``'front'`` or ``'back'``.
            image: The rendered background image.
        """
        self._template_id = template_id
        if side == "front":
            self._bg_front = image
        else:
            self._bg_back = image

    def invalidate(self) -> None:
        """Clear all cached entries (call on template change)."""
        self._bg_front = None
        self._bg_back = None
        self._template_id = None
