# -*- coding: utf-8 -*-
"""Diagnóstico del archivo de empleo trimestral 4 dígitos (SIPA-OEDE)."""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "data" / "raw" / "provinciales_serie_empleo_trimestral_4dig_7.xlsx"

print("=" * 90)
print(f"ARCHIVO: {RUTA.name}")
print("=" * 90)

xl = pd.ExcelFile(RUTA)
print(f"Hojas ({len(xl.sheet_names)}): {xl.sheet_names}")
print()

# Inspeccionar hoja "La Rioja"
hoja = "La Rioja"
if hoja not in xl.sheet_names:
    print(f"[!] No existe la hoja '{hoja}'. Buscando alternativas...")
    hoja = [h for h in xl.sheet_names if "rioja" in h.lower()][0]
    print(f"    Usando '{hoja}'")

raw = pd.read_excel(RUTA, sheet_name=hoja, header=None)
print(f"Shape: {raw.shape}")
print()

print("--- Primeras 20 filas, primeras 8 columnas ---")
print(raw.iloc[:20, :8].to_string())
print()

print("--- Fila 5 completa (primeras 15 columnas) ---")
if len(raw) > 5:
    print(raw.iloc[5, :15].tolist())
print()

print("--- Fila 6 completa (primeras 15 columnas) ---")
if len(raw) > 6:
    print(raw.iloc[6, :15].tolist())
print()

print("--- Fila 7 completa (primeras 15 columnas) ---")
if len(raw) > 7:
    print(raw.iloc[7, :15].tolist())
print()

# Buscar CIIU 7220, 7290, 7210
print("--- Buscando CIIU 7210/7220/7290 en columna 1 ---")
for idx in range(len(raw)):
    v = raw.iloc[idx, 1]
    try:
        v_int = int(float(v))
    except (ValueError, TypeError):
        continue
    if v_int in (7210, 7220, 7250, 7290):
        print(f"Fila {idx}: CIIU {v_int} -> {raw.iloc[idx, 2]}")
        # Últimos valores no-NaN
        vals = raw.iloc[idx, 3:].dropna()
        if len(vals) > 0:
            print(f"  Primer valor: {vals.iloc[0]} (col {vals.index[0]})")
            print(f"  Último valor: {vals.iloc[-1]} (col {vals.index[-1]})")
            print(f"  Últimos 6: {vals.tail(6).tolist()}")
print()

# Ver primeras 3 columnas del header (fila donde dice "Ramas")
print("--- Filas 0-10, col 0 y 1 ---")
for i in range(min(11, len(raw))):
    print(f"  [{i}] col0={raw.iloc[i, 0]!r:30s}  col1={raw.iloc[i, 1]!r:30s}  col2={raw.iloc[i, 2]!r}")
    