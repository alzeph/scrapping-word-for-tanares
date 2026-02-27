import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import colorsys

#  ────────────────────────────────────────────
# Classe : chargement & parsing CSV
# ─────────────────────────────────────────────

class RadioDataLoader:
    """Charge et nettoie les données depuis un CSV."""

    def __init__(self, filepath: str, sep: str = ","):
        self.filepath = filepath
        self.sep = sep
        self.df: pd.DataFrame = pd.DataFrame()

    def load(self) -> "RadioDataLoader":
        self.df = pd.read_csv(self.filepath, sep=self.sep)
        self._clean()
        return self

    def _clean(self):
        if "services" in self.df.columns:
            self.df = self.df[
                self.df["services"].notna() &
                (self.df["services"].astype(str).str.strip() != "")
            ].copy()

    @staticmethod
    def parse_band(band_str: str) -> tuple[float, float] | None:
        """
        '37,5–38,25 MHz' → (37.5, 38.25)
        Gère tirets longs/normaux et virgules décimales.
        """
        try:
            cleaned = (
                band_str
                .replace("MHz", "")
                .replace("\u2013", "-")
                .replace("\u2014", "-")
                .replace(" ", "")
                .replace(",", ".")
            )
            parts = cleaned.split("-")
            if len(parts) != 2:
                return None
            return float(parts[0]), float(parts[1])
        except (ValueError, AttributeError):
            return None

    def get_unique_services(self) -> list[str]:
        services = set()
        for val in self.df["services"].dropna():
            services.add(str(val).strip())
        return sorted(services)

    def iter_bands(self):
        """
        Itère sur les bandes groupées par 'bandes'.
        Yield: (band_str, (start_mhz, end_mhz), [services...])
        """
        for band, group in self.df.groupby("bandes", sort=False):
            coords = self.parse_band(str(band))
            if coords is None:
                continue
            svcs = [
                str(s).strip()
                for s in group["services"]
                if isinstance(s, str) and str(s).strip()
            ]
            if svcs:
                yield str(band), coords, svcs


# ─────────────────────────────────────────────
# Classe : palette couleurs
# ─────────────────────────────────────────────

class ServiceColorPalette:
    """Couleur unique et stable par service."""

    def __init__(self, services: list[str]):
        colors = self._generate_distinct_colors(len(services))
        self._palette: dict[str, tuple] = {
            svc: colors[i] for i, svc in enumerate(services)
        }

    def _generate_distinct_colors(self, n: int) -> list:
        """Génère n couleurs très distinctes via l'espace HSV."""
        if n == 0:
            return []
        colors = []
        for i in range(n):
            hue = i / n
            saturation = 0.65 + 0.35 * (i % 2)
            value = 0.55 + 0.45 * ((i // 2) % 2)
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            colors.append((r, g, b, 1.0))
        return colors


    def get(self, service: str, fallback=(0.8, 0.8, 0.8, 1.0)) -> tuple:
        return self._palette.get(service, fallback)

    def items(self):
        return self._palette.items()


# ─────────────────────────────────────────────
# Classe : affichage des bandes
# ─────────────────────────────────────────────

class BandRenderer:
    """
    Dessine les rectangles selon les vraies coordonnées MHz.

    Logique corrigée et stable :
      - services uniques (ordre conservé)
      - service[0] = fond principal
      - services secondaires = bandes fines en haut
      - aucune bande ne dépasse la hauteur totale
    """

    STRIP_H = 0.18   # hauteur des bandes secondaires
    MAX_STRIPS = 4   # sécurité visuelle

    def __init__(self, ax, palette: ServiceColorPalette):
        self.ax: plt.Axes = ax
        self.palette = palette

    def render(self, start: float, end: float, services: list[str]):
        width = end - start

        # 🔒 déduplication en conservant l’ordre
        seen = set()
        services = [s for s in services if not (s in seen or seen.add(s))]
        n = len(services)

        if n == 0:
            return

        # === 1 service ===
        if n == 1:
            self._rect(start, 0, width, 1.0, services[0])
            return

        # === 2 services ===
        if n == 2:
            self._rect(start, 0.0, width, 0.5, services[0])
            self._rect(start, 0.5, width, 0.5, services[1])
            return

        # === >2 services ===
        # Fond principal
        self._rect(start, 0, width, 1.0, services[0])

        # Bandes secondaires EN HAUT
        h = self.STRIP_H
        max_strips = min(len(services) - 1, self.MAX_STRIPS)

        for i in range(max_strips):
            svc = services[i + 1]
            y = 1.0 - (i + 1) * h
            if y < 0:
                break

            rect = patches.Rectangle(
                (start, y),
                width,
                h,
                facecolor=self.palette.get(svc),
                edgecolor="white",
                linewidth=0.3,
                alpha=0.9,
                zorder=4,
            )
            self.ax.add_patch(rect)

    def _rect(self, x, y, w, h, service: str):
        rect = patches.Rectangle(
            (x, y),
            w,
            h,
            facecolor=self.palette.get(service),
            # edgecolor="white",
            # linewidth=0.3,
            zorder=2,
        )
        self.ax.add_patch(rect)


class LabelManager:
    """
    Place les labels de fréquence en zig-zag vertical.

    Problème : sur l'axe réel MHz, des bandes très proches en fréquence
    produiront des labels qui se chevauchent.
    Solution : zig-zag sur LEVELS + skip_every configurable.
    """

    LEVELS = [1.04, 1.13, 1.22, 1.31, 1.40, 1.49]

    def __init__(self, ax, skip_every: int = 1, close_threshold: float = 0.0):
        """
        skip_every       : afficher 1 label sur N.
        close_threshold  : distance MHz en-dessous de laquelle on monte de niveau.
        """
        self.ax = ax
        self.skip_every = max(1, skip_every)
        self.close_threshold = close_threshold
        self._call_idx = 0
        self._level_idx = 0
        self._prev_x: float | None = None

    def add_label(self, x: float):
        """x : valeur de fréquence réelle (MHz) = position sur l'axe."""
        if self._call_idx % self.skip_every != 0:
            self._call_idx += 1
            return

        # Choisir le niveau vertical
        if self._prev_x is not None and abs(x - self._prev_x) < self.close_threshold:
            self._level_idx = (self._level_idx + 1) % len(self.LEVELS)
        else:
            # Alterner quand même même si pas proche, pour la lisibilité
            self._level_idx = (self._level_idx + 1) % len(self.LEVELS)

        y_text = self.LEVELS[self._level_idx]
        base_y = 1.01

        # Trait pointillé
        self.ax.plot(
            [x, x],
            [base_y, y_text - 0.015],
            linestyle="dotted",
            linewidth=0.7,
            color="#555555",
            alpha=0.85,
            zorder=5,
            clip_on=False,
        )

        # Texte
        label = str(int(x)) if float(x).is_integer() else f"{x:g}"
        self.ax.text(
            x, y_text, label,
            ha="center", va="bottom",
            fontsize=6.5,
            color="#111111",
            zorder=6,
            fontfamily="monospace",
            clip_on=False,
        )

        self._prev_x = x
        self._call_idx += 1


# ─────────────────────────────────────────────
# Classe : légende
# ─────────────────────────────────────────────

class LegendBuilder:
    """Légende en bas avec texte auto noir/blanc."""

    def __init__(self, ax, palette: ServiceColorPalette, ncol: int = 6):
        self.ax = ax
        self.palette = palette
        self.ncol = ncol

    def build(self):
        handles = [
            patches.Patch(
                facecolor=color,
                edgecolor="#333333",
                linewidth=0.5,
                label=service,
            )
            for service, color in self.palette.items()
        ]
        self.ax.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=self.ncol,
            frameon=True,
            framealpha=0.95,
            fontsize=8,
            title="Services",
            title_fontsize=9,
            edgecolor="#aaaaaa",
        )


class RadioBandDiagram:
    """
    Diagramme de bandes radio sur axe X en fréquences MHz réelles.

    Usage
    -----
    RadioBandDiagram("data.csv").build().save("out.png").show()
    """

    def __init__(
        self,
        csv_path: str,
        sep: str = ",",
        fig_height: int = 5,
        dpi: int = 150,
        legend_ncol: int = 6,
        output_path: str | None = None,
        pixels_per_mhz: float = 6.0,   # résolution horizontale
        max_width: int = 600,           # plafond largeur en pouces
        min_width: int = 40,
    ):
        self.csv_path = csv_path
        self.sep = sep
        self.fig_height = fig_height
        self.dpi = dpi
        self.legend_ncol = legend_ncol
        self.output_path = output_path
        self.pixels_per_mhz = pixels_per_mhz
        self.max_width = max_width
        self.min_width = min_width

        self.fig = None
        self.ax = None

    def build(self) -> "RadioBandDiagram":
        # 1. Données
        loader = RadioDataLoader(self.csv_path, self.sep).load()
        bands_data = list(loader.iter_bands())
        if not bands_data:
            raise ValueError("Aucune bande valide trouvée dans le CSV.")

        # 2. Étendue fréquentielle totale
        all_starts = [c[0] for _, c, _ in bands_data]
        all_ends   = [c[1] for _, c, _ in bands_data]
        freq_min, freq_max = min(all_starts), max(all_ends)
        freq_range = freq_max - freq_min

        # 3. Largeur figure basée sur MHz réels
        fig_width = (freq_range * self.pixels_per_mhz) / self.dpi
        fig_width = max(self.min_width, min(fig_width, self.max_width))

        # 4. skip_every : combien de pixels par bande en moyenne ?
        n_bands = len(bands_data)
        avg_band_width_mhz = freq_range / n_bands if n_bands else 1
        px_per_avg_band = avg_band_width_mhz * self.pixels_per_mhz
        if px_per_avg_band >= 40:
            skip_every = 1
        elif px_per_avg_band >= 20:
            skip_every = 2
        elif px_per_avg_band >= 10:
            skip_every = 4
        else:
            skip_every = max(1, int(40 / max(px_per_avg_band, 0.1)))

        # 5. Palette
        palette = ServiceColorPalette(loader.get_unique_services())

        # 6. Figure
        self.fig, self.ax = plt.subplots(figsize=(fig_width, self.fig_height), dpi=self.dpi)
        self.ax.set_ylim(0, 1.65)
        self.ax.set_yticks([])
        self.ax.spines[["top", "left", "right"]].set_visible(False)
        self.ax.spines["bottom"].set_linewidth(0.5)
        self.ax.set_xlabel("Fréquence (MHz)", fontsize=10, labelpad=4)
        self.ax.set_title(
            "Diagramme des bandes de fréquences radio (MHz)",
            fontsize=13, fontweight="bold", pad=6,
        )

        # 7. Tracé des bandes
        renderer = BandRenderer(self.ax, palette)
        label_mgr = LabelManager(
            self.ax,
            skip_every=skip_every,
            close_threshold=avg_band_width_mhz * 1.5,
        )

        for _, (start, end), services in bands_data:
            renderer.render(start, end, services)
            label_mgr.add_label(start)

        # 8. Axe X réel
        self.ax.set_xlim(freq_min, freq_max)

        # 9. Légende
        LegendBuilder(self.ax, palette, ncol=self.legend_ncol).build()

        # 10. Layout
        self.fig.tight_layout(rect=[0, 0.15, 1, 1])

        return self

    def save(self, path: str | None = None) -> "RadioBandDiagram":
        target = path or self.output_path
        if target:
            self.fig.savefig(target, bbox_inches="tight", dpi=self.dpi)
            print(f"✅ Sauvegardé → {target}")
        return self

    def show(self) -> "RadioBandDiagram":
        plt.show()
        return self


