import unicodedata
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import colorsys

class BandeTracer:
    BASE_Y = 0
    HEIGHT = 1
    
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
        "autres": "#E22624"
    }
    
    def __init__(self, csv_path: str, sep: str = ","):
        self.label_index = 0
        self.fig, self.ax = plt.subplots(figsize=(40, 3), dpi=100)
        self.df = pd.read_csv(csv_path, sep=sep)
        self._clean()
    
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
                .replace("kHz", "")
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
            if coords is None:
                continue
            services = [
                str(s).strip()
                for s in group["services"]
                if isinstance(s, str) and str(s).strip()
            ]
            if services:
                yield str(band), coords, services, self._get_group_services(services)
        
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
            (end - start)*4,
            height,
            facecolor=color,
            zorder=2,
        )
        self.ax.add_patch(rect)
        
    def render(self, start, end, services, group_services):
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
        
        # self.ax.text(start, self.BASE_Y+0.3+ self.HEIGHT + 0.1, f"{start}", ha="left", va="bottom", fontsize=8)
        # self.ax.plot(
        #     [start, start],
        #     [self.BASE_Y + self.HEIGHT, self.BASE_Y + self.HEIGHT + 0.38],
        #     linewidth=1,
        #     linestyle=":",
        #     color="#555555"
        # )
        # ---------- ESCALIER CYCLIQUE 4 NIVEAUX ----------

        levels = [0.15, 0.35, 0.55, 0.75]  # hauteurs relatives

        level = self.label_index % 4
        offset = levels[level]

        self.label_index += 1

        base_line = self.BASE_Y + self.HEIGHT
        line_height = offset
        text_height = base_line + line_height + 0.05

        # texte
        self.ax.text(
            start,
            text_height,
            f"{start}",
            ha="left",
            va="bottom",
            fontsize=6
        )

        # trait vertical
        self.ax.plot(
            [start, start],
            [base_line, base_line + line_height],
            linewidth=1,
            linestyle=":",
            color="#555555"
        )
            
    def show(self):
        min_x = float("inf")
        max_x = float("-inf")

        for band, coords, services, group_services in self.iter_bands():
            print(band, " | ", group_services)
            start, end = coords
            min_x = min(min_x, start)
            max_x = max(max_x, end)
            self.render(start, end, services, group_services)

        self.ax.set_xlim(min_x, max_x)
        self.ax.set_ylim(0, 2)

        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        plt.show()
