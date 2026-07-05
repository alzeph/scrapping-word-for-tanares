from dataclasses import dataclass
from typing import Iterator

import pandas as pd

from scrapping_docs.new_version.models.frequency import (
    FrequencyInterval,
    Unity,
    convert_frequency,
    normalize_unity,
)


@dataclass(frozen=True)
class BandRecord:
    """
    Une bande de fréquences prête à être tracée.
    Les bornes sont exprimées en GHz, l'unité d'origine est conservée
    pour l'affichage des étiquettes.
    """

    label: str
    start_ghz: float
    end_ghz: float
    services: list[str]
    unity: Unity


class BandRepository:
    """
    Charge les CSV produits par l'extraction et fournit les bandes,
    avec filtrage optionnel sur un intervalle de fréquences.
    """

    def __init__(self, csv_paths: dict[str, str], sep: str = ","):
        self.df = pd.concat(
            [pd.read_csv(csv_path, sep=sep) for csv_path in csv_paths.values()],
            ignore_index=True,
        )
        self._clean()

    def _clean(self):
        if "services" in self.df.columns:
            self.df = self.df[
                self.df["services"].notna()
                & (self.df["services"].astype(str).str.strip() != "")
            ].copy()

    @staticmethod
    def parse_band(band_str: str) -> tuple[float, float, Unity] | None:
        """
        '37,5–38,25-MHz' → (37.5, 38.25, 'MHz')
        Gère tirets longs/normaux et virgules décimales.
        Retourne None si la valeur n'est pas une bande exploitable.
        """
        try:
            cleaned = (
                band_str
                .replace("–", "-")
                .replace("—", "-")
                .replace(" ", "")
                .replace(",", ".")
            )
            parts = cleaned.split("-")
            if len(parts) != 3:
                return None
            return float(parts[0]), float(parts[1]), normalize_unity(parts[2])
        except (ValueError, AttributeError):
            return None

    def iter_bands(
        self, interval: FrequencyInterval | None = None
    ) -> Iterator[BandRecord]:
        """
        Itère sur les bandes valides, bornes converties en GHz.
        Si `interval` est fourni, seules les bandes qui l'intersectent
        sont retournées, découpées à ses bornes.
        """
        for band, group in self.df.groupby("bandes", sort=False):
            parsed = self.parse_band(str(band))
            if parsed is None:
                continue
            start, end, unity = parsed

            start_ghz = convert_frequency(start, unity, "GHz")
            end_ghz = convert_frequency(end, unity, "GHz")

            if interval is not None:
                if not interval.overlaps(start_ghz, end_ghz):
                    continue
                start_ghz, end_ghz = interval.clip(start_ghz, end_ghz)

            services = [
                str(s).strip()
                for s in group["services"]
                if isinstance(s, str) and str(s).strip()
            ]
            if services:
                yield BandRecord(str(band), start_ghz, end_ghz, services, unity)
