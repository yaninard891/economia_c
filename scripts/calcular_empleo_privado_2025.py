"""
Calcula el promedio 2025 del empleo privado formal de La Rioja
y lo divide por el empleo EC.
"""
import pandas as pd
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "data" / "raw" / "SerieWeb_EMPLEO_PRIVADO_FORMAL_provincias.xlsx"

# Cargar el archivo
df = pd.read_excel(RUTA, sheet_name=0, header=None)

# Fila 0: fechas
fechas = pd.to_datetime(df.iloc[0, 1:], errors="coerce")

# Fila 12: La Rioja (miles de puestos)
fila_rioja = df.iloc[12, 1:].astype(float)

# --- Serie completa de La Rioja ---
serie = pd.DataFrame({
    "fecha": fechas.values,
    "empleo_miles": fila_rioja.values,
})
serie = serie.dropna()

# --- Filtrar 2025 ---
serie_2025 = serie[serie["fecha"].dt.year == 2025]

print("=" * 60)
print("EMPLEO PRIVADO FORMAL — LA RIOJA 2025")
print("=" * 60)
print()
for _, row in serie_2025.iterrows():
    mes = row["fecha"].strftime("%b")
    print(f"  {mes}: {row['empleo_miles']:.3f} miles de puestos")

print()

# --- Promedio 2025 ---
promedio_2025 = serie_2025["empleo_miles"].mean()
print(f"Promedio 2025: {promedio_2025:.3f} miles")
print(f"             = {promedio_2025 * 1000:,.0f} puestos".replace(",", "."))
print()

# --- Comparación con EC ---
EMPLEO_EC = 521
NUCLEO = 63.8

print("=" * 60)
print("COMPARACIÓN CON EMPLEO EC")
print("=" * 60)
print()

empleo_total_2025 = promedio_2025 * 1000  # convertir de miles a puestos

proporcion_ec = EMPLEO_EC / empleo_total_2025 * 100
proporcion_nucleo = NUCLEO / empleo_total_2025 * 100

print(f"Empleo EC (definición amplia) 2025:  {EMPLEO_EC} puestos")
print(f"Empleo núcleo informático 2025:      {NUCLEO} puestos")
print(f"Empleo privado formal 2025 (prom):   {empleo_total_2025:,.0f} puestos".replace(",", "."))
print()
print(f"Proporción EC / privado formal:      {proporcion_ec:.2f}%")
print(f"Proporción núcleo / privado formal:  {proporcion_nucleo:.2f}%")