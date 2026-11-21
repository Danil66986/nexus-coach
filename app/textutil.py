import re
import unicodedata


def norm(text: str) -> str:
    """Minuscules sans accents, pour comparer les mots-clés."""
    t = unicodedata.normalize("NFD", text.lower().replace("’", "'"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def has(text: str, *words: str) -> bool:
    return any(re.search(rf"\b{re.escape(w)}", text) for w in words)
