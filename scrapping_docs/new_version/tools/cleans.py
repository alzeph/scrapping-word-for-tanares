import re


def extract_from_first_digit(s: str) -> list[str]:
    """
    Retourne la partie de la chaîne qui commence par un nombre
    (ex: 'texte 5.54A' -> ['5.54A']),
    en ignorant les nombres entre parenthèses.
    """
    if not s:
        return []

    without_parentheses = re.sub(r"\([^)]*\)", "", s)

    m = re.search(r"\d.*$", without_parentheses)
    result = [m.group()] if m else []
    _result = []
    for i in result:
        a = i.split(" ")
        _result.extend(a)
    return _result


def remove_from_first_digit(s: str) -> str:
    """
    Retourne la chaîne `s` sans les caractères de fin qui forment un nombre.
    (ex: 'salut le monde 5.54A' devient 'salut le monde').
    """
    return re.sub(r"\d.*$", "", s)


def starts_with_exact_number(text: str, number: str) -> bool:
    """
    Retourne True si text commence exactement par number (ex: '5.54'),
    sans lettre après.
    """
    regex = re.compile(rf"^{re.escape(number)}\b")
    return bool(regex.match(text))


def starts_with_number_like(text: str) -> bool:
    """
    Retourne True si le texte commence par un motif type '5.54' ou '5.54A'.
    """
    regex = re.compile(r"^\d\.\d{2}[A-Za-z]?")
    return bool(regex.match(text))


def extract_first_text_after_number(texts: list[str], number: str) -> str:
    """
    Parcourt une liste de chaînes et retourne le texte qui vient après
    `number` pour la première chaîne qui commence exactement par `number`.
    Retourne une chaîne vide si aucune correspondance.
    """
    for text in texts:
        if starts_with_exact_number(text, number):
            return re.sub(rf"^{re.escape(number)}\s*", "", text)
    return ""


def clean_paragraph(texte: str) -> str:
    if not texte:
        return ""
    return " ".join(texte.replace('"', "").split())


def clean_texte_special(texte: str) -> str:
    if not texte:
        return ""

    # Supprimer les espaces autour des tirets
    texte = re.sub(r"\s*-\s*", "-", texte)

    # Supprimer les espaces à l'intérieur des nombres
    texte = re.sub(r"(\d)\s+(\d)", r"\1\2", texte)

    # Supprimer les espaces multiples restants
    texte = re.sub(r"\s+", " ", texte)

    return texte.strip()
