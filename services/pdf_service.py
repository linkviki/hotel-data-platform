from pathlib import Path
import fitz


def pdf_page_to_png(pdf_path: Path, page_number: int = 0, zoom: int = 3) -> Path:
    output_dir = Path("output/pages")
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path = output_dir / f"{pdf_path.stem}_page_{page_number + 1}.png"

    with fitz.open(pdf_path) as doc:
        page = doc[page_number]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(image_path)

    return image_path