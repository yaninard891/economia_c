# -*- coding: utf-8 -*-
"""
Genera data/processed/empleo_ec_rioja.xlsx con el empleo EC de La Rioja,
alineado a los CIIU 4 dígitos del núcleo informático {7210, 7220, 7290}.

Reutiliza cargar_empleo_sector_provincia() de src.empleo.

Si algún CIIU del núcleo no tiene dato, se reporta pero no rompe el cálculo.
"""
from pathlib import Path
import sys

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.empleo import cargar_empleo_sector_provincia  # noqa: E402

# --- Definiciones alineadas con prima_salarial.py -------------------------
CIIU_NUCLEO_INFORMATICO = {"7210", "7220", "7290"}
CIIU_NUCLEO_AMPLIO      = {"7210", "7220", "7290", "7300", "7430"}
CIIU_COMPLETO           = {"7210", "7220", "7250", "7290",
                           "7300", "7421", "7430", "7499"}

MAPA_DEFINICIONES = {
    "nucleo":   CIIU_NUCLEO_INFORMATICO,
    "amplio":   CIIU_NUCLEO_AMPLIO,
    "completo": CIIU_COMPLETO,
}

SALIDA = RAIZ / "data" / "processed" / "empleo_ec_rioja.xlsx"
PROV = "La Rioja"


def _cargar_4dig(prov=PROV):
    """Carga el archivo 4-dig una sola vez y devuelve el DataFrame."""
    return cargar_empleo_sector_provincia(prov, nivel="4dig", solo_nivel="grupo")


def empleo_ec_por_anio(df=None, prov=PROV, definicion="nucleo") -> pd.DataFrame:
    """
    Serie anual de empleo EC (promedio de los 4 trimestres).

    - nivel="4dig" filtra los códigos CIIU a 4 dígitos.
    - Los CIIU del núcleo se suman trimestre a trimestre.
    - Después se promedia por año.
    """
    codigos = MAPA_DEFINICIONES[definicion]

    if df is None:
        df = _cargar_4dig(prov)

    df = df[df["codigo"].isin(codigos)].copy()

    # Diagnóstico: qué códigos del núcleo faltan
    presentes = set(df["codigo"].unique())
    faltantes = sorted(codigos - presentes)
    if faltantes:
        print(f"[!] CIIU sin dato en el archivo 4-dig: {faltantes}")
        print(f"    (el cálculo se hace con: {sorted(presentes)})")
    print()

    # Suma trimestre a trimestre
    por_trim = (df.groupby("fecha", as_index=False)["puestos"].sum()
                .rename(columns={"puestos": "empleo_trim"}))
    por_trim["anio"] = por_trim["fecha"].dt.year

    # Promedio por año
    serie = (por_trim.groupby("anio", as_index=False)["empleo_trim"].mean()
             .rename(columns={"empleo_trim": "empleo_ec_prom"})
             .sort_values("anio")
             .reset_index(drop=True))
    return serie


def empleo_por_ciiu(df=None, prov=PROV, definicion="completo",
                    anio=None, trimestre=None) -> pd.DataFrame:
    """Empleo por CIIU para un trimestre puntual (para gráficos de barras)."""
    codigos = MAPA_DEFINICIONES[definicion]

    if df is None:
        df = _cargar_4dig(prov)

    df = df[df["codigo"].isin(codigos)].copy()

    if anio is None:
        anio = int(df["fecha"].dt.year.max())
    df = df[df["fecha"].dt.year == anio].copy()

    if trimestre is None:
        trimestre = int(df["fecha"].dt.quarter.max())
    df = df[df["fecha"].dt.quarter == trimestre].copy()

    return (df[["codigo", "rama", "puestos", "fecha"]]
            .sort_values("puestos", ascending=False)
            .reset_index(drop=True))


def exportar(definicion="nucleo") -> Path:
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    serie = empleo_ec_por_anio(definicion=definicion)
    serie.to_excel(SALIDA, index=False)
    print(f"[OK] Exportado: {SALIDA}")
    print(f"     Definicion: {definicion}")
    print(f"     Filas: {len(serie)}")
    return SALIDA


# --- Ejecución directa ----------------------------------------------------
if __name__ == "__main__":
    print("=== Empleo EC — La Rioja (CIIU 4 digitos) ===\n")

    df4 = _cargar_4dig()

    print("--- Empleo por CIIU (ultimo trimestre disponible) ---")
    df_ciiu = empleo_por_ciiu(df=df4, definicion="completo")
    print(df_ciiu.to_string(index=False))

    print("\n--- Serie anual: núcleo (7210+7220+7290) ---")
    serie = empleo_ec_por_anio(df=df4, definicion="nucleo")
    print(serie.tail(10).to_string(index=False))

    print("\n--- Exportando Excel (núcleo) ---")
    exportar(definicion="nucleo")
    print("\n[OK] Listo.")