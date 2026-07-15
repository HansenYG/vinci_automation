"""translator_v2 — LLM-native translation for the chatbot.

Pipeline: user message → to_english() → LLM (English only) → _to_chinese() → user

Uses _llm_chat() from chatbot.py for contextual translation that preserves
lesson codes, dates, school/course names. Falls back to DeepL then Google Translate.
"""

from __future__ import annotations

import re

from app.services.translator import CHINESE_RE

# Cantonese-specific markers ( Traditional Chinese colloquialisms )
_YUE_MARKERS = re.compile(
    r"[㗎嘅係唔嗰乜嘢畀嗰度點解幾時做咗未呢啦嘛嘅嗰啲咁]"
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


def _llm_translate(text: str, target_lang: str = "en") -> str | None:
    """Use the configured LLM to translate text contextually."""
    from app.services.chatbot import _llm_chat

    lang_name = {"en": "English", "zh": "Traditional Chinese (繁體中文)", "yue": "Cantonese (廣東話)"}.get(
        target_lang, target_lang
    )
    system = (
        f"Translate the following text to {lang_name}. "
        "Preserve exactly: lesson codes (L-2026-XXX), dates (YYYY-MM-DD, DD/MM), "
        "times (HH:MM), school names, course names, and numeric IDs. "
        "Do NOT add explanations. Return ONLY the translation."
    )
    result = _llm_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": text}],
        temperature=0.1,
        max_tokens=300,
    )
    if result and result.get("content"):
        translated = result["content"].strip()
        if _translation_quality_check(text, translated):
            return translated
    return None


def _deepl_translate(text: str, target_lang: str = "EN") -> str | None:
    """Translate via DeepL (free tier) if available."""
    try:
        from deep_translator import DeepLTranslator

        result = DeepLTranslator(source="auto", target=target_lang).translate(text)
        return result.strip() if result else None
    except Exception:
        return None


def _google_translate(text: str, source: str = "zh-TW", target: str = "en") -> str | None:
    """Translate via Google Translate as final fallback."""
    try:
        from deep_translator import GoogleTranslator

        result = GoogleTranslator(source=source, target=target).translate(text)
        return result.strip() if result else None
    except Exception:
        return None


def to_english(text: str, source_lang: str = "zh") -> str:
    """Translate user message to English. Pipeline: LLM → DeepL → Google → original."""
    if not text or source_lang == "en":
        return text

    # 1. LLM (best quality, preserves context)
    translated = _llm_translate(text, "en")
    if translated:
        return translated

    # 2. DeepL (good quality, fast)
    translated = _deepl_translate(text, "EN")
    if translated:
        return translated

    # 3. Google Translate (reliable fallback)
    source = "zh-TW" if source_lang in ("zh", "yue") else "zh-CN"
    translated = _google_translate(text, source=source, target="en")
    if translated:
        return translated

    # 4. Return original if all fail
    return text


def _to_chinese(text: str, target_lang: str = "zh") -> str:
    """Translate English response back to Chinese. target_lang: "zh" or "yue"."""
    if not text:
        return text

    # 1. LLM (best quality for natural Cantonese/Traditional Chinese)
    translated = _llm_translate(text, target_lang)
    if translated:
        return translated

    # 2. Google Translate fallback
    target = "zh-TW"  # Default to Traditional Chinese
    translated = _google_translate(text, source="en", target=target)
    if translated:
        return translated

    return text
