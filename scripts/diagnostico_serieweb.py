# -*- coding: utf-8 -*-
"""Diagnóstico de SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx"""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "data" / "raw" / "SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx"

print("=" * 90)
print(f"ARCHIVO: {RUTA.name}")
print("=" * 90)

xl = pd.ExcelFile(RUTA)
print(f"Hojas ({len(xl.sheet_names)}): {xl.sheet_names}")
print()

for hoja in xl.sheet_names:
    raw = pd.read_excel(RUTA, sheet_name=hoja, header=None, nrows=15)
    print(f"--- Hoja '{hoja}' (primeras 15 filas) ---")
    print(raw.iloc[:, :8].to_string())
    print()

# Ahora ver qué devuelve regional.cargar_salario
print("=" * 90)
print("regional.cargar_salario('nivel') -> La Rioja")
print("=" * 90)
import sys
sys.path.insert(0, str(RAIZ))
from src import regional

df = regional.cargar_salario("nivel")
print(f"Shape total: {df.shape}")
print(f"Columnas: {df.columns.tolist()}")
print()

# Jurisdicciones únicas
if "jurisdiccion" in df.columns:
    print("Jurisdicciones únicas:")
    for j in sorted(df["jurisdiccion"].astype(str).unique()):
        print(f"  - '{j}'")
    print()

# Filtrar La Rioja y ver rango
prov = df[df["jurisdiccion"].astype(str).str.contains("La Rioja", case=False, na=False)].copy()
print(f"Filas La Rioja: {len(prov)}")

prov["fecha"] = pd.to_datetime(prov["fecha"], errors="coerce")
print(f"Rango: {prov['fecha'].min()} -> {prov['fecha'].max()}")
print()

# Ver últimos 12 meses
print("Últimos 12 registros de La Rioja:")
print(prov.sort_values("fecha").tail(12).to_string(index=False))
print()

# Ver específicamente dic-2024, nov-2024, mar-2026
for objetivo in ("2024-12", "2024-11", "2026-03", "2026-01"):
    mask = prov["fecha"].astype(str).str.startswith(objetivo)
    print(f"{objetivo}: {mask.sum()} filas")
    if mask.any():
        print(prov[mask].to_string(index=False))
    print()
    
