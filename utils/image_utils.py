# utils/image_utils.py

from PIL import Image

def validate_image(file) -> bool:
    # Basic validation: check if file can be opened by PIL as an image
    try:
        Image.open(file)
        return True
    except Exception:
        return False

def resize_image(file, max_size=(512, 512)) -> Image.Image:
    # Resize image maintaining aspect ratio
    img = Image.open(file)
    img.thumbnail(max_size)
    return img
