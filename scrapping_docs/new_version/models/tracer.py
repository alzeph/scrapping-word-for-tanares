from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.transforms import Bbox

from scrapping_docs.new_version.models.band_repository import BandRecord
from scrapping_docs.new_version.models.frequency import (
    FrequencyInterval,
    convert_frequency,
)
from scrapping_docs.new_version.models.services import (
    GROUP_COLOR_SERVICE,
    NOT_ALLOCATED_COLOR,
    NOT_ALLOCATED_LABEL,
    colors_for_band,
)


class BandeTracer:
    """
    Trace le diagramme du spectre à partir de BandRecord.
    Ne connaît que le rendu : le chargement/filtrage des données
    est la responsabilité de BandRepository.
    """

    BASE_Y = 10
    HEIGHT = 12

    HEIGHT_BAR = 2

    ASSIGNEE_COLOR = "#98B3DE"
    # Lignes d'affectataires (style ANFR) : une ligne par affectataire,
    # contour bleu clair, bandes détenues remplies.
    ASSIGNEE_Y0 = BASE_Y + HEIGHT + 3   # au-dessus des étiquettes de fréquences
    ASSIGNEE_ROW_HEIGHT = 1.0
    ASSIGNEE_ROW_STEP = 1.45
    DEFAULT_ASSIGNEE_ROWS = 4
    LOGO_TEXT_GAP = 0.003   # en fraction de largeur d'axes

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
        "Bande VHF": ((0.550, 0.400, 0.700), (0.500, 0.420, 0.730)),
        "Bande UHF": ((0.500, 0.420, 0.730), (0.450, 0.440, 0.760)),
        "Bande SHF": ((0.450, 0.440, 0.760), (0.380, 0.450, 0.800)),
        "Bande EHF": ((0.380, 0.450, 0.800), (0.290, 0.410, 0.735)),
        "Bande THF": ((0.290, 0.410, 0.735), (0.200, 0.370, 0.667)),
    }

    def __init__(
        self,
        records: list[BandRecord],
        interval: FrequencyInterval | None = None,
        vertical_margin_inches: float | None = None,
        palette: str = "anfr",
        assignees: dict | None = None,
        logos_dir: str | None = None,
    ):
        self.records = records
        self.interval = interval
        self.palette = palette
        # {code: {"name", "logo"}} — vide pour la source Word : on garde
        # alors les lignes vides historiques.
        self.assignees = assignees or {}
        self.logos_dir = Path(logos_dir) if logos_dir else None
        self.legend_items: dict[str, str] = {}
        n_rows = len(self.assignees) or self.DEFAULT_ASSIGNEE_ROWS
        self.assignee_top = (
            self.ASSIGNEE_Y0
            + (n_rows - 1) * self.ASSIGNEE_ROW_STEP
            + self.ASSIGNEE_ROW_HEIGHT
        )
        self.y_bar = self.assignee_top + 1
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
        group_services = colors_for_band(
            record.services, self.palette, record.service_colors
        )
        self.legend_items.update(group_services)
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

    def render_headers_band(self, min_x, max_x):
        # Désignations UIT officielles. Le sous-titre affiche la plage
        # officielle ; le rectangle est recadré sur les données tracées.
        headers_band = {
            "Bande VLF": ("3-30 kHz", convert_frequency(3, "KHz", "GHz"), convert_frequency(30, "KHz", "GHz")),
            "Bande LF": ("30-300 kHz", convert_frequency(30, "KHz", "GHz"), convert_frequency(300, "KHz", "GHz")),
            "Bande MF": ("300 kHz-3 MHz", convert_frequency(300, "KHz", "GHz"), convert_frequency(3, "MHz", "GHz")),
            "Bande HF": ("3-30 MHz", convert_frequency(3, "MHz", "GHz"), convert_frequency(30, "MHz", "GHz")),
            "Bande VHF": ("30-300 MHz", convert_frequency(30, "MHz", "GHz"), convert_frequency(300, "MHz", "GHz")),
            "Bande UHF": ("300 MHz-3 GHz", convert_frequency(300, "MHz", "GHz"), 3.0),
            "Bande SHF": ("3-30 GHz", 3.0, 30.0),
            "Bande EHF": ("30-300 GHz", 30.0, 300.0),
            "Bande THF": ("300-3000 GHz", 300.0, 3000.0),
        }

        first_drawn = True
        for band, (subtitle, freq_min, freq_max) in headers_band.items():
            if freq_max <= min_x or freq_min >= max_x:
                continue
            freq_min, freq_max = max(freq_min, min_x), min(freq_max, max_x)

            color_left, color_right = self.HEADER_COLORS[band]
            self._draw_labeled_rectangle(
                freq_min, self.y_bar,
                freq_max - freq_min,
                self.HEIGHT_BAR,
                f"{band}",
                subtitle,
                color_left,
                color_right,
            )

            if not first_drawn:
                self.ax.plot(
                    [freq_min, freq_min],
                    [self.BASE_Y + self.HEIGHT, self.y_bar],
                    linewidth=2, linestyle="-", color="#141414",
                )
            first_drawn = False

    # ------------------------------------------------------------------
    # Légende et cadres
    # ------------------------------------------------------------------

    LEGEND_GAP_X = 0.005

    @classmethod
    def legend_width(cls, rows: int, box_width: float, n_items: int | None = None) -> float:
        """
        Largeur totale (en fraction d'axes) occupée par la légende des
        groupes de services pour un nombre de lignes donné. Sert à
        positionner la légende de droite en miroir exact de celle de
        gauche (même largeur, collée au bord opposé).
        """
        n_items = n_items if n_items is not None else len(GROUP_COLOR_SERVICE)
        columns = -(-n_items // rows)  # division entière arrondie au-dessus
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
        BOX_H = 0.04 if rows <= 4 else 0.032
        GAP_X = self.LEGEND_GAP_X
        GAP_Y = 0.05 if rows <= 4 else 0.04

        start_x = position_x
        start_y = 0.05

        col = 0
        row = 0

        for service, color in self._legend_entries().items():
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

    def _legend_entries(self) -> dict[str, str]:
        """
        Palette ANFR : les familles de Cédric, dans son ordre.
        Palette services : les services réellement tracés, triés par nom.
        « Non attribuée » en dernier si présente.
        """
        if self.palette == "services":
            items = {
                k: v for k, v in sorted(self.legend_items.items())
                if k != NOT_ALLOCATED_LABEL
            }
        else:
            items = dict(GROUP_COLOR_SERVICE)
        if NOT_ALLOCATED_LABEL in self.legend_items:
            items[NOT_ALLOCATED_LABEL] = NOT_ALLOCATED_COLOR
        return items

    def render_assignees_rows(self, min_x, max_x):
        """
        Une ligne par affectataire (style ANFR) : contour bleu clair sur
        toute la largeur, bandes détenues remplies, logo à gauche.
        """
        for i, code in enumerate(self.assignees):
            # Premier affectataire en haut
            y = self.assignee_top - self.ASSIGNEE_ROW_HEIGHT - i * self.ASSIGNEE_ROW_STEP
            self.ax.add_patch(patches.Rectangle(
                (min_x, y), max_x - min_x, self.ASSIGNEE_ROW_HEIGHT,
                fill=False, edgecolor=self.ASSIGNEE_COLOR, linewidth=3, zorder=3,
            ))
            for record in self.records:
                if code in record.assignees:
                    self.ax.add_patch(patches.Rectangle(
                        (record.start_ghz, y),
                        record.end_ghz - record.start_ghz,
                        self.ASSIGNEE_ROW_HEIGHT,
                        facecolor=self.ASSIGNEE_COLOR, edgecolor="none", zorder=2,
                    ))
            self._render_assignee_label(code, y + self.ASSIGNEE_ROW_HEIGHT / 2)

        self.ax.text(
            -0.004, self.assignee_top + 0.35, "AFFECTATAIRES",
            transform=self.ax.get_yaxis_transform(),
            ha="right", va="bottom", fontsize=70, fontweight="bold",
            color=self.ASSIGNEE_COLOR, clip_on=False,
        )

    def _row_height_points(self) -> float:
        """Hauteur d'une unité de l'axe Y, en points typographiques."""
        axes_h_in = self.ax.get_position().height * self.fig.get_figheight()
        y0, y1 = self.ax.get_ylim()
        return axes_h_in / (y1 - y0) * 72

    def _render_assignee_label(self, code: str, y_center: float):
        info = self.assignees.get(code, {})
        logo_file = Path(info.get("logo", "")).name
        logo_path = self.logos_dir / logo_file if (self.logos_dir and logo_file) else None

        if logo_path and logo_path.exists():
            img = mpimg.imread(str(logo_path))
            target_pts = self._row_height_points() * self.ASSIGNEE_ROW_STEP * 0.9
            zoom = target_pts / img.shape[0]
            self.ax.add_artist(AnnotationBbox(
                OffsetImage(img, zoom=zoom),
                (-0.004, y_center),
                xycoords=self.ax.get_yaxis_transform(),
                box_alignment=(1, 0.5),
                frameon=False,
                annotation_clip=False,
            ))
            # Code de l'affectataire à gauche du logo (logos souvent
            # illisibles à cette taille : sceaux, armoiries).
            axes_w_pts = self.ax.get_position().width * self.fig.get_figwidth() * 72
            logo_w_frac = img.shape[1] * zoom / axes_w_pts
            text_x = -0.004 - logo_w_frac - self.LOGO_TEXT_GAP
        else:
            text_x = -0.004
        self.ax.text(
            text_x, y_center, info.get("name", code),
            transform=self.ax.get_yaxis_transform(),
            ha="right", va="center", fontsize=60, fontweight="bold",
            color="#1F3A68", clip_on=False,
        )

    def render_assignees_band(self, min_x, max_x):
        """Cadres horizontaux au-dessus des bandes (zone affectataires)."""
        for i in np.arange(self.ASSIGNEE_Y0, self.assignee_top, self.ASSIGNEE_ROW_STEP):
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
        self.ax.set_ylim(0, self.y_bar + self.HEIGHT_BAR + 2)
        self.ax.set_xscale("log")

        self.render_headers_band(min_x, max_x)
        if self.palette == "services":
            # Libellés longs (« Exploration de la Terre par satellite ») :
            # cases plus larges, police plus petite.
            self.render_legende(rows=5, width=0.12, fontsize=48, position_x=0)
        else:
            self.render_legende(rows=4, width=0.07, fontsize=60, position_x=0)
        if self.assignees:
            self.render_assignees_rows(min_x=min_x, max_x=max_x)
        else:
            self.render_assignees_band(min_x=min_x, max_x=max_x)

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
