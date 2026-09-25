# -*- coding: utf-8 -*-
"""Compara empleo EC con definición núcleo vs. completa (La Rioja)."""
from pathlib import Path
import sys

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.empleo import cargar_empleo_sector_provincia
from src import regional

# --- Definiciones ---------------------------------------------------------
NUCLEO   = {"7210", "7220", "7290"}
COMPLETO = {"7210", "7220", "7250", "7290",
            "7300", "7421", "7430", "7499"}
PROV = "La Rioja"

# --- Cargar 4dig una vez --------------------------------------------------
print("Cargando archivo 4dig...")
df4 = cargar_empleo_sector_provincia(PROV, nivel="4dig", solo_nivel="grupo")
df4 = df4[df4["fecha"].dt.year >= 2018].copy()  # desde 2018

# --- Serie anual por definición ------------------------------------------
def serie_anual(codigos):
    sub = df4[df4["codigo"].isin(codigos)].copy()
    presentes = sorted(sub["codigo"].unique())
    faltantes = sorted(codigos - set(presentes))
    por_trim = (sub.groupby("fecha", as_index=False)["puestos"].sum())
    por_trim["anio"] = por_trim["fecha"].dt.year
    out = (por_trim.groupby("anio", as_index=False)["puestos"].mean()
           .rename(columns={"puestos": "empleo"}))
    return out, presentes, faltantes

nucleo, pres_n, falt_n = serie_anual(NUCLEO)
completo, pres_c, falt_c = serie_anual(COMPLETO)

print(f"\nNUCLEO   -> con dato: {pres_n}, faltantes: {falt_n}")
print(f"COMPLETO -> con dato: {pres_c}, faltantes: {falt_c}")

# --- Empleo total provincial (miles -> puestos) --------------------------
emp_total = regional.cargar_empleo("desestacionalizada")
emp_total = emp_total[emp_total["jurisdiccion"] == "La Rioja"].copy()
emp_total["fecha"] = pd.to_datetime(emp_total["fecha"])
emp_total["anio"] = emp_total["fecha"].dt.year
emp_total_anual = (emp_total[emp_total["anio"] >= 2018]
                   .groupby("anio", as_index=False)["valor"].mean()
                   .rename(columns={"valor": "emp_total_miles"}))
emp_total_anual["emp_total"] = emp_total_anual["emp_total_miles"] * 1000

# --- Combinar -------------------------------------------------------------
m = nucleo.rename(columns={"empleo": "empleo_nucleo"}).merge(
    completo.rename(columns={"empleo": "empleo_completo"}), on="anio", how="outer"
).merge(emp_total_anual[["anio", "emp_total"]], on="anio", how="left")

m["share_nucleo"]   = m["empleo_nucleo"]   / m["emp_total"] * 100
m["share_completo"] = m["empleo_completo"] / m["emp_total"] * 100

# --- Índices base 2022=100 -----------------------------------------------
base = m[m["anio"] == 2022].iloc[0]
m["idx_nucleo"]   = m["empleo_nucleo"]   / base["empleo_nucleo"]   * 100
m["idx_completo"] = m["empleo_completo"] / base["empleo_completo"] * 100

# --- Imprimir ------------------------------------------------------------
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)

print("\n" + "=" * 100)
print("EMPLEO EC — La Rioja — Núcleo vs. Completo")
print("=" * 100)
print(m[["anio", "empleo_nucleo", "empleo_completo",
         "emp_total", "share_nucleo", "share_completo"]].round(3).to_string(index=False))

print("\n" + "=" * 100)
print("ÍNDICES 2022=100")
print("=" * 100)
print(m[["anio", "idx_nucleo", "idx_completo"]].round(1).to_string(index=False))

print("\n" + "=" * 100)
print("RATIO NÚCLEO / COMPLETO (peso del núcleo informático dentro del EC completo)")
print("=" * 100)
m["ratio_nucleo_sobre_completo"] = m["empleo_nucleo"] / m["empleo_completo"] * 100
print(m[["anio", "empleo_nucleo", "empleo_completo",
         "ratio_nucleo_sobre_completo"]].round(2).to_string(index=False))