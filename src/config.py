# src/config.py
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_RAW   = ROOT / "data" / "raw"
DATA_PROC  = ROOT / "data" / "processed"
OUT_GRAF   = ROOT / "outputs" / "graficos"
OUT_TABLAS = ROOT / "outputs" / "tablas"
OUT_INF    = ROOT / "outputs" / "informe_final"

for p in (DATA_RAW, DATA_PROC, OUT_GRAF, OUT_TABLAS, OUT_INF):
    p.mkdir(parents=True, exist_ok=True)

# --- IPC ---
FILE_IPC            = DATA_RAW / "sh_ipc_09_26.xls"
FILE_IPC_APERTURAS  = DATA_RAW / "sh_ipc_aperturas.xls"
FILE_IPC_PRECIOS    = DATA_RAW / "sh_ipc_precios_promedio.xls"
FILE_IPC_PROVINCIAL = DATA_RAW / "Series_IPC_Provinciales_webversion.xlsx"

# --- Empresas por provincia (vienen partidas en 3 archivos) ---
FILES_EMPRESAS = [
    DATA_RAW / "provinciales_serie_empresas1_2.xlsx",
    DATA_RAW / "provinciales_serie_empresas2_2.xlsx",
    DATA_RAW / "provinciales_serie_empresas3_2.xlsx",
]
FILE_EMPRESAS_NACIONAL = DATA_RAW / "nacional_serie_empresas_2.xlsx"

# --- Empleo y remuneraciones (los usaremos en Notebook 03) ---
FILE_EMPLEO_ANUAL      = DATA_RAW / "provinciales_serie_empleo_anual_3.xlsx"
FILE_EMPLEO_TRIM_2D    = DATA_RAW / "provinciales_serie_empleo_trimestral_2dig_6.xlsx"
FILE_EMPLEO_TRIM_4D    = DATA_RAW / "provinciales_serie_empleo_trimestral_4dig_7.xlsx"
FILE_REMUN_ANUAL       = DATA_RAW / "provinciales_serie_remuneraciones_anual_3.xlsx"
FILE_REMUN_MENS_2D     = DATA_RAW / "provinciales_serie_remuneraciones_mensual_2dig_8.xlsx"
FILE_REMUN_MENS_4D     = DATA_RAW / "provinciales_serie_remuneraciones_mensual_4dig_7.xlsx"

# --- Dominio ---
PROVINCIA_FOCO = "La Rioja"

PROVINCIAS_BENCHMARK = [
    "CABA", "Córdoba", "Santa Fé", "Mendoza",
    "Tucumán", "Salta", "Neuquén", "San Juan",
]

RAMA_TIC = {
    "64": "Telecomunicaciones",
    "72": "Informática y servicios conexos",
    "73": "Investigación y desarrollo",
    "74": "Servicios profesionales y empresariales",
    "80": "Enseñanza",
    "85": "Salud y servicios sociales",
    "92": "Actividades culturales y de esparcimiento",
}

COLOR_LA_RIOJA = "#C8102E"
COLOR_NOA      = "#1F77B4"
COLOR_NACIONAL = "#333333"