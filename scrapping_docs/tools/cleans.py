import re

def extract_from_first_digit(s: str) -> list[str]:
    """
    Retourne la partie de la chaîne qui commence par un nombre
    (ex: 'texte 5.54A' -> ['5.54A']),
    en ignorant les nombres entre parenthèses.
    """
    if not s:
        return []

    # supprimer tout ce qui est entre parenthèses
    without_parentheses = re.sub(r'\([^)]*\)', '', s)

    # chercher le premier nombre hors parenthèses
    m = re.search(r'\d.*$', without_parentheses)
    result =  [m.group()] if m else []
    _result = []
    for i in result:
        a = i.split(" ")
        _result.extend(a)
    result = _result
    return result

def remove_from_first_digit(s: str) -> str:
    """
    Retourne la chaîne `s` sans les caractères de début qui forment un nombre.
    (ex: 'salut le monde 5.54A' devient 'salut le monde').
    """
    return re.sub(r'\d.*$', '', s)

def filter_exact_number_prefix(strings: list[str], number: str) -> list[str]:
    """
    Retourne les chaînes qui commencent exactement par `number`
    (ex: '5.54' ne matche pas '5.54A').
    """
    regex = re.compile(rf'^{re.escape(number)}\b')
    return [s for s in strings if regex.match(s)]

def starts_with_exact_number(text: str, number: str) -> bool:
    """
    Retourne True si text commence exactement par number (ex: '5.54'),
    sans lettre après.
    """
    regex = re.compile(rf'^{re.escape(number)}\b')
    return bool(regex.match(text))

def starts_with_number_like(text: str) -> bool:
    """
    Retourne True si le texte commence par :
    - un chiffre
    - un point
    - deux chiffres après le point
    - éventuellement une lettre juste après
    Exemples valides : '5.54', '5.54A', '1.23B'
    """
    regex = re.compile(r'^\d\.\d{2}[A-Za-z]?')
    return bool(regex.match(text))

def extract_text_after_specific_number(text: str, number: str) -> str:
    """
    Retourne le texte qui vient après number si text commence exactement
    par number. Sinon, retourne une chaîne vide.
    """
    if starts_with_exact_number(text, number):
        # retirer le nombre et les espaces qui suivent
        return re.sub(rf'^{re.escape(number)}\s*', '', text)
    return ''


def extract_first_text_after_number(texts: list[str], number: str) -> str:
    """
    Parcourt une liste de chaînes et retourne le texte qui vient après
    number pour la première chaîne qui commence exactement par number.
    Retourne une chaîne vide si aucune correspondance.
    """
    for text in texts:
        if starts_with_exact_number(text, number):
            # retirer le nombre et les espaces qui suivent
            return re.sub(rf'^{re.escape(number)}\s*', '', text)
    return ''
