"""
Análisis de empresas y Economía del Conocimiento (Ley 27.506) — La Rioja
========================================================================
Ejecutar desde la raíz del proyecto:
    python notebooks/empresas_ec_analisis.py
"""

import os
import sys
from pathlib import Path

if Path.cwd().name == "notebooks":
    os.chdir(Path.cwd().parent)
sys.path.insert(0, str(Path.cwd()))

from src.empresas_ec import (
    cargar_provincia,
    comparar_definiciones,
    detalle_ramas,
    serie_empresas,
    serie_ec,
    benchmark_provincias,
    listar_ramas_definicion,
    exportar_excel_empresas,
    exportar_excel_ec,
    ETIQUETAS,
    DEFINICIONES,
)


# --- Configuración ---------------------------------------------------------
RUTA         = Path("data/raw/provinciales_serie_empresas3_2.xlsx")
PROV         = "La Rioja"
ANIO         = 2024
OUT_EMPRESAS = Path("data/processed/empresas_rioja_analisis.xlsx")
OUT_EC       = Path("data/processed/empresas_ec_rioja.xlsx")


print("=" * 72)
print(f"  Análisis de empresas — {PROV}")
print("=" * 72)


# --- Carga -----------------------------------------------------------------
df = cargar_provincia(RUTA, PROV)
print(f"Filas tidy: {len(df):,} | años: {df['anio'].min()}–{df['anio'].max()}")


# --- Totales por definición (columnas sin prefijo) -------------------------
tabla = comparar_definiciones(df)
fila = tabla.query("anio == @ANIO").iloc[0]

print(f"\n--- Totales {ANIO} ---")
print(f"  Empresas totales provincia:     {fila['total_empresas']}")
for k, etiqueta in ETIQUETAS.items():
    if k in fila.index:
        print(f"  {etiqueta:60s}: {fila[k]}")

tot = fila.get("total_empresas")
ley = fila.get("ley_27_506")
if pd.notna(ley) and pd.notna(tot) and tot > 0:
    print(f"\n  Share Ley 27.506 / total:       {ley / tot * 100:.2f}%")


# --- Detalle Ley 27.506 ----------------------------------------------------
print(f"\n--- Detalle Ley 27.506 — {ANIO} ---")
det_ley = detalle_ramas(df, ANIO, "ley_27_506")
print(det_ley.to_string(index=False))
print(f"\n  Total Ley 27.506: {det_ley['empresas'].sum()}")


# --- Detalle curada (para comparar) ----------------------------------------
print(f"\n--- Detalle curada — {ANIO} ---")
det_cur = detalle_ramas(df, ANIO, "curada")
print(det_cur.to_string(index=False))
print(f"\n  Total curada: {det_cur['empresas'].sum()}")


# --- Benchmark -------------------------------------------------------------
print(f"\n--- Benchmark {ANIO} (Ley 27.506) ---")
bench = benchmark_provincias(RUTA, ANIO, "ley_27_506")
print(bench.to_string(index=False))


# --- Serie Ley 27.506 2015–2024 --------------------------------------------
print(f"\n--- Serie Ley 27.506 2015–{ANIO} ---")
print(serie_ec(df, "ley_27_506").query("anio >= 2015").to_string(index=False))


# --- Serie total empresas 2015–2024 ----------------------------------------
print(f"\n--- Serie total empresas 2015–{ANIO} ---")
print(serie_empresas(df).query("anio >= 2015").to_string(index=False))


# --- Exportar los dos Excel ------------------------------------------------
print()
exportar_excel_empresas(df, ANIO, OUT_EMPRESAS, PROV, ruta_excel=RUTA)
exportar_excel_ec(df, OUT_EC, PROV)


print("\n" + "=" * 72)
print("  LISTO")
print("=" * 72)