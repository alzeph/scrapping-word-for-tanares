import unicodedata

GROUP_SERVICES = [
    "Aéronautique",
    "Radiodiffusion",
    "Maritime",
    "Scientifique",
    "Fixe",
    "Radioamateur",
    "Radiolocalisation",
    "Météorologie",
    "Mobile",
    "Satellite",
    "autres",
]

GROUP_COLOR_SERVICE = {
    "Aéronautique": "#1F5CA5",
    "Radiodiffusion": "#F9DB28",
    "Maritime": "#159C78",
    "Scientifique": "#F2A60E",
    "Fixe": "#BCA1CA",
    "Radioamateur": "#CF5F83",
    "Radiolocalisation": "#FFC000",
    "Météorologie": "#D76C0D",
    "Mobile": "#1D8CBC",
    "Satellite": "#774899",
    "autres": "#000000",
}


def normalize(s: str) -> str:
    """Supprime les accents et met en majuscules pour comparer les services."""
    if not isinstance(s, str):
        return ""
    nfkd_form = unicodedata.normalize("NFKD", s)
    sans_accents = "".join(c for c in nfkd_form if not unicodedata.combining(c))
    return sans_accents.upper()


def get_group_services(services: list[str]) -> dict[str, str]:
    """
    Associe chaque service à son (ses) groupe(s) et retourne {groupe: couleur}.
    Un service qui ne matche aucun groupe est classé dans 'autres'.
    """
    group_services: dict[str, str] = {}

    for service in services:
        service_norm = normalize(service)
        matched = False

        for group in GROUP_SERVICES[:-1]:
            if normalize(group) in service_norm:
                group_services[group] = GROUP_COLOR_SERVICE[group]
                matched = True

        if not matched:
            group_services["autres"] = GROUP_COLOR_SERVICE["autres"]

    return group_services
