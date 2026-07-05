import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.transforms import Bbox

from scrapping_docs.new_version.models.band_repository import BandRecord
from scrapping_docs.new_version.models.frequency import (
    FrequencyInterval,
    convert_frequency,
)
from scrapping_docs.new_version.models.services import (
    GROUP_COLOR_SERVICE,
    get_group_services,
)


class BandeTracer:
    """
    Trace le diagramme du spectre à partir de BandRecord.
    Ne connaît que le rendu : le chargement/filtrage des données
    est la responsabilité de BandRepository.
    """

    BASE_Y = 10
    HEIGHT = 12

    Y_BAR = BASE_Y + HEIGHT + 12
    HEIGHT_BAR = 2

    ASSIGNEE_COLOR = "#98B3DE"

    # Marge uniforme (en pouces) ajoutée autour de tout le contenu rendu
    # (bandes, en-têtes, légendes) lors de l'export : garantit un espace
    # constant par rapport au bord et centre le tracé sur la page.
    MARGIN_INCHES = 2.0

    # Résolution (dpi) utilisée pour l'export final : sert de référence pour
    # convertir la taille voulue de la colonne de logos (en pixels) en pouces.
    SAVE_DPI = 150

    # Largeur réservée (en pixels, à SAVE_DPI) pour une future colonne de
    # logos d'affectataires (100x100 px empilés) au-delà de la légende, de
    # part et d'autre du tracé. S'ajoute à MARGIN_INCHES uniquement à
    # l'horizontale : les marges haut/bas ne changent pas.
    LOGO_COLUMN_WIDTH_PX = 100

    HEADER_COLORS = {
        "Bande VLF": ((0.733, 0.271, 0.592), (0.700, 0.300, 0.610)),
        "Bande LF": ((0.700, 0.300, 0.610), (0.650, 0.340, 0.640)),
        "Bande MF": ((0.650, 0.340, 0.640), (0.600, 0.370, 0.670)),
        "Bande HF": ((0.600, 0.370, 0.670), (0.550, 0.400, 0.700)),
        "Bande UHF": ((0.550, 0.400, 0.700), (0.500, 0.420, 0.730)),
        "Bande VHF": ((0.500, 0.420, 0.730), (0.450, 0.440, 0.760)),
        "Bande VLH": ((0.450, 0.440, 0.760), (0.380, 0.450, 0.800)),
        "Bande LH": ((0.380, 0.450, 0.800), (0.200, 0.370, 0.667)),
    }

    def __init__(
        self,
        records: list[BandRecord],
        interval: FrequencyInterval | None = None,
        vertical_margin_inches: float | None = None,
    ):
        self.records = records
        self.interval = interval
        self.label_index = 0
        self.last_label_x = -float("inf")
        self.fig, self.ax = plt.subplots(figsize=(157.5, 78.7), dpi=200)
        # Marge verticale (en pouces) : si non fournie, on garde la valeur
        # par défaut historique (MARGIN_INCHES).
        self.vertical_margin_inches = (
            vertical_margin_inches
            if vertical_margin_inches is not None
            else self.MARGIN_INCHES
        )

    # ------------------------------------------------------------------
    # Primitives de dessin
    # ------------------------------------------------------------------

    def _rect(self, start, height, base_y, end, color: str):
        rect = plt.Rectangle(
            (start, base_y),
            (end - start),
            height,
            facecolor=color,
            zorder=2,
        )
        self.ax.add_patch(rect)

    def _draw_gradient_band(
        self, x_start, y, width, height, color_left, color_right,
        zorder=1, resolution=400,
    ):
        """Dessine un rectangle avec gradient horizontal."""
        x_end = x_start + width

        grad = np.linspace(0, 1, resolution)
        grad = np.vstack((grad, grad))

        r = color_left[0] + (color_right[0] - color_left[0]) * grad
        g = color_left[1] + (color_right[1] - color_left[1]) * grad
        b = color_left[2] + (color_right[2] - color_left[2]) * grad

        gradient_rgb = np.dstack((r, g, b))

        self.ax.imshow(
            gradient_rgb,
            extent=[x_start, x_end, y, y + height],
            aspect="auto",
            origin="lower",
            zorder=zorder,
        )

    def _compute_text_x(self, start, width):
        """
        Position X du texte à l'intérieur d'un rectangle selon sa largeur.
        """
        if width < 0.0001:
            frac = 0.1
        elif width < 0.1:
            frac = 0.03
        elif width < 1:
            frac = 0.02
        else:
            frac = 0.01
        return start + width * frac

    def _draw_labeled_rectangle(
        self, x, y, w, h, title, subtitle, color_left, color_right,
        edgecolor="white", linewidth=1.5,
    ):
        self._draw_gradient_band(x, y, w, h, color_left, color_right, zorder=1)

        rect = patches.Rectangle(
            (x, y), w, h,
            fill=False,
            edgecolor=edgecolor,
            linewidth=linewidth,
            zorder=2,
        )
        self.ax.add_patch(rect)

        self.ax.text(
            self._compute_text_x(x, w),
            y + h * 0.65,
            title,
            ha="left", va="center",
            fontsize=55, zorder=3, color="white",
        )
        self.ax.text(
            self._compute_text_x(x, w),
            y + h * 0.30,
            subtitle,
            ha="left", va="center",
            fontsize=55, fontweight="bold", zorder=3, color="white",
        )

    def _auto_text_color(self, hex_color: str) -> str:
        """Retourne noir ou blanc selon la luminosité du fond."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "black" if luminance > 140 else "white"

    # ------------------------------------------------------------------
    # Rendu des bandes
    # ------------------------------------------------------------------

    def render(self, record: BandRecord):
        """Dessine une bande et son étiquette de fréquence."""
        start, end = record.start_ghz, record.end_ghz
        group_services = get_group_services(record.services)
        group_services_keys = list(group_services.keys())

        if len(group_services_keys) == 0:
            return

        if len(group_services_keys) == 1:
            self._rect(
                start, self.HEIGHT, self.BASE_Y, end,
                group_services[group_services_keys[0]],
            )
        else:
            nbr_services = len(group_services_keys)
            height = self.HEIGHT / nbr_services
            base_y = self.BASE_Y
            for i in range(nbr_services):
                self._rect(start, height, base_y, end, group_services[group_services_keys[i]])
                base_y += height

        # ---------- ESCALIER CYCLIQUE 5 NIVEAUX ----------
        min_ratio = 1.15  # écart logarithmique minimal entre deux étiquettes
        if self.last_label_x > 0 and (start / self.last_label_x) < min_ratio:
            return

        levels = [0.10, 0.55, 1.10, 1.65, 2.10]
        offset = levels[self.label_index % 5]
        self.label_index += 1

        base_line = self.BASE_Y + self.HEIGHT
        text_height = base_line + offset + 0.05

        self.ax.text(
            start,
            text_height,
            f"{convert_frequency(start, 'GHz', record.unity):g}",
            ha="left", va="bottom",
            fontsize=40,
        )
        self.ax.plot(
            [start, start],
            [base_line, base_line + offset],
            linewidth=1, linestyle=":", color="#555555",
        )
        self.last_label_x = start

    def render_bands(self) -> tuple[float, float]:
        min_x = float("inf")
        max_x = float("-inf")

        for record in self.records:
            min_x = min(min_x, record.start_ghz)
            max_x = max(max_x, record.end_ghz)
            self.render(record)
        return min_x, max_x

    # ------------------------------------------------------------------
    # En-têtes de familles de bandes (VLF → LH)
    # ------------------------------------------------------------------

    def render_headers_band(self, max_x):
        # `unit` sert uniquement à formater le sous-titre affiché ; les
        # bornes réelles sont toujours calculées/recadrées en GHz.
        headers_band = {
            "Bande VLF": {"unit": "KHz", "freq": [convert_frequency(8.3, "KHz", "GHz"), convert_frequency(30, "KHz", "GHz")]},
            "Bande LF": {"unit": "KHz", "freq": [convert_frequency(30, "KHz", "GHz"), convert_frequency(300, "KHz", "GHz")]},
            "Bande MF": {"unit": "MHz", "freq": [convert_frequency(300, "KHz", "GHz"), convert_frequency(3, "MHz", "GHz")]},
            "Bande HF": {"unit": "MHz", "freq": [convert_frequency(3, "MHz", "GHz"), convert_frequency(30, "MHz", "GHz")]},
            "Bande UHF": {"unit": "MHz", "freq": [convert_frequency(30, "MHz", "GHz"), convert_frequency(300, "MHz", "GHz")]},
            "Bande VHF": {"unit": "GHz", "freq": [convert_frequency(300, "MHz", "GHz"), 3.0]},
            "Bande VLH": {"unit": "GHz", "freq": [3.0, 30.0]},
            "Bande LH": {"unit": "GHz", "freq": [30.0, max(max_x, 30.0)]},
        }

        first_freq_min = headers_band["Bande VLF"]["freq"][0]

        for band, band_info in headers_band.items():
            freq_min, freq_max = band_info["freq"]

            # Ne garder que la portion visible dans l'intervalle demandé
            if self.interval is not None:
                if not self.interval.overlaps(freq_min, freq_max):
                    continue
                freq_min, freq_max = self.interval.clip(freq_min, freq_max)

            unit = band_info["unit"]
            label_min = convert_frequency(freq_min, "GHz", unit)
            label_max = convert_frequency(freq_max, "GHz", unit)
            subtitle = f"{label_min:g}-{label_max:g} {unit}"

            color_left, color_right = self.HEADER_COLORS[band]
            self._draw_labeled_rectangle(
                freq_min, self.Y_BAR,
                freq_max - freq_min,
                self.HEIGHT_BAR,
                f"{band}",
                subtitle,
                color_left,
                color_right,
            )

            if freq_min != first_freq_min:
                self.ax.plot(
                    [freq_min, freq_min],
                    [self.BASE_Y + self.HEIGHT, self.Y_BAR],
                    linewidth=2, linestyle="-", color="#141414",
                )

    # ------------------------------------------------------------------
    # Légende et cadres
    # ------------------------------------------------------------------

    LEGEND_GAP_X = 0.005

    @classmethod
    def legend_width(cls, rows: int, box_width: float) -> float:
        """
        Largeur totale (en fraction d'axes) occupée par la légende des
        groupes de services pour un nombre de lignes donné. Sert à
        positionner la légende de droite en miroir exact de celle de
        gauche (même largeur, collée au bord opposé).
        """
        columns = -(-len(GROUP_COLOR_SERVICE) // rows)  # division entière arrondie au-dessus
        return columns * box_width + (columns - 1) * cls.LEGEND_GAP_X

    def render_legende(
        self,
        rows: int = 4,
        width: float = 0.07,
        fontsize: int = 8,
        position_x: float = 0.05,
    ):
        """Affiche la légende des groupes de services."""
        BOX_W = width
        BOX_H = 0.04
        GAP_X = self.LEGEND_GAP_X
        GAP_Y = 0.05

        start_x = position_x
        start_y = 0.05

        col = 0
        row = 0

        for service, color in GROUP_COLOR_SERVICE.items():
            x = start_x + col * (BOX_W + GAP_X)
            y = start_y + row * GAP_Y

            rect = patches.Rectangle(
                (x, y),
                BOX_W, BOX_H,
                transform=self.ax.transAxes,
                facecolor=color,
                edgecolor="white",
                linewidth=0.6,
                zorder=50,
                clip_on=False,
            )
            self.ax.add_patch(rect)

            self.ax.text(
                x + BOX_W * 0.5,
                y + BOX_H * 0.5,
                service,
                transform=self.ax.transAxes,
                ha="center", va="center",
                fontsize=fontsize,
                color=self._auto_text_color(color),
                weight="bold",
                zorder=51,
            )

            row += 1
            if row >= rows:
                row = 0
                col += 1

    def render_assignees_band(self, min_x, max_x):
        """Cadres horizontaux au-dessus des bandes (zone affectataires)."""
        for i in range(self.BASE_Y + self.HEIGHT + 4, self.BASE_Y + self.HEIGHT + 12, 2):
            self.ax.hlines(i, min_x, max_x, color=self.ASSIGNEE_COLOR, linewidth=3)
            self.ax.hlines(i + 1, min_x, max_x, color=self.ASSIGNEE_COLOR, linewidth=3)
            self.ax.vlines(min_x, i, i + 1, color=self.ASSIGNEE_COLOR, linewidth=3)
            self.ax.vlines(max_x, i, i + 1, color=self.ASSIGNEE_COLOR, linewidth=3)

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------

    def save(self, output_path: str = "tanares.png"):
        print("rendering...")
        min_x, max_x = self.render_bands()

        if min_x == float("inf"):
            raise ValueError("Aucune bande à tracer dans l'intervalle demandé.")

        self.render_headers_band(max_x)
        legend_rows = 4
        legend_box_width = 0.07
        right_legend_x = 1.0 - self.legend_width(legend_rows, legend_box_width)
        self.render_legende(rows=legend_rows, width=legend_box_width, fontsize=60, position_x=0)
        self.render_legende(rows=legend_rows, width=legend_box_width, fontsize=60, position_x=right_legend_x)
        self.render_assignees_band(min_x=min_x, max_x=max_x)

        if self.interval is not None:
            # Se caler sur l'intervalle demandé (bornes ouvertes → données)
            if self.interval.start_ghz > 0:
                min_x = self.interval.start_ghz
            if self.interval.end_ghz != float("inf"):
                max_x = self.interval.end_ghz
        # Sans intervalle explicite, on se cale strictement sur les bornes
        # réelles des données (min_x/max_x issus de render_bands) : ajouter
        # une marge fixe en fréquence linéaire (ex. 1KHz / 3500GHz) crée une
        # marge très asymétrique une fois passée à l'échelle log, ce qui
        # décale visuellement tout le tracé par rapport à la légende
        # (centrée, elle, sur l'ensemble de l'axe).

        self.ax.set_xlim(float(min_x), float(max_x))
        self.ax.set_ylim(0, 38)
        self.ax.set_xscale("log")

        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_xticks([])
        self.ax.xaxis.set_minor_locator(plt.NullLocator())
        self.ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
        self.ax.set_yticks([])

        # Marge asymétrique : on part du bbox "tight" réel (bandes + légendes)
        # puis on ajoute MARGIN_INCHES sur les 4 côtés, plus la largeur de la
        # future colonne de logos uniquement à gauche et à droite.
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        tight_bbox = self.fig.get_tightbbox(renderer)

        logo_column_inches = self.LOGO_COLUMN_WIDTH_PX / self.SAVE_DPI
        horizontal_margin = (self.MARGIN_INCHES + logo_column_inches) * 5

        export_bbox = Bbox.from_extents(
            tight_bbox.x0 - horizontal_margin,
            tight_bbox.y0 - self.vertical_margin_inches,
            tight_bbox.x1 + horizontal_margin,
            tight_bbox.y1 + self.vertical_margin_inches,
        )

        self.fig.savefig(
            output_path,
            bbox_inches=export_bbox,
            dpi=self.SAVE_DPI,
        )
        print(f"Sauvegardé dans {output_path}")
        plt.close(self.fig)
