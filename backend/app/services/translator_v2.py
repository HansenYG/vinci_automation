"""translator_v2 — Fast translation for the chatbot.

Pipeline: user message → to_english() (DeepL/Google) → LLM → _to_chinese() (Google) → user

Skips LLM translation calls for speed. DeepL/Google handle short messages well.
Quality check verifies lesson codes, dates, times survive translation.
"""

from __future__ import annotations

import re

from app.services.translator import CHINESE_RE

# Cantonese-specific markers (Traditional Chinese colloquialisms)
_YUE_MARKERS = re.compile(
    r"[㗎嘅係唔嗰乜嘢嗰度]"
    r"|嘅|係|唔|嗰|乜|㗎|咁|幾時|點解|做乜|做咩|唔好|嗰度|呢度"
)

# Lesson code pattern (e.g. L-2026-010)
_LESSON_CODE_RE = re.compile(r"L-\d{4}-\d{3}")
# Date patterns
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}")
# Time pattern
_TIME_RE = re.compile(r"\d{1,2}:\d{2}")


def detect_language(text: str) -> str:
    """Detect whether text is English, Cantonese, or Mandarin.

    Returns "en", "yue" (Cantonese), or "zh" (Mandarin).
    """
    if not CHINESE_RE.search(text):
        return "en"
    if _YUE_MARKERS.search(text):
        return "yue"
    return "zh"


def _translation_quality_check(original: str, translated: str) -> bool:
    """Verify critical tokens survived translation."""
    for pattern in (_LESSON_CODE_RE, _DATE_RE, _TIME_RE):
        orig_matches = pattern.findall(original)
        if orig_matches:
            for m in orig_matches:
                if m not in translated:
                    return False
    return True


def _google_translate(text: str, source: str = "zh-TW", target: str = "en") -> str | None:
    """Translate via Google Translate."""
    try:
        from deep_translator import GoogleTranslator

        result = GoogleTranslator(source=source, target=target).translate(text)
        return result.strip() if result else None
    except Exception:
        return None


def _deepl_translate(text: str, target_lang: str = "EN") -> str | None:
    """Translate via DeepL (free tier) if available."""
    try:
        from deep_translator import DeepLTranslator

        result = DeepLTranslator(source="auto", target=target_lang).translate(text)
        return result.strip() if result else None
    except Exception:
        return None


def to_english(text: str, source_lang: str = "zh") -> str:
    """Translate user message to English. Pipeline: DeepL → Google → original."""
    if not text or source_lang == "en":
        return text

    # 1. DeepL (fast, good quality)
    translated = _deepl_translate(text, "EN")
    if translated and _translation_quality_check(text, translated):
        return translated

    # 2. Google Translate (reliable fallback)
    source = "zh-TW" if source_lang in ("zh", "yue") else "zh-CN"
    translated = _google_translate(text, source=source, target="en")
    if translated and _translation_quality_check(text, translated):
        return translated

    # 3. Return original if all fail
    return text


def _to_chinese(text: str, target_lang: str = "zh") -> str:
    """Translate English response back to Chinese. target_lang: "zh" or "yue"."""
    if not text:
        return text

    # Google Translate (fast, preserves formatting better than LLM)
    target = "zh-TW"  # Default to Traditional Chinese
    translated = _google_translate(text, source="en", target=target)
    if translated:
        return translated

    return text
