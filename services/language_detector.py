from langdetect import detect, LangDetectException


def detect_language(text: str) -> str:
    try:
        return detect(text[:5000])
    except LangDetectException:
        return "unknown"
