"""
Análisis de empresas de Economía del Conocimiento (Ley 27.506) — La Rioja
========================================================================
Ejecutar desde la raíz del proyecto:
    python notebooks/empresas_ec_2022_2025.py
"""

import os
import sys
from pathlib import Path

import pandas as pd

if Path.cwd().name == "notebooks":
    os.chdir(Path.cwd().parent)
sys.path.insert(0, str(Path.cwd()))

from src.empresas_ec import (
    cargar_provincia,
    serie_empresas,
    serie_ec,
    detalle_ramas,
    benchmark_provincias,
    filtrar_ec,
    listar_ramas_definicion,
)

RUTA   = Path("data/raw/provinciales_serie_empresas3_2.xlsx")
PROV   = "La Rioja"
ANIOS  = [2022, 2024, 2025]
OUT    = Path("data/processed/empresas_ec_rioja_2022_2025.xlsx")

print("=" * 78)
print(f"  Empresas EC — Ley 27.506 — {PROV} — 2022–2025")
print("=" * 78)

df = cargar_provincia(RUTA, PROV)
anios_disponibles = sorted(df["anio"].dropna().unique())
ANIOS = [a for a in ANIOS if a in anios_disponibles]
print(f"Años a analizar: {ANIOS}\n")

# 1. Total provincia
print("--- 1. Total empresas provincia ---")
tot = serie_empresas(df)
tot = tot[tot["anio"].isin(ANIOS)].reset_index(drop=True)
tot["var_abs"] = tot["total_empresas"].diff()
tot["var_pct"] = (tot["total_empresas"].pct_change() * 100).round(2)
print(tot.to_string(index=False))

# 2. Ley 27.506
print("\n--- 2. Empresas Ley 27.506 ---")
ley = serie_ec(df, "ley_27_506")
ley = ley[ley["anio"].isin(ANIOS)].reset_index(drop=True)
ley["var_abs"] = ley["empresas_ec"].diff()
ley["var_pct"] = (ley["empresas_ec"].pct_change() * 100).round(2)
ley["share_pct"] = (ley["empresas_ec"] / tot["total_empresas"].values * 100).round(2)
print(ley.to_string(index=False))

# 3. Detalle por rama
print("\n--- 3. Detalle por rama (Ley 27.506) ---")
sub = filtrar_ec(df, "ley_27_506")
pivot = (sub[sub["anio"].isin(ANIOS)]
         .pivot_table(index=["rama", "descripcion"], columns="anio",
                      values="empresas", aggfunc="sum")
         .fillna(0).astype(int))
if len(ANIOS) >= 2:
    p, u = ANIOS[0], ANIOS[-1]
    pivot["var_abs"] = pivot[u] - pivot[p]
    pivot["var_pct"] = ((pivot[u] / pivot[p] - 1) * 100).round(1)
    pivot = pivot.sort_values(u, ascending=False)
print(pivot.to_string())

# 4. Benchmark
print("\n--- 4. Benchmark provincias (Ley 27.506) ---")
bench_frames = []
for a in ANIOS:
    b = benchmark_provincias(RUTA, a, "ley_27_506")
    b["anio"] = a
    bench_frames.append(b)
bench_all = pd.concat(bench_frames, ignore_index=True)
bench_pivot = (bench_all.pivot(index="provincia", columns="anio",
                               values="empresas_ec").fillna(0).astype(int))
if len(ANIOS) >= 2:
    p, u = ANIOS[0], ANIOS[-1]
    bench_pivot["var_abs"] = bench_pivot[u] - bench_pivot[p]
    bench_pivot["var_pct"] = ((bench_pivot[u] / bench_pivot[p] - 1) * 100).round(1)
    bench_pivot = bench_pivot.sort_values(u, ascending=False)
print(bench_pivot.to_string())

# 5. Exportar
OUT.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    tot.to_excel(w, sheet_name="Total_provincia", index=False)
    ley.to_excel(w, sheet_name="Ley_27_506", index=False)
    pivot.to_excel(w, sheet_name="Ley_27_506_por_rama")
    bench_pivot.to_excel(w, sheet_name="Benchmark_provincias")
    listar_ramas_definicion("ley_27_506").to_excel(w, sheet_name="Codigos_ley", index=False)
print(f"\n[OK] {OUT}")