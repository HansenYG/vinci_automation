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


def batch_to_english(texts: list[str]) -> list[str]:
    """Translate a list of Chinese strings to English in one API call.

    Uses numbered lines (``0: text\\n1: text``) so we can re-map results
    even if Google Translate reorders or merges lines.
    """
    if not texts:
        return texts
    has_cjk = [has_chinese(t) for t in texts]
    if not any(has_cjk):
        return texts
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="zh-CN", target="en")
        numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(texts))
        translated = translator.translate(numbered)
        if not translated:
            return texts
        result = list(texts)
        for line in translated.split("\n"):
            line = line.strip()
            if ": " in line:
                idx_str, _, rest = line.partition(": ")
                try:
                    idx = int(idx_str.strip())
                    if 0 <= idx < len(result):
                        result[idx] = rest.strip()
                except ValueError:
                    pass
        return result
    except Exception:
        return texts


def from_english(text: str, original_had_chinese: bool) -> str:
    if not original_had_chinese:
        return text
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="en", target="zh-CN").translate(text)
        return translated if translated else text
    except Exception:
        return text
