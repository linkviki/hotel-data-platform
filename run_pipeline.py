from __future__ import annotations

import sys
from pathlib import Path

from main import process_file
from services.gmail_service import download_pdf_attachments
from services.report_detector import detect_report_type


def run_pipeline() -> int:
    try:
        downloaded_paths = download_pdf_attachments()
    except Exception as exc:
        print(f"Failed to download Gmail attachments: {exc}", file=sys.stderr)
        return 1

    total_downloaded = len(downloaded_paths)
    processed_successfully = 0
    failed = 0
    skipped_unknown = 0

    for downloaded_path in downloaded_paths:
        pdf_path = Path(downloaded_path)
        report_type = detect_report_type(pdf_path)

        try:
            process_file(pdf_path)
            if report_type == "UNKNOWN":
                skipped_unknown += 1
            else:
                processed_successfully += 1
        except Exception as exc:
            failed += 1
            print(f"Failed to process {pdf_path}: {exc}", file=sys.stderr)

    print("\nPipeline summary")
    print(f"total downloaded: {total_downloaded}")
    print(f"processed successfully: {processed_successfully}")
    print(f"failed: {failed}")
    print(f"skipped/unknown: {skipped_unknown}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run_pipeline())
