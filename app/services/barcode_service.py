# app/services/barcode_service.py

import base64
from io import BytesIO
from PIL import Image
from pyzbar.pyzbar import decode


def decode_base64_image(data_url: str) -> Image.Image:
    """
    Given a data URL (e.g. "data:image/png;base64,...."), return a PIL Image.
    """
    # Split off the header (e.g. "data:image/png;base64,")
    try:
        header, encoded = data_url.split(",", 1)
    except ValueError:
        raise ValueError("Invalid data URI format for barcode image")

    image_data = base64.b64decode(encoded)
    return Image.open(BytesIO(image_data))


def extract_barcode_text_from_pil_image(pil_img: Image.Image) -> str | None:
    """
    Run pyzbar.decode on the given PIL image. If a barcode is found,
    return its text (as a string). Otherwise return None.
    """
    barcodes = decode(pil_img)
    if not barcodes:
        return None

    # If multiple barcodes are present, just return the first one’s data
    barcode_bytes = barcodes[0].data
    try:
        return barcode_bytes.decode("utf-8")
    except Exception:
        # In case it isn’t UTF-8 encoded, decode as latin‐1 or raw
        return barcode_bytes.decode("latin1", errors="ignore")


def decode_dataurl_to_barcode_text(data_url: str) -> str | None:
    """
    Convenience wrapper: take a data URL, convert to PIL, then decode.
    Returns the decoded text if successful, or None if no barcode was found.
    """
    try:
        pil_img = decode_base64_image(data_url)
    except Exception as e:
        raise ValueError(f"Unable to decode data URL into image: {e}")

    return extract_barcode_text_from_pil_image(pil_img)
