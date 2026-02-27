import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.cm as cm
import matplotlib.colors as mcolors

# ======================
# Lecture du CSV
# ======================
df = pd.read_csv(
    "/Users/admin/cedric/scrapping-file-word/scrapping_docs/output/MHz.csv",
    sep=","
)

# ======================
# Couleurs automatiques par service
# ======================
services_uniques = df["services"].dropna().unique()
cmap = cm.get_cmap("tab20", len(services_uniques))
couleurs = {s: cmap(i) for i, s in enumerate(services_uniques)}

# ======================
# Parse bande
# ======================
def parse_band(band):
    t = band.replace("MHz", "").replace(" ", "").replace("–", "-")
    start, end = t.split("-")
    return float(start.replace(",", ".")), float(end.replace(",", "."))

# ======================
# Texte lisible selon fond
# ======================
def text_color(bg):
    r, g, b, _ = mcolors.to_rgba(bg)
    return "black" if (0.299*r + 0.587*g + 0.114*b) > 0.6 else "white"

# ======================
# Figure LARGE
# ======================
fig, ax = plt.subplots(figsize=(40, 4), dpi=150)
ax.set_ylim(0, 2)
ax.set_yticks([])
ax.set_xlabel("Fréquence (MHz)")

# ======================
# Tracé des bandes
# ======================
grouped = df.groupby("bandes")
band_starts, band_ends = [], []

for band, group in grouped:
    start, end = parse_band(band)
    band_starts.append(start)
    band_ends.append(end)

    services = [s for s in group["services"] if isinstance(s, str)]
    if not services:
        continue

    n = len(services)

    if n == 1:
        ax.add_patch(patches.Rectangle(
            (start, 0), end-start, 1,
            facecolor=couleurs[services[0]]
        ))

    elif n == 2:
        ax.add_patch(patches.Rectangle(
            (start, 0), end-start, 0.5,
            facecolor=couleurs[services[0]]
        ))
        ax.add_patch(patches.Rectangle(
            (start, 0.5), end-start, 0.5,
            facecolor=couleurs[services[1]]
        ))

    else:
        ax.add_patch(patches.Rectangle(
            (start, 0), end-start, 1,
            facecolor=couleurs[services[0]]
        ))
        h = 0.3
        for i, s in enumerate(services[1:]):
            ax.add_patch(patches.Rectangle(
                (start, i*h), end-start, h,
                facecolor=couleurs.get(s, "lightgray")
            ))


ax.set_xlim(min(band_starts), max(band_ends))

plt.show()