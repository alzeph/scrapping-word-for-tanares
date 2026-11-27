import argparse
from pathlib import Path

from scrapping_docs.new_version.models.band_repository import BandRepository
from scrapping_docs.new_version.models.db_repository import DbBandRepository
from scrapping_docs.new_version.models.services import PALETTES
from scrapping_docs.new_version.models.extract_data import ExtractData
from scrapping_docs.new_version.models.frequency import FrequencyInterval
from scrapping_docs.new_version.models.tracer import BandeTracer

BASE_PATH = Path(__file__).resolve().parent  # scrapping_docs/new_version/
ASSERTS_DIR = BASE_PATH.parent / "asserts"  # scrapping_docs/asserts/
OUTPUT_DIR = BASE_PATH / "output"

GLOBAL_DOCX = ASSERTS_DIR / "TANARES.docx"
SOURCE_DOCX = {
    "KHz": ASSERTS_DIR / "TANARES-kHz.docx",
    "MHz": ASSERTS_DIR / "TANARES-MHz.docx",
    "GHz": ASSERTS_DIR / "TANARES-GHz.docx",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Trace le diagramme du spectre TANARES à partir des fichiers Word "
            "sources. Un intervalle optionnel (--min/--max) permet de ne "
            "représenter que les bandes comprises dans cette plage de fréquences."
        )
    )
    parser.add_argument(
        "--min",
        help="Borne basse de l'intervalle, ex. '10KHz', '100MHz'",
    )
    parser.add_argument(
        "--max",
        help="Borne haute de l'intervalle, ex. '1000000KHz', '3GHz'",
    )
    parser.add_argument(
        "--output",
        default="tanares.png",
        help="Chemin du fichier image de sortie (défaut : tanares.png)",
    )
    parser.add_argument(
        "--vertical-margin",
        type=float,
        default=None,
        help=(
            "Marge verticale (en pouces) ajoutée en haut/bas de l'image "
            f"exportée (défaut : {BandeTracer.MARGIN_INCHES:g})"
        ),
    )
    parser.add_argument(
        "--db-csv",
        help=(
            "CSV exporté depuis la base TANARES (une ligne par allocation). "
            "Remplace la lecture des .docx et active les lignes d'affectataires."
        ),
    )
    parser.add_argument(
        "--palette",
        choices=PALETTES,
        default="anfr",
        help=(
            "Couleurs des bandes : 'anfr' = 12 familles de services (défaut), "
            "'services' = couleur propre de chaque service (base uniquement)"
        ),
    )
    parser.add_argument(
        "--logos-dir",
        help="Dossier des logos d'affectataires (noms de fichiers de la colonne assignee_logo)",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help=(
            "Ne pas relire les .docx : réutiliser les CSV déjà présents dans "
            f"{OUTPUT_DIR}"
        ),
    )
    return parser.parse_args()


def extract_all() -> dict[str, str]:
    """
    Relit les .docx sources et régénère les CSV par unité dans output/.
    Retourne les chemins des CSV produits.
    """
    csv_paths = {}
    for unity, path_file in SOURCE_DOCX.items():
        print(f"Extraction {unity} depuis {path_file.name}...")
        extractor = ExtractData(
            path_file=str(path_file),
            unity=unity,
            path_global_file=str(GLOBAL_DOCX),
        )
        csv_paths[unity] = extractor.write_data_in_csv(
            str(OUTPUT_DIR / f"{unity}.csv")
        )
    return csv_paths


def main():
    args = parse_args()

    interval = None
    if args.min or args.max:
        interval = FrequencyInterval.from_texts(args.min, args.max)
        print(f"Intervalle demandé : [{interval.start_ghz:g} ; {interval.end_ghz:g}] GHz")

    assignees = None
    if args.db_csv:
        db_repository = DbBandRepository(args.db_csv)
        records = list(db_repository.iter_bands(interval))
        assignees = db_repository.assignees()
    else:
        if args.palette == "services":
            print("La palette 'services' nécessite --db-csv : palette 'anfr' utilisée.")
            args.palette = "anfr"
        if args.skip_extract:
            csv_paths = {
                unity: str(OUTPUT_DIR / f"{unity}.csv") for unity in SOURCE_DOCX
            }
        else:
            csv_paths = extract_all()
        records = list(BandRepository(csv_paths=csv_paths).iter_bands(interval))

    print(f"{len(records)} bandes à tracer")

    tracer = BandeTracer(
        records,
        interval=interval,
        vertical_margin_inches=args.vertical_margin,
        palette=args.palette,
        assignees=assignees,
        logos_dir=args.logos_dir,
    )
    tracer.save(args.output)


if __name__ == "__main__":
    main()
