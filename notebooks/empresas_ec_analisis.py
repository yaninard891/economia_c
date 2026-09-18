"""
Análisis de Empresas de la Economía del Conocimiento — La Rioja
================================================================
Definición AFIP-DGIP (8 códigos CIIU)

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
    cargar_ec,
    serie_ec,
    por_bloque,
    por_codigo,
    participacion_total,
    resumen,
    benchmark_provincias,
    exportar_excel_ec,
    CIIU_EC,
    ACTIVIDADES_AFIP,
    BLOQUES,
)


# --- Configuración ---------------------------------------------------------
ANIO_FOCO = 2024
OUT_EC = Path("data/processed/empresas_ec_rioja.xlsx")

print("=" * 72)
print(f"  Empresas EC — La Rioja (definición AFIP-DGIP)")
print("=" * 72)

# --- Carga -----------------------------------------------------------------
df = cargar_ec()
print(f"Filas: {len(df)} | años: {sorted(df['anio'].unique())}")
print(f"CIIU EC: {sorted(CIIU_EC.keys())}")

# --- Equivalencia AFIP ↔ CIIU ---------------------------------------------
print(f"\n--- Equivalencia AFIP ↔ CIIU ---")
for ciiu, afip in ACTIVIDADES_AFIP.items():
    print(f"  AFIP {afip:14s} → CIIU {ciiu}  ({CIIU_EC[ciiu]})")

# --- Serie anual -----------------------------------------------------------
print(f"\n--- Serie anual EC ---")
s = serie_ec(df)
print(s.to_string(index=False))

# --- Por bloque ------------------------------------------------------------
print(f"\n--- Por bloque temático ---")
bloques = por_bloque(df)
print(bloques.to_string(index=False))

# --- Por código CIIU -------------------------------------------------------
print(f"\n--- Por código CIIU (ancho) ---")
cod = por_codigo(df)
print(cod.to_string())

# --- Participación sobre total provincial ---------------------------------
print(f"\n--- Participación EC sobre total provincial ---")
part = participacion_total(df)
print(part.to_string(index=False))

# --- Detalle del año foco --------------------------------------------------
print(f"\n--- Detalle {ANIO_FOCO} ---")
df_foco = df[df["anio"] == ANIO_FOCO].copy()

# Agregar bloque
def _get_bloque(ciiu):
    for nombre, codigos in BLOQUES.items():
        if ciiu in codigos:
            return nombre
    return "Otros"

df_foco["bloque"] = df_foco["ciiu"].apply(_get_bloque)
print(df_foco[["ciiu", "actividad", "bloque", "empresas"]].to_string(index=False))
print(f"\n  Total {ANIO_FOCO}: {df_foco['empresas'].sum(min_count=1):.0f}")

# --- Benchmark 9 provincias ------------------------------------------------
print(f"\n--- Benchmark {ANIO_FOCO} (intensidad EC ‰) ---")
bench = benchmark_provincias(str(ANIO_FOCO))
print(bench.to_string(index=False))

# --- Resumen ejecutivo -----------------------------------------------------
print(f"\n--- Resumen ejecutivo ---")
r = resumen(df)
for k, v in r.items():
    if k != "serie":
        print(f"  {k}: {v}")

# --- Exportar Excel --------------------------------------------------------
print()
exportar_excel_ec(OUT_EC, df)

print("\n" + "=" * 72)
print("  LISTO")
print("=" * 72)