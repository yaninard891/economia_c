# src/benchmark_intensidad.py
"""Intensidad empresarial EC (‰) por provincia con definición AFIP-DGIP."""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "data" / "raw" / "provinciales_serie_empresas3_2.xlsx"

CIIU_EC = {7210, 7220, 7250, 7290, 7300, 7421, 7430, 7499}
PROVINCIAS = [
    "La Rioja", "Catamarca", "Jujuy", "Salta",
    "Santiago del Estero", "Tucumán", "Córdoba",
    "Santa Fé", "CABA",
]

def procesar(hoja: str, anio: str = "2024"):
    try:
        df = pd.read_excel(RUTA, sheet_name=hoja, header=None)
    except Exception as e:
        print(f"  ⚠️  No se pudo leer hoja '{hoja}': {e}")
        return None, None

    fila_anios = None
    for i in range(min(15, len(df))):
        if (df.iloc[i].astype(str) == "1996").any():
            fila_anios = i
            break
    if fila_anios is None:
        return None, None

    anios = df.iloc[fila_anios].tolist()
    col_anio = None
    for j, v in enumerate(anios):
        if str(v).strip() == anio:
            col_anio = j
            break
    if col_anio is None:
        return None, None

    ec, total = 0, 0
    for i in range(fila_anios + 1, len(df)):
        try:
            cod = int(df.iloc[i, 0])
        except (ValueError, TypeError):
            continue
        try:
            val = int(float(df.iloc[i, col_anio]))
        except (ValueError, TypeError):
            continue
        total += val
        if cod in CIIU_EC:
            ec += val
    return ec, total


if __name__ == "__main__":
    print(f"{'Provincia':25s} {'EC':>6s} {'Total':>8s} {'Intensidad':>12s}")
    print("-" * 55)
    resultados = []
    for prov in PROVINCIAS:
        ec, tot = procesar(prov, "2024")
        if ec is None or tot == 0:
            print(f"{prov:25s} {'s/d':>6s}")
            continue
        inten = ec / tot * 1000
        resultados.append({"provincia": prov, "ec": ec, "total": tot, "intensidad": inten})
        print(f"{prov:25s} {ec:>6d} {tot:>8d} {inten:>11.2f}‰")

    # Guardar CSV para usar en dashboard
    out = RAIZ / "data" / "processed" / "intensidad_provincias.csv"
    pd.DataFrame(resultados).to_csv(out, index=False)
    print(f"\n✅ Guardado: {out}")