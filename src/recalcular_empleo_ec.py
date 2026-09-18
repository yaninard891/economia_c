# src/recalcular_empleo_ec.py
"""Recalcula el empleo EC de La Rioja con la definición AFIP-DGIP (8 CIIU)."""
import sys
import os
import re
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
os.chdir(_RAIZ)
sys.path.insert(0, str(_RAIZ))

import pandas as pd
from src.empresas_ec import CIIU_EC

RAW = _RAIZ / "data" / "raw"
PROCESSED = _RAIZ / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

RUTA_EMPLEO = RAW / "provinciales_serie_empleo_trimestral_4dig_7.xlsx"
HOJA = "La Rioja"

# ============================================================
# Total de empleo privado formal provincial (denominador correcto)
# Fuente: SerieWeb_EMPLEO_PRIVADO_FORMAL_provincias.xlsx
# ============================================================
TOTAL_EMPLEO_PROV = {
    2019: 26894,
    2022: 30125,
    2024: 28008,
    2025: 27047,
    # 2020, 2021 y 2023 sin dato cargado
}

# ============================================================
# 1. Cargar el Excel de empleo trimestral a 4 dígitos
# ============================================================
df = pd.read_excel(RUTA_EMPLEO, sheet_name=HOJA, header=None)

# --- Detectar fila de años ---
fila_anios = None
for i in range(min(20, len(df))):
    fila = df.iloc[i].astype(str)
    if fila.str.contains("2019").any() or fila.str.contains("2020").any():
        fila_anios = i
        break

if fila_anios is None:
    raise ValueError("No se encontró la fila de años en el Excel de empleo.")

print(f"Fila de años detectada: {fila_anios}")

# --- Identificar columnas trimestrales de interés ---
ANIOS_INTERES = ["2019", "2020", "2021", "2022", "2024", "2025"]
columnas_empleo = []
for j in range(len(df.columns)):
    val = str(df.iloc[fila_anios, j]).strip()
    if any(a in val for a in ANIOS_INTERES):
        columnas_empleo.append(j)

print(f"Columnas detectadas: {[str(df.iloc[fila_anios, j]) for j in columnas_empleo]}")

# --- Filtrar filas de los 8 CIIU EC ---
filas_ec = []
for i in range(fila_anios + 1, len(df)):
    try:
        cod = int(float(df.iloc[i, 0]))
    except (ValueError, TypeError):
        continue
    if cod in CIIU_EC:
        filas_ec.append((i, cod))

if not filas_ec:
    raise ValueError("No se encontraron filas de CIIU EC en el Excel de empleo.")

print(f"CIIU EC encontrados: {[c for _, c in filas_ec]}")

# --- Sumar empleo EC por columna trimestral ---
totales_ec = {}
for j in columnas_empleo:
    col_name = str(df.iloc[fila_anios, j]).strip()
    suma = 0.0
    for i, _ in filas_ec:
        try:
            v = float(df.iloc[i, j])
            if pd.notna(v):
                suma += v
        except (ValueError, TypeError):
            pass
    totales_ec[col_name] = suma

# --- Promediar por año ---
serie_anual = {}
for col, val in totales_ec.items():
    match = re.search(r"(19|20)\d{2}", col)
    if not match:
        continue
    anio = match.group(0)
    serie_anual.setdefault(anio, []).append(val)

resultado = []
for anio in sorted(serie_anual.keys()):
    vals = [v for v in serie_anual[anio] if v > 0]
    if not vals:
        continue
    empleo_prom = sum(vals) / len(vals)
    resultado.append({"anio": int(anio), "empleo_ec": round(empleo_prom)})

df_out = pd.DataFrame(resultado)

# ============================================================
# 2. Agregar total provincial y calcular participación
# ============================================================
df_out["total_empleo_prov"] = df_out["anio"].map(TOTAL_EMPLEO_PROV)
df_out["part_%"] = (
    df_out["empleo_ec"] / df_out["total_empleo_prov"] * 100
).round(2)

# ============================================================
# 3. Exportar
# ============================================================
salida = PROCESSED / "empleo_ec_rioja.xlsx"
df_out.to_excel(salida, index=False)

print(f"\n✅ Generado: {salida}")
print("\nEmpleo EC La Rioja (definición AFIP-DGIP):")
print(df_out.to_string(index=False))

print("\n⚠️  Años sin total provincial (2020, 2021, 2023): part_% = NaN")
print("   Completar en TOTAL_EMPLEO_PROV cuando tengas el dato.")