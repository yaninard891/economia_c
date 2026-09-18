"""
Empresas EC — AFIP-DGIP — La Rioja — 2022, 2024, 2025
======================================================
Ejecutar desde la raíz del proyecto:
    python notebooks/empresas_ec_2022_2025.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if Path.cwd().name == "notebooks":
    os.chdir(Path.cwd().parent)
sys.path.insert(0, str(Path.cwd()))

from src.empresas_ec import (
    cargar_ec,
    serie_ec,
    por_bloque,
    por_codigo,
    participacion_total,
    benchmark_provincias,
    exportar_excel_ec,
    CIIU_EC,
    BLOQUES,
)

ANIOS = [2022, 2024, 2025]
OUT = Path("data/processed/empresas_ec_rioja_2022_2025.xlsx")

print("=" * 78)
print("  Empresas EC — AFIP-DGIP — La Rioja — 2022/2024/2025")
print("=" * 78)

# --- Carga ----------------------------------------------------------------
df = cargar_ec()
anios_disponibles = sorted(df["anio"].unique().tolist())
ANIOS = [a for a in ANIOS if a in anios_disponibles]
print(f"Años a analizar: {ANIOS}\n")

# --- 1. Total empresas provincia + EC + share -----------------------------
print("--- 1. Total provincia vs EC ---")
comp = participacion_total(df)
comp = comp[comp["anio"].isin(ANIOS)].reset_index(drop=True)
comp = comp.rename(columns={
    "total_ec": "empresas_ec",
    "total_provincial": "total_provincia",
    "participacion_pct": "share_pct",
})
comp["var_ec_abs"] = comp["empresas_ec"].diff()
comp["var_ec_pct"] = (comp["empresas_ec"].pct_change() * 100).round(2)
comp["var_tot_abs"] = comp["total_provincia"].diff()
comp["var_tot_pct"] = (comp["total_provincia"].pct_change() * 100).round(2)
print(comp.to_string(index=False))

# --- 2. Detalle por bloque temático ---------------------------------------
print("\n--- 2. Detalle por bloque ---")
bloques = por_bloque(df)
bl_pivot = (bloques[bloques["anio"].isin(ANIOS)]
            .pivot_table(index="bloque", columns="anio",
                         values="empresas", aggfunc="sum")
            .fillna(0).astype(int))
if len(ANIOS) >= 2:
    p, u = ANIOS[0], ANIOS[-1]
    bl_pivot["var_abs"] = bl_pivot[u] - bl_pivot[p]
    bl_pivot["var_pct"] = (
        (bl_pivot[u] / bl_pivot[p].replace(0, np.nan) - 1) * 100
    ).round(1)
    bl_pivot = bl_pivot.sort_values(u, ascending=False)
print(bl_pivot.to_string())

# --- 3. Detalle por código CIIU -------------------------------------------
print("\n--- 3. Detalle por CIIU ---")
cod = por_codigo(df)
cod_sel = cod[[c for c in cod.columns if c in ANIOS]].fillna(0).astype(int)
if len(ANIOS) >= 2:
    p, u = ANIOS[0], ANIOS[-1]
    cod_sel["var_abs"] = cod_sel[u] - cod_sel[p]
    cod_sel["var_pct"] = (
        (cod_sel[u] / cod_sel[p].replace(0, np.nan) - 1) * 100
    ).round(1)
    cod_sel = cod_sel.sort_values(u, ascending=False)

# Agregar descripción legible
cod_sel = cod_sel.reset_index()
cod_sel["descripcion"] = cod_sel["ciiu"].map(CIIU_EC)
cod_sel = cod_sel.set_index(["ciiu", "descripcion"])
print(cod_sel.to_string())

# --- 4. Benchmark provincias (3 años) -------------------------------------
print("\n--- 4. Benchmark provincias (intensidad EC ‰) ---")
bench_frames = []
for a in ANIOS:
    b = benchmark_provincias(str(a))
    b["anio"] = a
    bench_frames.append(b)
bench_all = pd.concat(bench_frames, ignore_index=True)

bench_pivot = (bench_all.pivot(index="provincia", columns="anio",
                               values="intensidad_pm")
               .fillna(0).round(2))
if len(ANIOS) >= 2:
    p, u = ANIOS[0], ANIOS[-1]
    bench_pivot["var_pp"] = (bench_pivot[u] - bench_pivot[p]).round(2)
    bench_pivot = bench_pivot.sort_values(u, ascending=False)
print(bench_pivot.to_string())

# --- 5. Exportar ----------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    comp.to_excel(w, sheet_name="EC_vs_Total", index=False)
    bl_pivot.to_excel(w, sheet_name="Por_bloque")
    cod_sel.to_excel(w, sheet_name="Por_CIIU")
    bench_pivot.to_excel(w, sheet_name="Benchmark_provincias")
    pd.DataFrame({
        "ciiu": list(CIIU_EC.keys()),
        "descripcion": list(CIIU_EC.values()),
    }).to_excel(w, sheet_name="CIIU_EC", index=False)

print(f"\n[OK] {OUT}")