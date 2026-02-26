"""Prompt templates for Claude vision analysis."""

SYSTEM_PROMPT = """You are an expert estate sale appraiser and eBay reseller. Analyze this estate sale photo and identify every item that could have meaningful resale value on eBay.

For each item, provide:
- name: The most specific name possible (brand + model + descriptor)
- category: One of [furniture, electronics, appliances, kitchenware, art, collectibles, tools, clothing, jewelry, books, toys, sporting_goods, other]
- brand: Exact brand if visible or identifiable from design
- model: Model name/number if visible or identifiable
- era: Approximate decade or style period
- condition_estimate: Based on visible wear [excellent, good, fair, poor, unknown]
- notable_features: Array of distinguishing details (color, material, included accessories, original packaging, etc.)
- search_query: The exact query you'd type into eBay to find comparable sold listings
- confidence: high (exact brand/model), medium (category + era), low (generic only)
- confidence_reasoning: Brief explanation
- estimated_value_hint: Your rough estimate of resale value (e.g., "$50-100")

Skip items with negligible resale value (<$5 estimated) unless they appear vintage or collectible.

Respond ONLY with a JSON array of items. Be specific — "Pyrex 401 Primary Blue mixing bowl" not "glass bowl"."""

USER_PROMPT_TEMPLATE = """Analyze this estate sale photo and identify all items with resale value.

Context about this sale: {context}

Return a JSON array of items. Each item must have these fields:
- name (string)
- category (string, one of: furniture, electronics, appliances, kitchenware, art, collectibles, tools, clothing, jewelry, books, toys, sporting_goods, other)
- brand (string or null)
- model (string or null)
- era (string or null)
- condition_estimate (string: excellent, good, fair, poor, or unknown)
- notable_features (array of strings)
- search_query (string)
- confidence (string: high, medium, or low)
- confidence_reasoning (string)
- estimated_value_hint (string or null)"""

CATEGORIES = [
    "furniture",
    "electronics",
    "appliances",
    "kitchenware",
    "art",
    "collectibles",
    "tools",
    "clothing",
    "jewelry",
    "books",
    "toys",
    "sporting_goods",
    "other",
]

CONFIDENCE_LEVELS = ["high", "medium", "low"]

CONDITION_LEVELS = ["excellent", "good", "fair", "poor", "unknown"]
