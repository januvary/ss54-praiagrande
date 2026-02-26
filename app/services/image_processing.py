"""
Image Processing Service

Centralized image operations for validation, normalization, and conversion.

Architecture:
- ImageValidator: Validates image format, dimensions, and quality
- ImageNormalizer: Handles mode conversion, transparency, and DPI preservation
- ImageConverter: Converts normalized images to PDF via img2pdf
- MetadataStripper: Removes EXIF/GPS metadata for privacy

Module-level aliases are provided for direct function access:
- validate_image = ImageValidator.validate
- normalize_image = ImageNormalizer.normalize
- convert_to_pdf = ImageConverter.convert_to_pdf
- strip_metadata = MetadataStripper.strip_metadata
"""

import gc
import io
import logging
from typing import Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """Container for image metadata."""

    format: str
    mode: str
    size: tuple[int, int]
    dpi: Optional[tuple[int, int]]
    has_transparency: bool


class ImageValidationError(Exception):
    """Raised when image validation fails."""

    pass


class ImageConversionError(Exception):
    """Raised when image conversion fails."""

    pass


class ImageValidator:
    """
    Validates image files before processing.

    Checks:
    - File format (JPEG, PNG)
    - Image is not corrupted
    - Dimensions are within acceptable range
    """

    MIN_DIMENSION = 10  # pixels
    MAX_DIMENSION = 10000  # pixels
    ALLOWED_FORMATS = {"JPEG", "PNG"}

    @staticmethod
    def _validate_image(img) -> None:
        """
        Validate image format and dimensions.

        Args:
            img: PIL Image object

        Raises:
            ImageValidationError: If format or dimensions are invalid
        """
        if img.format not in ImageValidator.ALLOWED_FORMATS:
            raise ImageValidationError(
                f"Formato não suportado: {img.format}. Use: JPEG ou PNG"
            )

        width, height = img.size
        if (
            width < ImageValidator.MIN_DIMENSION
            or height < ImageValidator.MIN_DIMENSION
        ):
            raise ImageValidationError(
                f"Imagem muito pequena: {width}x{height}px. "
                f"Mínimo: {ImageValidator.MIN_DIMENSION}px"
            )

        if (
            width > ImageValidator.MAX_DIMENSION
            or height > ImageValidator.MAX_DIMENSION
        ):
            raise ImageValidationError(
                f"Imagem muito grande: {width}x{height}px. "
                f"Máximo: {ImageValidator.MAX_DIMENSION}px"
            )

    @staticmethod
    def _extract_metadata(img):
        """
        Extract DPI and transparency information from image.

        Args:
            img: PIL Image object

        Returns:
            Tuple of (dpi tuple or None, has_transparency bool)
        """
        dpi = img.info.get("dpi")
        if dpi and isinstance(dpi, tuple):
            dpi_tuple = tuple(int(d) for d in dpi)
            dpi = (dpi_tuple[0], dpi_tuple[1]) if len(dpi_tuple) >= 2 else None

        has_transparency = (
            img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        )

        return dpi, has_transparency

    @staticmethod
    def validate(image_bytes: bytes) -> ImageInfo:
        """
        Validate image and return metadata.

        Args:
            image_bytes: Raw image file bytes

        Returns:
            ImageInfo object with metadata

        Raises:
            ImageValidationError: If validation fails
        """
        try:
            from PIL import Image
        except ImportError as e:
            logger.error(f"PIL not available: {e}")
            raise ImageValidationError(
                "Biblioteca de processamento de imagem não disponível"
            )

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                ImageValidator._validate_image(img)
                dpi, has_transparency = ImageValidator._extract_metadata(img)

                width, height = img.size
                if img.format is None:
                    raise ImageValidationError(
                        "Image format should be set after validation"
                    )
                logger.info(
                    f"Image validated: {img.format} {img.mode} {width}x{height} "
                    f"DPI:{dpi} alpha:{has_transparency}"
                )

                return ImageInfo(
                    format=img.format,
                    mode=img.mode,
                    size=img.size,
                    dpi=dpi,
                    has_transparency=has_transparency,
                )

        except ImageValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating image: {e}")
            raise ImageValidationError(f"Imagem corrompida ou inválida: {e}")


class ImageNormalizer:
    """
    Normalizes images to a consistent format for PDF conversion.

    Handles:
    - Mode conversion (RGBA, P, LA, L, etc. → RGB)
    - Transparency handling (white background)
    - DPI preservation
    """

    @staticmethod
    def normalize(image_bytes: bytes, image_info: ImageInfo) -> bytes:
        """
        Normalize image to RGB format with transparency handled.

        Args:
            image_bytes: Raw image file bytes
            image_info: Image metadata from validator

        Returns:
            Normalized image bytes in PNG format (RGB mode)

        Raises:
            ImageConversionError: If normalization fails
        """
        try:
            from PIL import Image
        except ImportError as e:
            logger.error(f"PIL not available: {e}")
            raise ImageConversionError(
                "Biblioteca de processamento de imagem não disponível"
            )

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    logger.info(f"Converting image mode from {img.mode} to RGB")
                    img_rgb = ImageNormalizer._convert_to_rgb(img)
                    img = img_rgb

                # Save as PNG (lossless, preserves quality)
                output = io.BytesIO()
                img.save(output, format="PNG")
                output.seek(0)

                logger.info("Image normalized to RGB/PNG")
                return output.getvalue()

        except ImageConversionError:
            raise
        except Exception as e:
            logger.error(f"Error normalizing image: {e}")
            raise ImageConversionError(f"Falha ao normalizar imagem: {e}")

    @staticmethod
    def _convert_to_rgb(img) -> Any:
        """
        Convert PIL Image to RGB mode, handling transparency.

        Handles all modes: RGBA, LA, PA, P, L, CMYK, YCbCr, LAB, HSV, etc.

        Args:
            img: PIL Image object

        Returns:
            New PIL Image in RGB mode
        """
        from PIL import Image

        # Modes that need transparency compositing
        if img.mode in ("RGBA", "LA", "PA", "P"):
            # Convert to RGBA first (handles all palette modes)
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Composite on white background
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1])  # Alpha channel as mask
            return rgb_img

        # Direct conversion for other modes
        return img.convert("RGB")


class ImageConverter:
    """
    Converts normalized RGB images to PDF using img2pdf.

    Uses lossless conversion to preserve image quality.
    """

    @staticmethod
    def convert_to_pdf(
        image_bytes: bytes, dpi: Optional[tuple[int, int]] = None
    ) -> bytes:
        """
        Convert RGB image (PNG format) to PDF.

        Args:
            image_bytes: Normalized image bytes (RGB mode, PNG format)
            dpi: DPI tuple (x, y) for PDF output. Defaults to (150, 150)

        Returns:
            PDF file bytes

        Raises:
            ImageConversionError: If conversion fails
        """
        # Default DPI if not provided
        if dpi is None:
            dpi = (150, 150)

        # Try img2pdf first (lossless, better quality)
        try:
            import img2pdf  # type: ignore
        except ImportError as e:
            logger.warning(f"img2pdf not available: {e}, using PIL fallback")
            return ImageConverter._convert_with_pil(image_bytes, dpi)

        try:
            # Convert to PDF using img2pdf (lossless)
            pdf_bytes = img2pdf.convert(image_bytes, dpi=dpi)
            if pdf_bytes is None:
                logger.warning("img2pdf returned None, trying PIL fallback")
                return ImageConverter._convert_with_pil(image_bytes, dpi)
            logger.info(
                f"Successfully converted image to PDF with img2pdf (DPI: {dpi})"
            )
            return pdf_bytes

        except Exception as e:
            logger.warning(f"img2pdf conversion failed ({e}), trying PIL fallback")
            # Fallback to PIL PDF generation
            return ImageConverter._convert_with_pil(image_bytes, dpi)

    @staticmethod
    def _convert_with_pil(image_bytes: bytes, dpi: tuple[int, int]) -> bytes:
        """
        Fallback PDF conversion using PIL when img2pdf fails.

        Args:
            image_bytes: Normalized image bytes (RGB mode, PNG format)
            dpi: DPI tuple (x, y) for PDF output

        Returns:
            PDF file bytes

        Raises:
            ImageConversionError: If all conversion methods fail
        """
        from PIL import Image
        import io

        try:
            img = Image.open(io.BytesIO(image_bytes))
            output = io.BytesIO()

            # Save as PDF using PIL
            # PIL expects DPI as a single value or tuple (x_dpi, y_dpi)
            img.save(output, format="PDF", resolution=dpi[0])  # Use x_dpi
            output.seek(0)

            logger.info("Successfully converted image to PDF using PIL fallback")
            return output.getvalue()

        except Exception as e:
            logger.error(f"PIL PDF conversion also failed: {e}")
            raise ImageConversionError(
                f"All PDF conversion methods failed. "
                f"PIL error: {e}. "
                f"Try converting the image to PDF manually before uploading."
            )


class MetadataStripper:
    """
    Removes EXIF and other metadata from images for privacy.

    Removes:
    - EXIF data (camera settings, timestamps)
    - GPS coordinates
    - Camera make/model
    - Software information
    - XMP data
    """

    @staticmethod
    def strip_metadata(image_bytes: bytes, mime_type: str) -> bytes:
        """
        Strip metadata from image.

        Args:
            image_bytes: Raw image file bytes
            mime_type: MIME type (image/jpeg or image/png)

        Returns:
            Cleaned image bytes with metadata removed, or original bytes on failure
        """
        try:
            from PIL import Image
        except ImportError:
            logger.warning("PIL not available, skipping metadata stripping")
            return image_bytes

        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Get image mode and size
            mode = img.mode
            size = img.size

            # Create clean copy without metadata
            img_clean = Image.new(mode, size)

            # Handle different modes for clean copy
            if mode in ("P", "PA"):
                # Palette mode - convert to RGB/RGBA
                if "A" in mode:
                    img_clean = img_clean.convert("RGBA")
                else:
                    img_clean = img_clean.convert("RGB")
                img_clean.paste(img)
            elif mode == "LA":
                # Grayscale with alpha
                img_clean.paste(img)
            elif mode == "L":
                # Grayscale
                img_clean.paste(img)
            else:
                # RGB, RGBA, etc.
                data = list(img.get_flattened_data())  # Pillow 14+ API
                img_clean.putdata(data)  # type: ignore[arg-type]

            # Save to bytes
            output = io.BytesIO()
            format_map = {
                "image/jpeg": "JPEG",
                "image/png": "PNG",
            }
            save_format = format_map.get(mime_type)

            if save_format is None:
                logger.warning(f"Unsupported image MIME type: {mime_type}")
                return image_bytes

            # JPEG-specific options for quality
            if save_format == "JPEG":
                img_clean.save(output, format=save_format, quality=95)
            else:
                img_clean.save(output, format=save_format)

            logger.info(f"Stripped metadata from {mime_type} image")
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Metadata stripping failed, using original image: {e}")
            return image_bytes


def convert_image_to_pdf(image_bytes: bytes) -> bytes:
    """
    Complete image to PDF conversion pipeline.

    This is the main entry point that orchestrates the full conversion process:
    1. Validate image format and dimensions
    2. Strip metadata for privacy
    3. Normalize to RGB format
    4. Convert to PDF

    Args:
        image_bytes: Raw image file bytes (JPEG or PNG)

    Returns:
        PDF file bytes

    Raises:
        ImageValidationError: If image is invalid
        ImageConversionError: If conversion fails
    """
    image_info = ImageValidator.validate(image_bytes)
    stripped_bytes = MetadataStripper.strip_metadata(
        image_bytes, f"image/{image_info.format.lower()}"
    )
    normalized_bytes = ImageNormalizer.normalize(stripped_bytes, image_info)
    pdf_bytes = ImageConverter.convert_to_pdf(normalized_bytes, image_info.dpi)

    gc.collect()

    return pdf_bytes


validate_image = ImageValidator.validate
normalize_image = ImageNormalizer.normalize
convert_to_pdf = ImageConverter.convert_to_pdf
strip_metadata = MetadataStripper.strip_metadata
