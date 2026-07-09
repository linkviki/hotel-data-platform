from pathlib import Path
from uuid import uuid4
import fitz


def get_pdf_page_count(pdf_path: Path) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count


def validate_page_number(pdf_path: Path, page_number: int, page_count: int | None = None) -> None:
    total_pages = page_count if page_count is not None else get_pdf_page_count(pdf_path)

    if page_number < 0 or page_number >= total_pages:
        raise IndexError(
            f"Page number {page_number} out of range for {pdf_path.name}; "
            f"page_count={total_pages}"
        )


def pdf_page_to_png(pdf_path: Path, page_number: int = 0, zoom: int = 3) -> Path:
    output_dir = Path("output/pages")
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path = output_dir / f"{pdf_path.stem}_page_{page_number + 1}.png"
    if image_path.exists():
        image_path = output_dir / f"{pdf_path.stem}_{uuid4().hex[:8]}_page_{page_number + 1}.png"

    with fitz.open(pdf_path) as doc:
        validate_page_number(pdf_path, page_number, doc.page_count)
        page = doc[page_number]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(image_path)

    return image_path
