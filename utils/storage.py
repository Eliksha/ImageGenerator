# utils/storage.py
import os
from pathlib import Path

def save_uploaded_file(uploaded_file, category: str, filename_prefix: str) -> str:
    """
    Saves a Streamlit uploaded file object to disk.
    Args:
        uploaded_file: UploadedFile from Streamlit
        category: subfolder under storage/uploads (e.g., 'single_person')
        filename_prefix: prefix to use in saved filename
    Returns:
        The full path of saved file as string.
    """
    base_dir = Path("storage") / "uploads" / category
    base_dir.mkdir(parents=True, exist_ok=True)

    # Generate a unique filename
    ext = Path(uploaded_file.name).suffix or ".jpg"
    filename = f"{filename_prefix}_{int(os.times().system * 10000)}{ext}"
    save_path = base_dir / filename

    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(save_path)
