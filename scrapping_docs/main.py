from models.tracer import BandeTracer
from models.tracers import BandeTracers
from models.extract_data import ExtractData


if False:
    extract_data_KHz = ExtractData(
        path_file="/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/TANARES-KHz.docx",
        unity="KHz",
        path_global_file="/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/TANARES.docx",
    )
    extract_data_MHz = ExtractData(
        path_file="/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/TANARES-MHz.docx",
        unity="MHz",
        path_global_file="/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/TANARES.docx",
    )
    extract_data_GHz = ExtractData(
        path_file="/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/TANARES-GHz.docx",
        unity="GHz",
        path_global_file="/Users/admin/cedric/scrapping-file-word/scrapping_docs/asserts/TANARES.docx",
    )

    extract_data_KHz.write_data_in_csv()
    extract_data_MHz.write_data_in_csv()
    extract_data_GHz.write_data_in_csv()

    tracer = BandeTracer(
        csv_path="/Users/admin/cedric/scrapping-file-word/scrapping_docs/output/KHz.csv",
        unity="KHz",
        sep=",",
        )
    tracer.show()

tracers = BandeTracers(
    csv_paths={
        "KHz": "/Users/admin/cedric/scrapping-file-word/scrapping_docs/output/KHz.csv",
        "MHz": "/Users/admin/cedric/scrapping-file-word/scrapping_docs/output/MHz.csv",
        "GHz": "/Users/admin/cedric/scrapping-file-word/scrapping_docs/output/GHz.csv",
    },
    sep=",",
)
tracers.show()
