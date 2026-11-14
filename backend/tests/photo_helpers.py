"""Build test images in memory."""

import io

from PIL import Image

GPS_IFD = 0x8825
ORIENTATION = 0x0112


def jpeg_with_gps(size: tuple[int, int] = (800, 600), orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, (200, 80, 40))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # camera make
    exif[0x0131] = "SecretCam 1.0"  # software
    exif.get_ifd(GPS_IFD).update({1: "S", 2: (17.0, 49.0, 45.12), 3: "E", 4: (31.0, 3.0, 7.92)})
    if orientation is not None:
        exif[ORIENTATION] = orientation
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def image_bytes(fmt: str, size: tuple[int, int] = (300, 200), mode: str = "RGB") -> bytes:
    colours = {"RGBA": (10, 120, 110, 128), "L": 120}
    image = Image.new(mode, size, colours.get(mode, (10, 120, 110)))
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def bomb_png() -> bytes:
    """A tiny file that decodes to ~49 megapixels (over the 40 MP limit)."""
    buffer = io.BytesIO()
    Image.new("1", (7000, 7000)).save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
