"""Claude vision API integration for item identification."""

import asyncio
import base64
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from PIL import Image

from estate_pricer.analyzer.prompts import (
    CATEGORIES,
    CONDITION_LEVELS,
    CONFIDENCE_LEVELS,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from estate_pricer.config import Config


MAX_IMAGE_DIMENSION = 1568  # Max pixels on longest edge for token optimization


def _resize_image_if_needed(image_path: str) -> bytes:
    """Resize image to max dimension and return as bytes."""
    with Image.open(image_path) as img:
        if img.mode == "RGBA":
            img = img.convert("RGB")

        width, height = img.size
        if max(width, height) > MAX_IMAGE_DIMENSION:
            ratio = MAX_IMAGE_DIMENSION / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def _get_media_type(image_path: str) -> str:
    """Determine media type from file extension."""
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(ext, "image/jpeg")


def _validate_item(item: dict) -> dict:
    """Validate and normalize an identified item."""
    # Ensure required fields
    if not item.get("name") or not item.get("search_query"):
        return None

    # Normalize category
    category = item.get("category", "other").lower()
    if category not in CATEGORIES:
        category = "other"
    item["category"] = category

    # Normalize confidence
    confidence = item.get("confidence", "low").lower()
    if confidence not in CONFIDENCE_LEVELS:
        confidence = "low"
    item["confidence"] = confidence

    # Normalize condition
    condition = item.get("condition_estimate", "unknown").lower()
    if condition not in CONDITION_LEVELS:
        condition = "unknown"
    item["condition_estimate"] = condition

    # Ensure lists
    if not isinstance(item.get("notable_features"), list):
        item["notable_features"] = []

    # Generate ID
    item["item_id"] = str(uuid.uuid4())

    return item


async def analyze_photo(
    image_path: str,
    config: Config,
    context: str = "",
    sale_id: str = "",
) -> list[dict]:
    """Analyze a single photo with Claude vision and return identified items.

    Args:
        image_path: Path to the image file.
        config: Application configuration.
        context: Optional context about the sale.
        sale_id: Sale ID for linking items.

    Returns:
        List of identified item dicts.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    # Prepare image
    image_data = _resize_image_if_needed(image_path)
    b64_image = base64.b64encode(image_data).decode("utf-8")
    media_type = _get_media_type(image_path)

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context or "No additional context provided"
    )

    # Call Claude API
    message = client.messages.create(
        model=config.analyzer.model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                ],
            }
        ],
    )

    # Parse response
    response_text = message.content[0].text.strip()

    # Handle markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    try:
        raw_items = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON array from response
        start = response_text.find("[")
        end = response_text.rfind("]") + 1
        if start >= 0 and end > start:
            raw_items = json.loads(response_text[start:end])
        else:
            return []

    if not isinstance(raw_items, list):
        raw_items = [raw_items]

    # Generate photo_id from the image path
    photo_id = str(uuid.uuid5(uuid.NAMESPACE_URL, image_path))
    now = datetime.now(timezone.utc).isoformat()

    items = []
    for raw in raw_items:
        item = _validate_item(raw)
        if item:
            item["photo_id"] = photo_id
            item["sale_id"] = sale_id
            item["identified_at"] = now
            items.append(item)

    return items


async def analyze_photos(
    image_paths: list[str],
    config: Config,
    context: str = "",
    sale_id: str = "",
) -> list[dict]:
    """Analyze multiple photos concurrently.

    Args:
        image_paths: List of image file paths.
        config: Application configuration.
        context: Optional context about the sale.
        sale_id: Sale ID for linking items.

    Returns:
        List of all identified items across all photos.
    """
    semaphore = asyncio.Semaphore(config.analyzer.max_concurrency)

    async def _analyze_with_limit(path):
        async with semaphore:
            try:
                return await analyze_photo(path, config, context, sale_id)
            except Exception as e:
                print(f"[warning] Failed to analyze {path}: {e}")
                return []

    tasks = [_analyze_with_limit(path) for path in image_paths]
    results = await asyncio.gather(*tasks)

    all_items = []
    for items in results:
        all_items.extend(items)

    return all_items
