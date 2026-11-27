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


# ----------------------------------------------------------------------
# Palettes de rendu
# ----------------------------------------------------------------------

# Bande « Non attribuée » : gris clair plutôt que le noir de « autres »,
# pour qu'une grande zone non attribuée (ex. 275-3000 GHz) ne domine pas.
NOT_ALLOCATED_LABEL = "Non attribuée"
NOT_ALLOCATED_COLOR = "#D9D9D9"

PALETTES = ("anfr", "services")


def _is_not_allocated(service: str) -> bool:
    return "NON ATTRIBUE" in normalize(service)


def colors_for_band(
    services: list[str],
    palette: str,
    service_colors: tuple[tuple[str, str], ...] = (),
) -> dict[str, str]:
    """
    Couleurs des sous-barres d'une bande, {libellé: couleur}.
    - 'anfr'     : 12 familles de services (couleurs ANFR de Cédric).
    - 'services' : une couleur par service, celle de la base (color_code).
    """
    allocated = [s for s in services if not _is_not_allocated(s)]
    if not allocated:
        return {NOT_ALLOCATED_LABEL: NOT_ALLOCATED_COLOR}

    if palette == "services" and service_colors:
        own = dict(service_colors)
        return {s: own.get(s, GROUP_COLOR_SERVICE["autres"]) for s in allocated}

    return get_group_services(allocated)
