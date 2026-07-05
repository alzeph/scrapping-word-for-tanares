# TANARES — Générateur de diagramme du spectre

Extrait les données d'allocation des bandes de fréquences du TANARES (Tableau
National de Répartition des Bandes de Fréquences de Côte d'Ivoire), à partir
de documents Word, et génère une image de type diagramme du spectre
(similaire aux planches ITU/nationales), avec un code couleur par groupe de
services.

## Sommaire

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
  - [Commande courte `tanares`](#commande-courte-tanares)
  - [Options disponibles](#options-disponibles)
  - [Exemples](#exemples)
- [Structure du projet](#structure-du-projet)
- [Pipeline](#pipeline)

## Prérequis

- Python 3.11 (voir `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) pour la gestion des dépendances et de
  l'environnement virtuel

## Installation

```bash
# Clone du dépôt
git clone https://github.com/alzeph/scrapping-word-for-tanares.git
cd scrapping-word-for-tanares

# Installe les dépendances dans .venv et construit le paquet du projet
# (nécessaire pour que la commande `tanares` soit disponible)
uv sync
```

`uv sync` :
- crée/actualise l'environnement virtuel `.venv` ;
- installe les dépendances listées dans `pyproject.toml` (`matplotlib`,
  `pandas`, `python-docx`, etc.) ;
- installe le projet lui-même en mode éditable, ce qui enregistre le point
  d'entrée `tanares` (voir `[project.scripts]` dans `pyproject.toml`).

Les fichiers `.docx` sources (`TANARES.docx`, `TANARES-kHz.docx`,
`TANARES-MHz.docx`, `TANARES-GHz.docx`) doivent être présents dans
`scrapping_docs/asserts/` (déjà fournis dans le dépôt).

## Utilisation

### Commande courte `tanares`

Une fois `uv sync` exécuté, la commande `tanares` est disponible dans
l'environnement `uv` et pointe vers le pipeline complet
(`scrapping_docs/new_version/main.py:main`) :

```bash
uv run tanares [options]
```

C'est un raccourci équivalent à :

```bash
uv run python -m scrapping_docs.new_version.main [options]
```

### Options disponibles

| Option               | Type   | Défaut         | Description |
|----------------------|--------|----------------|--------------|
| `--min`              | texte  | *(aucune)*     | Borne basse de l'intervalle à tracer, ex. `10KHz`, `100MHz`. Sans borne, l'intervalle est ouvert vers le bas. |
| `--max`              | texte  | *(aucune)*     | Borne haute de l'intervalle à tracer, ex. `1000000KHz`, `3GHz`. Sans borne, l'intervalle est ouvert vers le haut. |
| `--output`           | chemin | `tanares.png`  | Chemin du fichier image de sortie. |
| `--vertical-margin`  | float  | `6` (pouces)   | Marge verticale ajoutée en haut/bas de l'image exportée. Sans valeur, la marge par défaut historique est conservée. |
| `--skip-extract`     | flag   | désactivé      | Ne relit pas les `.docx` sources : réutilise les CSV déjà présents dans `scrapping_docs/new_version/output/`. Utile pour itérer rapidement sur le rendu sans relancer l'extraction. |

### Exemples

Génération complète (extraction + rendu), sortie par défaut `tanares.png` :

```bash
uv run tanares
```

Ne tracer que la bande HF à VHF, avec une marge verticale plus large, sans
relire les `.docx` (réutilise les CSV déjà extraits) :

```bash
uv run tanares --min 3MHz --max 3GHz --vertical-margin 10 --skip-extract --output spectre-hf-vhf.png
```

Régénérer uniquement l'extraction puis le rendu avec un nom de fichier dédié :

```bash
uv run tanares --output tanares-2026.png
```

## Structure du projet

```
scrapping_docs/
├── asserts/                    # .docx sources + logos des affectataires
│   ├── TANARES.docx            # document global (renvois/footnotes numérotés)
│   ├── TANARES-kHz.docx
│   ├── TANARES-MHz.docx
│   ├── TANARES-GHz.docx
│   └── logo/
└── new_version/                # implémentation active du pipeline
    ├── main.py                 # point d'entrée CLI (argparse) — cible de `tanares`
    ├── models/
    │   ├── extract_data.py     # lecture des .docx, extraction bande/services/renvois
    │   ├── frequency.py        # parsing/normalisation/conversion des fréquences
    │   ├── band_repository.py  # chargement des CSV, filtrage par intervalle
    │   ├── services.py         # regroupement des services par couleur
    │   └── tracer.py           # rendu matplotlib du diagramme (BandeTracer)
    ├── tools/
    │   └── cleans.py           # helpers de nettoyage de texte partagés
    └── output/                 # CSV générés par l'extraction (kHz/MHz/GHz)
```

## Pipeline

1. **Extraction** (`ExtractData`) : lit chaque document Word par unité
   (`TANARES-kHz.docx`, `TANARES-MHz.docx`, `TANARES-GHz.docx`) ainsi que le
   document global `TANARES.docx` (paragraphes de renvois numérotés, ex.
   `5.54`). Pour chaque ligne de tableau, extrait la bande, les services et
   les renvois associés, puis écrit un CSV par unité dans
   `scrapping_docs/new_version/output/`.

2. **Chargement** (`BandRepository`) : concatène les CSV, parse chaque bande
   (`"37,5–38,25-MHz"` → bornes + unité), convertit en GHz et applique le
   filtrage optionnel sur l'intervalle `--min`/`--max`.

3. **Rendu** (`BandeTracer`) : dessine une figure `matplotlib` large — une
   barre colorée par bande (couleur = groupe de services dominant), des
   sous-barres empilées si plusieurs groupes de services coexistent sur une
   bande, un axe des fréquences en échelle logarithmique, des en-têtes de
   familles de bandes (VLF → LH) en dégradé, et une légende des groupes de
   services. Sauvegarde le résultat dans le fichier passé à `--output`.
