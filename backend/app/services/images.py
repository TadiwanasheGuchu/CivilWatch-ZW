"""Validate and sanitise uploaded photographs.

Uploads are decoded and re-encoded from pixels, never stored as received.
That strips all metadata (EXIF, including GPS location, and XMP/ICC), drops
anything appended to or embedded in the file, and normalises every photo to
a compact JPEG suited to slow mobile connections.
"""

import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import AppError

ACCEPTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


class InvalidPhotoError(AppError):
    status_code = 422
    code = "invalid_photo"


@dataclass(frozen=True)
class ProcessedPhoto:
    display: bytes
    width: int
    height: int
    thumbnail: bytes


def _encode(image: Image.Image, max_px: int, quality: int) -> tuple[bytes, int, int]:
    copy = image.copy()
    copy.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    # No exif=/icc_profile= arguments: the output carries no metadata.
    copy.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue(), copy.width, copy.height


def process_photo(data: bytes, settings: Settings) -> ProcessedPhoto:
    Image.MAX_IMAGE_PIXELS = settings.photo_max_pixels
    try:
        with warnings.catch_warnings():
            # Treat "possible decompression bomb" warnings as errors too.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format not in ACCEPTED_FORMATS:
                    raise InvalidPhotoError("Upload a photo in JPEG, PNG or WebP format.")
                probe.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                # Respect the camera's rotation before the EXIF data is discarded.
                image = ImageOps.exif_transpose(image)
                if image.mode not in ("RGB", "L"):
                    rgba = image.convert("RGBA")
                    background = Image.new("RGB", rgba.size, (255, 255, 255))
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    image = background
                elif image.mode == "L":
                    image = image.convert("RGB")
    except InvalidPhotoError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise InvalidPhotoError("This photo is too large. Use a smaller photo.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise InvalidPhotoError("This file is not a photo we can read.") from exc

    display, width, height = _encode(
        image, settings.photo_display_max_px, settings.photo_jpeg_quality
    )
    thumbnail, _, _ = _encode(image, settings.photo_thumbnail_max_px, settings.photo_jpeg_quality)
    return ProcessedPhoto(display=display, width=width, height=height, thumbnail=thumbnail)
