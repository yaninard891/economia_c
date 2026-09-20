# -*- coding: utf-8 -*-
"""Compara los archivos de salario por CIIU disponibles en data/raw/."""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"


def mostrar_ciiu(nombre: str, hoja: str = "La Rioja") -> None:
    print("=" * 90)
    print(f"ARCHIVO: {nombre}")
    ruta = RAW / nombre
    if not ruta.exists():
        print("  No existe.")
        return
    try:
        xl = pd.ExcelFile(ruta)
        print(f"  Hojas ({len(xl.sheet_names)}): {xl.sheet_names[:10]}")
        if hoja not in xl.sheet_names:
            print(f'  Sin hoja "{hoja}", salteando.')
            return

        raw = pd.read_excel(ruta, sheet_name=hoja, header=None)
        print(f"  Shape: {raw.shape}")

        # Filas candidatas a header
        for idx in range(min(15, len(raw))):
            fila = [str(x) for x in raw.iloc[idx].tolist()]
            txt = " ".join(fila).upper()
            if any(k in txt for k in ("CIIU", "RAMAS", "DESCRIPCI", "CÓDIGO", "CODIGO")):
                print(f"  Header posible en fila {idx}: {fila[:8]}")

        # Buscar CIIU objetivo en col 1
        encontrados = 0
        for idx in range(0, len(raw)):
            v = raw.iloc[idx, 1]
            try:
                v_int = int(float(v))
            except (ValueError, TypeError):
                continue
            if v_int in (7290, 7220, 7210):
                encontrados += 1
                print(f"  CIIU {v_int} (fila {idx}): desc={raw.iloc[idx, 2]}")
                vals = raw.iloc[idx, 3:].dropna()
                if len(vals) > 0:
                    print(f"    últimos 6 valores: {vals.tail(6).tolist()}")
                    print(f"    columnas de esos 6: {list(vals.tail(6).index)}")
                    print(f"    PRIMER valor: {vals.iloc[0]} (col {vals.index[0]})")
        if encontrados == 0:
            print("  No se encontraron CIIU 7210/7220/7290 en col 1.")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
    print()


if __name__ == "__main__":
    mostrar_ciiu("provinciales_serie_remuneraciones_mensual_4dig_7.xlsx")
    mostrar_ciiu("provinciales_serie_remuneraciones_anual_3.xlsx")
    mostrar_ciiu("provinciales_serie_remuneraciones_mensual_2dig_8.xlsx")