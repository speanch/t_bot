import base64
import logging

import aiohttp

from config import config

logger = logging.getLogger(__name__)

OPENROUTER_IMAGE_URL = "https://openrouter.ai/api/v1/images"

MODEL = "google/gemini-3.1-flash-lite-image"


def _to_data_url(raw: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


async def generate_fitting(
    car_image: bytes,
    part_image: bytes | None,
    part_description: str,
    instruction: str,
) -> str | None:
    prompt = (
        "Edit the first image (the car photo). Keep the car EXACTLY as it is: "
        "same model, same color, same angle, same lighting, same background, "
        "same shadows, same reflections. Do NOT generate a new car.\n\n"
    )
    if part_image:
        prompt += (
            "The second image shows the PART/ACCESSORY to install on this car. "
            "Take the part from the second image and physically place it on the car "
            "from the first image, matching perspective, scale, lighting, and shadows. "
        )
    prompt += (
        f"Modification requested: {instruction}"
    )
    if part_description:
        prompt += f"\nPart details: {part_description}"

    input_refs = [
        {"type": "image_url", "image_url": {"url": _to_data_url(car_image)}},
    ]
    if part_image:
        input_refs.append(
            {"type": "image_url", "image_url": {"url": _to_data_url(part_image)}}
        )

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "input_references": input_refs,
    }

    headers = {
        "Authorization": f"Bearer {config.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://avtomerka.local",
        "X-Title": "AvtoMerkaBot",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_IMAGE_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as resp:
                raw_text = await resp.text()
                if resp.status != 200:
                    logger.error("OpenRouter image error %s: %s", resp.status, raw_text)
                    return None
                data = await resp.json()
                logger.info("OpenRouter image response keys: %s", list(data.keys()))
                if "data" in data:
                    logger.info("Generated %d image(s)", len(data["data"]))
    except Exception as exc:
        logger.exception("OpenRouter image request failed: %s", exc)
        return None

    try:
        item = data["data"][0]
        if item.get("url"):
            return item["url"]
        if item.get("b64_json"):
            return f"data:image/png;base64,{item['b64_json']}"
    except (KeyError, IndexError, TypeError):
        logger.error("Unexpected OpenRouter image response: %s", data)

    return None
