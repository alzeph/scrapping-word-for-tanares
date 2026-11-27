"""
Source de données « base TANARES » : lit un CSV exporté depuis la base
Laravel (une ligne par allocation) au lieu des documents Word.

Colonnes attendues :
    freq_start, freq_end, unit, service_priority, service_code,
    service_name, service_color, service_anfr_color,
    assignee_code, assignee_name, assignee_logo
"""

from collections import OrderedDict
from typing import Iterator

import pandas as pd

from scrapping_docs.new_version.models.band_repository import BandRecord
from scrapping_docs.new_version.models.frequency import (
    FrequencyInterval,
    convert_frequency,
    normalize_unity,
)


class DbBandRepository:
    """Regroupe les allocations par bande (début, fin, unité)."""

    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    def assignees(self) -> "OrderedDict[str, dict]":
        """
        Affectataires présents, dans l'ordre de première apparition :
        {code: {"name": ..., "logo": ...}}.
        """
        result: "OrderedDict[str, dict]" = OrderedDict()
        for _, row in self.df.iterrows():
            code = row.get("assignee_code", "").strip()
            if code and code not in result:
                result[code] = {
                    "name": row.get("assignee_name", "").strip() or code,
                    "logo": row.get("assignee_logo", "").strip(),
                }
        return result

    def iter_bands(
        self, interval: FrequencyInterval | None = None
    ) -> Iterator[BandRecord]:
        keys = ["freq_start", "freq_end", "unit"]
        for (start_txt, end_txt, unit_txt), group in self.df.groupby(keys, sort=False):
            try:
                start, end = float(start_txt), float(end_txt)
                unity = normalize_unity(unit_txt)
            except ValueError:
                continue
            # Échelle log : une bande qui commence à 0 ne peut pas être tracée.
            if start <= 0 or end <= start:
                continue

            start_ghz = convert_frequency(start, unity, "GHz")
            end_ghz = convert_frequency(end, unity, "GHz")
            if interval is not None:
                if not interval.overlaps(start_ghz, end_ghz):
                    continue
                start_ghz, end_ghz = interval.clip(start_ghz, end_ghz)

            services: list[str] = []
            colors: dict[str, str] = {}
            for _, row in group.iterrows():
                name = row["service_name"].strip()
                if name and name not in colors:
                    services.append(name)
                    colors[name] = row["service_color"].strip() or "#000000"

            assignees = tuple(
                dict.fromkeys(
                    code.strip() for code in group["assignee_code"] if code.strip()
                )
            )

            if services:
                yield BandRecord(
                    label=f"{start:g}-{end:g}-{unity}",
                    start_ghz=start_ghz,
                    end_ghz=end_ghz,
                    services=services,
                    unity=unity,
                    service_colors=tuple(colors.items()),
                    assignees=assignees,
                )
