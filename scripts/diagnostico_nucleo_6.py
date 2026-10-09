"""
Diagnóstico: ¿qué códigos del núcleo informático tienen dato en SIPA?
Núcleo teórico: 7220, 7210, 7290, 7300, 7430, 7250
"""
import pandas as pd
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "data" / "raw" / "provinciales_serie_empleo_trimestral_4dig_7.xlsx"

# Leer sin header para ver la estructura cruda
df = pd.read_excel(RUTA, sheet_name="La Rioja", header=None)

print("=" * 75)
print("ESTRUCTURA DEL ARCHIVO")
print("=" * 75)
print(f"Dimensiones: {df.shape}")
print()

# Mostrar las primeras 12 filas, primeras 6 columnas
print("Primeras 12 filas × 6 columnas:")
print(df.iloc[:12, :6].to_string())
print()

# Buscar dónde están los códigos CIIU (columna 0 probablemente)
print("=" * 75)
print("BÚSQUEDA DE CÓDIGOS DEL NÚCLEO")
print("=" * 75)

NUCLEO_6 = [7220, 7210, 7290, 7300, 7430, 7250]

# Convertir la columna 0 a string, manejando NaN
col0 = df.iloc[:, 0].astype(str)

for codigo in NUCLEO_6:
    # Buscar el código como número al inicio de la celda
    mascara = col0.str.startswith(str(codigo))
    filas = df[mascara]
    if len(filas) > 0:
        idx = filas.index[0]
        nombre = str(df.iloc[idx, 1])[:70] if df.shape[1] > 1 else "—"
        print(f"  ✅ CIIU {codigo}: fila {idx} → {nombre}")
    else:
        print(f"  ❌ CIIU {codigo}: NO ENCONTRADO")

print()
print("=" * 75)
print("PRIMERAS FILAS DE LA COLUMNA 'RAMAS' (col 0)")
print("=" * 75)
for i in range(6, 20):
    if i < len(df):
        val = df.iloc[i, 0]
        if pd.notna(val):
            print(f"  Fila {i}: {val}")