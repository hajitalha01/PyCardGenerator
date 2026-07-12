"""PDF generation service.

Assembles rendered card images into single-page or combined
PDF documents using ReportLab.
"""


class PDFService:
    """Generates PDF documents from rendered card images.

    Currently a skeleton. Full implementation will use ReportLab to
    produce front-only, back-only, and combined PDFs at print-ready
    resolution.
    """

    def __init__(self) -> None:
        """Initialise the PDF service."""
        self._page_size: tuple[float, float] = (85.6, 54.0)

    def create_front_pdf(self, image_path: str, output_path: str) -> str:
        """Create a PDF containing only the front card image.

        Args:
            image_path: Path to the rendered front image.
            output_path: Desired path for the output PDF.

        Returns:
            The filesystem path to the generated PDF.

        Raises:
            NotImplementedError: Method is not yet implemented.
        """
        raise NotImplementedError("Front PDF creation is not yet implemented.")

    def create_back_pdf(self, image_path: str, output_path: str) -> str:
        """Create a PDF containing only the back card image.

        Args:
            image_path: Path to the rendered back image.
            output_path: Desired path for the output PDF.

        Returns:
            The filesystem path to the generated PDF.

        Raises:
            NotImplementedError: Method is not yet implemented.
        """
        raise NotImplementedError("Back PDF creation is not yet implemented.")

    def create_combined_pdf(
        self, front_path: str, back_path: str, output_path: str
    ) -> str:
        """Create a PDF with the front card on page one and back on page two.

        Args:
            front_path: Path to the rendered front image.
            back_path: Path to the rendered back image.
            output_path: Desired path for the output PDF.

        Returns:
            The filesystem path to the generated PDF.

        Raises:
            NotImplementedError: Method is not yet implemented.
        """
        raise NotImplementedError(
            "Combined PDF creation is not yet implemented."
        )
