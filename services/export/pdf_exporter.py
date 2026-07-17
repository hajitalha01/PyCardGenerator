"""PDF export for card images.

Uses ReportLab to produce single-page (front-only or back-only)
and two-page (combined front + back) PDF documents at the ID-1
card size (85.6 x 54.0 mm / CR-80).
"""

from __future__ import annotations

from config.constants import CARD_HEIGHT_MM, CARD_WIDTH_MM


class PDFExporter:
    """Creates print-ready PDFs from rendered card images.

    Typical usage::

        exporter = PDFExporter()
        pdf_path = exporter.create_combined_pdf(
            "front.png", "back.png", "output.pdf"
        )
    """

    def __init__(self, dpi: int = 600) -> None:
        """Initialise with the ID-1 card page size.

        Args:
            dpi: Output resolution for embedded images.
        """
        self._width_mm: float = CARD_WIDTH_MM
        self._height_mm: float = CARD_HEIGHT_MM
        self._dpi: int = dpi

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_front_pdf(self, image_path: str, output_path: str) -> str:
        """Create a single-page PDF with the front card image.

        Args:
            image_path: Path to the rendered front card image (PNG/JPEG).
            output_path: Desired path for the output PDF.

        Returns:
            The ``output_path`` the PDF was saved to.
        """
        from reportlab.lib.units import mm  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415

        c: canvas.Canvas = canvas.Canvas(
            output_path,
            pagesize=(self._width_mm * mm, self._height_mm * mm),
        )
        c.drawImage(
            image_path,
            0,
            0,
            width=self._width_mm * mm,
            height=self._height_mm * mm,
        )
        c.save()
        return output_path

    def create_back_pdf(self, image_path: str, output_path: str) -> str:
        """Create a single-page PDF with the back card image.

        Args:
            image_path: Path to the rendered back card image (PNG/JPEG).
            output_path: Desired path for the output PDF.

        Returns:
            The ``output_path`` the PDF was saved to.
        """
        from reportlab.lib.units import mm  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415

        c: canvas.Canvas = canvas.Canvas(
            output_path,
            pagesize=(self._width_mm * mm, self._height_mm * mm),
        )
        c.drawImage(
            image_path,
            0,
            0,
            width=self._width_mm * mm,
            height=self._height_mm * mm,
        )
        c.save()
        return output_path

    def create_combined_pdf(
        self, front_path: str, back_path: str, output_path: str
    ) -> str:
        """Create a two-page PDF with front on page one and back on page two.

        Args:
            front_path: Path to the rendered front card image.
            back_path: Path to the rendered back card image.
            output_path: Desired path for the output PDF.

        Returns:
            The ``output_path`` the PDF was saved to.
        """
        from reportlab.lib.units import mm  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415

        c: canvas.Canvas = canvas.Canvas(
            output_path,
            pagesize=(self._width_mm * mm, self._height_mm * mm),
        )

        # Page 1 — front
        c.drawImage(
            front_path,
            0,
            0,
            width=self._width_mm * mm,
            height=self._height_mm * mm,
        )
        c.showPage()

        # Page 2 — back
        c.drawImage(
            back_path,
            0,
            0,
            width=self._width_mm * mm,
            height=self._height_mm * mm,
        )
        c.showPage()

        c.save()
        return output_path
