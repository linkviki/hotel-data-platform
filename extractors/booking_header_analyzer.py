import json
from pathlib import Path

from services.pdf_service import pdf_page_to_png
from services.vision_service import extract_json_from_image


PDF_PATH = Path("samples/BOOKING STATS REPORT - JUNE 29 2026.pdf")
PROMPT_PATH = Path("prompts/booking_header_prompt.txt")
OUTPUT_PATH = Path("output/booking_header_analysis.json")


def analyze_booking_headers(pdf_path: Path) -> dict:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    # Header is on page 1
    image_path = pdf_page_to_png(pdf_path, page_number=0, zoom=4)

    result = extract_json_from_image(image_path, prompt)
    return result


if __name__ == "__main__":
    result = analyze_booking_headers(PDF_PATH)

    print(json.dumps(result, indent=4))

    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(f"\nSaved header analysis to: {OUTPUT_PATH}")