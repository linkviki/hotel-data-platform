import os
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def clean_json_response(raw: str) -> dict:
    import re

    raw = raw.strip()

    #print("\n--- RAW VISION RESPONSE START ---")
    #print(raw[:3000])
    #print("--- RAW VISION RESPONSE END ---\n")

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    # Extract only the JSON object from surrounding text
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in vision response")

    json_text = match.group(0)

    return json.loads(json_text)


def extract_json_from_image(image_path: Path, prompt: str) -> dict:
    image_base64 = encode_image(image_path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_base64}",
                    },
                ],
            }
        ],
    )

    return clean_json_response(response.output_text)