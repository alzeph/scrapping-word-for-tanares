import unicodedata
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import matplotlib.image as mpimg
import colorsys
import numpy as np


from typing import Literal
Unity = Literal["GHz", "MHz", "KHz"]
class BandeTracers:
    BASE_Y = 10
    HEIGHT = 12
    
    Y_BAR = BASE_Y + HEIGHT + 12
    Y_LEGEND = 0
    HEIGHT_BAR = 2
    HEIGHT_LEGEND = 1
    
    HEADER_COLORS = {
    "Bande VLF": ((0.733,0.271,0.592), (0.700,0.300,0.610)),
    "Bande LF":  ((0.700,0.300,0.610), (0.650,0.340,0.640)),
    "Bande MF":  ((0.650,0.340,0.640), (0.600,0.370,0.670)),
    "Bande HF":  ((0.600,0.370,0.670), (0.550,0.400,0.700)),
    "Bande UHF": ((0.550,0.400,0.700), (0.500,0.420,0.730)),
    "Bande VHF": ((0.500,0.420,0.730), (0.450,0.440,0.760)),
    "Bande VLH": ((0.450,0.440,0.760), (0.380,0.450,0.800)),
    "Bande LH":  ((0.380,0.450,0.800), (0.200,0.370,0.667)),
}
    
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
        "autres"
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
        "autres": "#000000"
    }
    
    ASSIGNEE_COLOR = "#98B3DE"
    ASSIGNEE_LOGO = {
        "ANAC" : mpimg.imread("/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/logo/ANAC.jpeg"),
        "ARTCI" : mpimg.imread("/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/logo/ARTCI.jpeg"),
        "DGAMP" : mpimg.imread("/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/logo/DGAMP.jpeg"),
        "GOUVERNEMENT" : mpimg.imread("/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/logo/GOUVERNEMENT.jpeg"),
    }
    
    def __init__(self, csv_paths: dict[str, str], sep: str = ","):
        self.label_index = 0
        self.last_label_x = -float("inf")  # x du dernier label tracé
        self.min_label_gap = 1000  # distance minimale entre labels (unités bande)
        self.fig, self.ax = plt.subplots(figsize=(157.5, 78.7), dpi=200)
        self.df = pd.concat(
            [pd.read_csv(csv_path, sep=sep) for csv_path in csv_paths.values()],
            ignore_index=True
        )
        self._clean()
        
    def convert_frequency(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convertit une fréquence entre kHz, MHz et GHz.
        
        value : valeur numérique
        from_unit : "kHz", "MHz" ou "GHz"
        to_unit : "kHz", "MHz" ou "GHz"
        """
        units = {"KHz": 1, "MHz": 1_000, "GHz": 1_000_000}
        
        # Conversion vers kHz
        value_in_khz = value * units[from_unit]
        
        # Conversion vers unité cible
        return value_in_khz / units[to_unit]
    
    def _clean(self):
        if "services" in self.df.columns:
            self.df = self.df[
                self.df["services"].notna() &
                (self.df["services"].astype(str).str.strip() != "")
            ].copy()
    
    def _draw_logo(self, img, x, y, height, text="", fontsize=50, gap=0.01):
        """
        Place un logo avec texte à droite dans les coordonnées Axes,
        respecte le ratio de l'image.
        x, y, height en fraction de l'axe (0 → 1)
        """
        h, w = img.shape[:2]
        ratio = w / h
        width = height * ratio  # largeur proportionnelle pour garder le ratio

        # image
        self.ax.imshow(
            img,
            extent=[x, x + width, y, y + height],
            transform=self.ax.transAxes,
            aspect="auto",
            zorder=20,
            clip_on=False,
        )

        # texte à droite
        if text:
            self.ax.text(
                x + width + gap,
                y + height / 2,
                text,
                transform=self.ax.transAxes,
                va="center",
                ha="left",
                fontsize=fontsize,
                zorder=21,
            )

    def parse_band(self, band_str: str) -> tuple[float, float] | None:
        """
        '37,5–38,25 MHz' → (37.5, 38.25)
        Gère tirets longs/normaux et virgules décimales.
        """
        try:
            cleaned = (
                band_str
                .replace("\u2013", "-")
                .replace("\u2014", "-")
                .replace(" ", "")
                .replace(",", ".")
            )
            parts = cleaned.split("-")
            if len(parts) != 3:
                return None
            return float(parts[0]), float(parts[1]), str(parts[2])
        except (ValueError, AttributeError):
            return None

    def normalize(self, s: str) -> str:
        if not isinstance(s, str):
            return ""
        
        # Supprimer les accents
        nfkd_form = unicodedata.normalize('NFKD', s)
        sans_accents = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        
        # Mettre en majuscules
        return sans_accents.upper()
    
    def iter_bands(self):
        for band, group in self.df.groupby("bandes", sort=False):
            coords = self.parse_band(str(band))
            if coords is None or len(coords) != 3:
                continue
            services = [
                str(s).strip()
                for s in group["services"]
                if isinstance(s, str) and str(s).strip()
            ]
            if services:
                yield str(band), coords[:2], services, self._get_group_services(services), coords[2], group
        
    def _get_group_services(self, services):

        group_services = {}

        for service in services:
            service_norm = self.normalize(service)
            matched = False

            # On parcourt tous les groupes sauf "autres"
            for group in self.GROUP_SERVICES[:-1]:
                group_norm = self.normalize(group)

                if group_norm in service_norm:
                    group_services[group] = self.GROUP_COLOR_SERVICE[group]
                    matched = True

            # 🔥 Si aucun groupe trouvé → classé dans "autres"
            if not matched:
                group_services["autres"] = self.GROUP_COLOR_SERVICE["autres"]

        return group_services

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
        self,
        x_start,
        y,
        width,
        height,
        color_left,
        color_right,
        zorder=1,
        resolution=400,
    ):
        """
        Dessine un rectangle avec gradient horizontal.
        """

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
        Calcule la position X du texte à l'intérieur d'un rectangle
        selon la largeur/échelle de la bande.
        """
        # fraction à prendre par rapport à la largeur
        # largeur très petite → +2% de décalage
        # largeur moyenne → +1.5%
        # largeur grande → +1%
        frac = 0.02  # base 2%
        
        # on peut adapter dynamiquement selon la largeur
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
        self,
        x,
        y,
        w,
        h,
        title,
        subtitle,
        color_left,
        color_right,
        edgecolor="white",
        linewidth=1.5,
    ):
        # gradient
        self._draw_gradient_band(
            x, y, w, h,
            color_left, 
            color_right,
            zorder=1,
        )

        # bordure
        rect = patches.Rectangle(
            (x, y), w, h,
            fill=False,
            edgecolor=edgecolor,
            linewidth=linewidth,
            zorder=2,
        )
        self.ax.add_patch(rect)


        # titre normal
        self.ax.text(
            self._compute_text_x(x, w),
            y + h * 0.65,
            title,
            ha="left",
            va="center",
            fontsize=55,
            zorder=3,
            color="white"
        )

        # sous-titre bold
        self.ax.text(
            self._compute_text_x(x, w),
            y + h * 0.30,
            subtitle,
            ha="left",
            va="center",
            fontsize=55,
            fontweight="bold",
            zorder=3,
            color="white"
        )
    
    def _auto_text_color(self, hex_color: str) -> str:
        """Retourne noir ou blanc selon luminosité du fond."""

        hex_color = hex_color.lstrip("#")

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # luminance perceptuelle
        luminance = (0.299*r + 0.587*g + 0.114*b)

        return "black" if luminance > 140 else "white"
    
    def render(self, start, end, services, group_services, unity):
        """
        Dessine les bandes de tracer sur l'axe axe
        """
        group_services_keys = list(group_services.keys())
        
        if len(group_services_keys) == 0:
            return
        
        if len(group_services_keys) == 1:
            self._rect(start, self.HEIGHT, self.BASE_Y, end, group_services[group_services_keys[0]])
        
        else:
            nbr_services = len(group_services_keys)
            height = self.HEIGHT / nbr_services
            base_y = self.BASE_Y
            for i in range(nbr_services):
                self._rect(start, height, base_y, end, group_services[group_services_keys[i]])
                base_y += height
                
        # ---------- ESCALIER CYCLIQUE 4 NIVEAUX ----------
        # Ne pas afficher si trop proche du précédent
        # if start - self.last_label_x < self.min_label_gap:
        #     return
        
        min_ratio = 1.15  # ratio d'espacement (ex: 1.3 signifie 30% d'écart minimum)
        # Nouveau test de collision logarithmique
        if self.last_label_x > 0 and (start / self.last_label_x) < min_ratio:
            return

        levels = [0.10, 0.55, 1.10, 1.65, 2.10]  # hauteurs relatives

        level = self.label_index % 5
        offset = levels[level]

        self.label_index += 1

        base_line = self.BASE_Y + self.HEIGHT
        line_height = offset
        text_height = base_line + line_height + 0.05

        # texte
        self.ax.text(
            start,
            text_height,
            f"{self.convert_frequency(start, 'GHz', unity):g}",
            ha="left",
            va="bottom",
            fontsize=40,
            # rotation=45
        )

        # trait vertical
        self.ax.plot(
            [start, start],
            [base_line, base_line + line_height],
            linewidth=1,
            linestyle=":",
            color="#555555"
        )
        # Mettre à jour la dernière position
        self.last_label_x = start
    
    def render_band(self):
        min_x = float("inf")
        max_x = float("-inf")

        for band, coords, services, group_services, unity, group in self.iter_bands():
            start, end = coords
            if unity != "GHz":
                start = self.convert_frequency(start, unity, "GHz")
                end = self.convert_frequency(end, unity, "GHz")
            
            min_x = min(min_x, start)
            max_x = max(max_x, end)
            self.render(start, end, services, group_services, unity)
        return min_x, max_x
    
    def render_headers_band(self, max_x):
        headers_band = {
            "Bande VLF": {"title": "8.3-30 KHz", "freq": [self.convert_frequency(8.3, "KHz", "GHz"), self.convert_frequency(30, "KHz", "GHz")]},
            "Bande LF": {"title": "30-300 KHz", "freq": [self.convert_frequency(30, "KHz", "GHz"), self.convert_frequency(300, "KHz", "GHz")]},
            "Bande MF": {"title": "300 KHz-3 MHz", "freq": [self.convert_frequency(300, "KHz", "GHz"), self.convert_frequency(3, "MHz", "GHz")]},
            "Bande HF": {"title": "3-30 MHz", "freq": [self.convert_frequency(3, "MHz", "GHz"), self.convert_frequency(30, "MHz", "GHz")]},
            "Bande UHF": {"title": "30-300 MHz", "freq": [self.convert_frequency(30, "MHz", "GHz"), self.convert_frequency(300, "MHz", "GHz")]},
            "Bande VHF": {"title": "300-3 GHz", "freq": [self.convert_frequency(300, "MHz", "GHz"), self.convert_frequency(3, "GHz", "GHz")]},
            "Bande VLH": {"title": "3-30 GHz", "freq": [self.convert_frequency(3, "GHz", "GHz"), self.convert_frequency(30, "GHz", "GHz")]},
            "Bande LH": {"title": "30-300 GHz", "freq": [self.convert_frequency(30, "GHz", "GHz"), max_x]}
        }
        
        for band, band_info in headers_band.items():
            title = band_info["title"]
            freq_min, freq_max = band_info["freq"]
            color_left, color_right = self.HEADER_COLORS[band]
            self._draw_labeled_rectangle(
                freq_min, self.Y_BAR,
                freq_max-freq_min,
                self.HEIGHT_BAR,
                f"{band}",
                f"{title}",
                color_left,
                color_right,
            )
            
            # trait vertical
            if freq_min != headers_band["Bande VLF"]["freq"][0]:
                self.ax.plot(
                [freq_min, freq_min],
                [self.BASE_Y+self.HEIGHT, self.Y_BAR],
                linewidth=2,
                linestyle="-",
                color="#141414"
            )
            
    def render_legende(
        self,
        rows: int = 4,
        width: float = 0.07,
        fontsize: int = 8,
        position_x: float = 0.05,
    ):
        """
        Affiche la légende des services.

        Parameters
        ----------
        rows : nombre de lignes par colonne
        width : largeur des rectangles (coordonnées axe 0→1)
        fontsize : taille du texte
        position_x : position X de départ (0→1)
        """

        BOX_W = width
        BOX_H = 0.04
        GAP_X = 0.005
        GAP_Y = 0.05

        start_x = position_x
        start_y = 0.05

        col = 0
        row = 0

        for service, color in self.GROUP_COLOR_SERVICE.items():

            # position grille
            x = start_x + col * (BOX_W + GAP_X)
            y = start_y + row * GAP_Y

            # === rectangle ===
            rect = patches.Rectangle(
                (x, y),
                BOX_W,
                BOX_H,
                transform=self.ax.transAxes,  # non affecté par log scale
                facecolor=color,
                edgecolor="white",
                linewidth=0.6,
                zorder=50,
                clip_on=False,
            )
            self.ax.add_patch(rect)

            # couleur texte automatique
            text_color = self._auto_text_color(color)

            # === texte ===
            self.ax.text(
                x + BOX_W * 0.5,
                y + BOX_H * 0.5,
                service,
                transform=self.ax.transAxes,
                ha="center",
                va="center",
                fontsize=fontsize,
                color=text_color,
                weight="bold",
                zorder=51,
            )

            # gestion grille
            row += 1
            if row >= rows:
                row = 0
                col += 1  
       
    def render_assignees_band(self, min_x, max_x):
        """
        Place les logos à gauche et à droite des bandes sans déformer le diagramme.
        """

        # Conversion Y DATA → AXES
        def data_to_axes(y):
            _, y_axes = self.ax.transAxes.inverted().transform(
                self.ax.transData.transform((0, y))
            )
            return y_axes

        for i in range(self.BASE_Y+self.HEIGHT+4, self.BASE_Y+self.HEIGHT+12, 2):
            # Cadres bande en DATA
            self.ax.hlines(i, min_x, max_x, color=self.ASSIGNEE_COLOR, linewidth=3)
            self.ax.hlines(i+1, min_x, max_x, color=self.ASSIGNEE_COLOR, linewidth=3)
            self.ax.vlines(min_x, i, i+1, color=self.ASSIGNEE_COLOR, linewidth=3)
            self.ax.vlines(max_x, i, i+1, color=self.ASSIGNEE_COLOR, linewidth=3)

        # Placer logos en AXES coords pour ne pas déformer le diagramme
        # y_axes = data_to_axes(16)
        # for assignee, img in self.ASSIGNEE_LOGO.items():
        #     # gauche
        #     self._draw_logo(img, x=0.01, y=y_axes, height=0.05, text=assignee, fontsize=40)
        #     # droite
        #     self._draw_logo(img, x=0.88, y=y_axes, height=0.05, text=assignee, fontsize=40)
        #     y_axes += 0.08          
           
    def show(self):
        print("rendering...")
        min_x,max_x = self.render_band()
        self.render_headers_band(max_x)
        self.render_legende(fontsize=60,position_x=0)
        self.render_legende(fontsize=60,position_x=0.88)
        self.render_assignees_band(min_x=min_x,max_x=max_x)
        
        if self.convert_frequency(1, "KHz", "GHz") < min_x:
            min_x = self.convert_frequency(1, "KHz", "GHz")
        
        if 3300 > max_x:
            max_x = 3500
        
        self.ax.set_xlim(
            float(min_x) if min_x is not None else -float('inf'),
            float(max_x) if max_x is not None else float('inf')
        )
            
        self.ax.set_ylim(0, 38)
        self.ax.set_xscale('log')
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_xticks([])
        self.ax.xaxis.set_minor_locator(plt.NullLocator())
        self.ax.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
        
        self.ax.set_yticks([])
        self.fig.savefig("tanares.png", bbox_inches="tight", dpi=150)
        print(f"Sauvegardé......")
        plt.close(self.fig)
        plt.subplots_adjust(bottom=0.15)
        plt.show()

