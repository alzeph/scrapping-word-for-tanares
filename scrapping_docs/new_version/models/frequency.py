import re
from dataclasses import dataclass
from typing import Literal

Unity = Literal["GHz", "MHz", "KHz"]

_UNITS_IN_KHZ: dict[str, float] = {"KHz": 1.0, "MHz": 1_000.0, "GHz": 1_000_000.0}
_UNITY_ALIASES = {"khz": "KHz", "mhz": "MHz", "ghz": "GHz"}


def normalize_unity(text: str) -> Unity:
    """
    Normalise une unité écrite librement ('kHz', 'KHZ', ' Mhz ') vers Unity.
    """
    try:
        return _UNITY_ALIASES[text.strip().lower()]
    except KeyError:
        raise ValueError(f"Unité de fréquence inconnue : {text!r}")


def convert_frequency(value: float, from_unit: Unity, to_unit: Unity) -> float:
    """
    Convertit une fréquence entre KHz, MHz et GHz.
    """
    value_in_khz = value * _UNITS_IN_KHZ[from_unit]
    return value_in_khz / _UNITS_IN_KHZ[to_unit]


def parse_frequency(text: str) -> float:
    """
    Parse une fréquence écrite avec son unité et retourne sa valeur en GHz.
    Exemples valides : '100MHz', '8,3 kHz', '3.5GHz'.
    """
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*([kKmMgG][Hh][Zz])\s*", text)
    if not m:
        raise ValueError(
            f"Fréquence invalide : {text!r} (format attendu : '<valeur><unité>', ex. '100MHz')"
        )
    value = float(m.group(1).replace(",", "."))
    return convert_frequency(value, normalize_unity(m.group(2)), "GHz")


@dataclass(frozen=True)
class FrequencyInterval:
    """
    Intervalle de fréquences [start_ghz, end_ghz], exprimé en GHz.
    """

    start_ghz: float
    end_ghz: float

    def __post_init__(self):
        if self.start_ghz >= self.end_ghz:
            raise ValueError(
                f"Intervalle invalide : le début ({self.start_ghz} GHz) doit être "
                f"strictement inférieur à la fin ({self.end_ghz} GHz)"
            )

    @classmethod
    def from_texts(cls, start: str | None, end: str | None) -> "FrequencyInterval":
        """
        Construit un intervalle depuis des textes ('100MHz', '3GHz').
        Une borne absente donne un intervalle ouvert de ce côté.
        """
        start_ghz = parse_frequency(start) if start else 0.0
        end_ghz = parse_frequency(end) if end else float("inf")
        return cls(start_ghz, end_ghz)

    def overlaps(self, start_ghz: float, end_ghz: float) -> bool:
        """True si [start_ghz, end_ghz] intersecte l'intervalle."""
        return end_ghz > self.start_ghz and start_ghz < self.end_ghz

    def clip(self, start_ghz: float, end_ghz: float) -> tuple[float, float]:
        """Restreint [start_ghz, end_ghz] aux bornes de l'intervalle."""
        return max(start_ghz, self.start_ghz), min(end_ghz, self.end_ghz)
