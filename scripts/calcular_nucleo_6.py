"""
Calcula el empleo del núcleo informático ignorando códigos sin dato.
Núcleo teórico: 7210 + 7220 + 7250 + 7290 + 7300 + 7430
"""
import pandas as pd
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "data" / "raw" / "provinciales_serie_empleo_trimestral_4dig_7.xlsx"

df = pd.read_excel(RUTA, sheet_name="La Rioja", header=None)
header_tiempo = df.iloc[6, 2:].tolist()

def extraer_anio_trimestre(s):
    m = re.search(r"(\d)° Trim (\d{4})", str(s))
    return (int(m.group(2)), int(m.group(1))) if m else (None, None)

columnas_validas = [(i + 2, *extraer_anio_trimestre(h))
                    for i, h in enumerate(header_tiempo)
                    if extraer_anio_trimestre(h)[0] in (2022, 2023, 2024, 2025)]

def serie_ciiu(codigo):
    col0 = df.iloc[:, 0].astype(str)
    idx = df[col0.str.startswith(str(codigo))].index[0]
    valores = []
    for col_idx, anio, trim in columnas_validas:
        val = df.iloc[idx, col_idx]
        if pd.isna(val) or str(val).strip().lower() in ("s.d.", "sd", "—", "-", ""):
            valores.append((anio, trim, None))
        else:
            try:
                valores.append((anio, trim, float(val)))
            except (ValueError, TypeError):
                valores.append((anio, trim, None))
    return valores

def promedio_anual(valores):
    df_v = pd.DataFrame(valores, columns=["anio", "trim", "valor"])
    return df_v.groupby("anio")["valor"].mean().to_dict()

NUCLEO_6 = [7210, 7220, 7250, 7290, 7300, 7430]
PROXIES_2 = [7421, 7499]
AMPLIA_8 = NUCLEO_6 + PROXIES_2

resumen = {c: promedio_anual(serie_ciiu(c)) for c in AMPLIA_8}

# ---- Núcleo informático CON DATO DISPONIBLE (excluye nan) ----
print("=" * 85)
print("NÚCLEO INFORMÁTICO — CÓDIGOS CON DATO DISPONIBLE POR AÑO")
print("=" * 85)
print(f"{'CIIU':<6} {'Rama':<42} {'2022':>8} {'2023':>8} {'2024':>8} {'2025':>8}")
print("-" * 85)
nombres = {}
for c in AMPLIA_8:
    col0 = df.iloc[:, 0].astype(str)
    idx = df[col0.str.startswith(str(c))].index[0]
    nombres[c] = str(df.iloc[idx, 1])[:40]
    v = resumen[c]
    fila = f"{c:<6} {nombres[c]:<42}"
    for a in [2022, 2023, 2024, 2025]:
        val = v.get(a)
        fila += f" {val:>8.1f}" if val is not None and not pd.isna(val) else f" {'—':>8}"
    print(fila)
print("-" * 85)

def suma_anual(codigos):
    """Suma ignorando los códigos sin dato (nan)."""
    total = {}
    detalle = {}
    for a in [2022, 2023, 2024, 2025]:
        vals = []
        codigos_con_dato = []
        for c in codigos:
            v = resumen[c].get(a)
            if v is not None and not pd.isna(v):
                vals.append(v)
                codigos_con_dato.append(c)
        total[a] = sum(vals) if vals else None
        detalle[a] = codigos_con_dato
    return total, detalle

nucleo_6, det_nucleo = suma_anual(NUCLEO_6)
proxies_2, det_proxies = suma_anual(PROXIES_2)
amplia_8, det_amplia = suma_anual(AMPLIA_8)

print()
print("=" * 85)
print("AGREGADOS (ignorando códigos sin dato)")
print("=" * 85)
print(f"{'Categoría':<48} {'2022':>8} {'2023':>8} {'2024':>8} {'2025':>8}")
print("-" * 85)
for nombre, datos in [
    ("NÚCLEO INFORMÁTICO (6 códigos teóricos)", nucleo_6),
    ("PROXIES (7421+7499)", proxies_2),
    ("DEFINICIÓN AMPLIA ARCA-DGIP (8 códigos)", amplia_8),
]:
    fila = f"{nombre:<48}"
    for a in [2022, 2023, 2024, 2025]:
        val = datos.get(a)
        fila += f" {val:>8.1f}" if val is not None else f" {'—':>8}"
    print(fila)
print("-" * 85)

print()
print("DETALLE DE CÓDIGOS INCLUIDOS POR AÑO")
print("=" * 85)
for a in [2022, 2023, 2024, 2025]:
    print(f"  {a} → Núcleo: {det_nucleo[a]}")

print()
print("VARIACIONES 2022 → 2025")
for nombre, datos in [
    ("Núcleo informático", nucleo_6),
    ("Proxies", proxies_2),
    ("Definición amplia", amplia_8),
]:
    v22, v25 = datos.get(2022), datos.get(2025)
    if v22 and v25:
        delta = (v25 - v22) / v22 * 100
        print(f"  {nombre:<25}: {v22:>6.1f} → {v25:>6.1f}  ({delta:+.1f}%)")