import re

CHINESE_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")


def has_chinese(text: str) -> bool:
    return bool(CHINESE_RE.search(text))


def to_english(text: str) -> str:
    if not has_chinese(text):
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="zh-CN", target="en").translate(text)
    except Exception:
        return text


def from_english(text: str, original_had_chinese: bool) -> str:
    if not original_had_chinese:
        return text
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="en", target="zh-CN").translate(text)
        return translated if translated else text
    except Exception:
        return text
