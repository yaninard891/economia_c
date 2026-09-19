# src/prima_salarial.py
"""
Prima salarial EC (salario EC vs. salario provincial de La Rioja).

Metodología
-----------
- Prima mensual = (salario EC / salario provincial mensual − 1) × 100
- Prima anual  = promedio simple de las 12 primas mensuales
- Se reportan TRES versiones:
    * Nucleo_Software:     CIIU 7220 + 7250 + 7290 (software puro)
    * Nucleo_Amplio:       + 7300 (I+D) + 7430 (publicidad)
    * AFIP_DGIP_completo:  los 8 CIIU de la definición AFIP-DGIP
"""
import sys, os, re
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ = Path(__file__).resolve().parent.parent
os.chdir(_RAIZ)
sys.path.insert(0, str(_RAIZ))

from src.empresas_ec import CIIU_EC

RAW = _RAIZ / "data" / "raw"
PROCESSED = _RAIZ / "data" / "processed"

RUTA_REMUN = RAW / "provinciales_serie_remuneraciones_mensual_4dig_7.xlsx"
RUTA_SAL_PROV = RAW / "SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx"

HOJA_REMUN = "La Rioja"
ANIOS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

CIIU_NUCLEO_SW = {7220, 7250, 7290}
CIIU_NUCLEO_AMPLIO = {7220, 7250, 7290, 7300, 7430}
CIIU_COMPLETO = set(CIIU_EC.keys())


def parsear_hoja_remuneraciones(ruta, hoja):
    raw = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")
    header_row = None
    for i in range(min(15, len(raw))):
        vals = raw.iloc[i].astype(str).str.strip().str.lower().tolist()
        if "ramas" in vals:
            header_row = i
            break
    df = raw.iloc[header_row + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_row]]
    df = df.rename(columns={df.columns[1]: "rama", df.columns[2]: "descripcion"})
    df["rama"] = df["rama"].astype(str).str.strip()
    df = df[df["rama"].str.fullmatch(r"\d{3,4}")].copy()

    cols_mes = [c for c in df.columns if re.search(r"\d{4}-\d{2}", str(c))]
    tidy = df.melt(id_vars=["rama", "descripcion"], value_vars=cols_mes,
                   var_name="periodo", value_name="remuneracion")

    def _parse(s):
        m = re.search(r"(\d{4})-(\d{2})", str(s))
        return pd.Series([int(m.group(1)), int(m.group(2))]) if m else pd.Series([pd.NA, pd.NA])
    tidy[["anio", "mes"]] = tidy["periodo"].apply(_parse)

    def _a_float(v):
        if pd.isna(v): return np.nan
        s = str(v).strip()
        if s.lower() in {"s.d.", "sd", "", "nan", "-"}: return np.nan
        try: return float(s)
        except ValueError: return np.nan

    tidy["remuneracion"] = tidy["remuneracion"].map(_a_float)
    tidy = tidy.dropna(subset=["anio", "mes"]).copy()
    tidy["anio"] = tidy["anio"].astype(int)
    tidy["mes"] = tidy["mes"].astype(int)
    tidy["rama"] = tidy["rama"].astype(int)
    return tidy.reset_index(drop=True)


def salario_provincial_mensual(ruta, prov="La Rioja"):
    raw = pd.read_excel(ruta, sheet_name="Remuneraciones_promedio_privado",
                        header=None, engine="openpyxl")
    fila = None
    for i in range(len(raw)):
        if str(raw.iloc[i, 0]).strip() == prov:
            fila = i; break
    if fila is None:
        raise ValueError(f"Provincia '{prov}' no encontrada")

    cols = raw.iloc[0].tolist()
    df = pd.DataFrame({"periodo": cols[1:], "valor": raw.iloc[fila, 1:].values})
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    def _parse(p):
        s = str(p)
        m = re.search(r"(\d{4})-(\d{2})", s)
        if m:
            return pd.Series([int(m.group(1)), int(m.group(2))])
        meses = {"ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,
                 "jul":7,"ago":8,"sep":9,"oct":10,"nov":11,"dic":12}
        m = re.search(r"([a-z]{3})-(\d{2,4})", s.lower())
        if m:
            mes = meses.get(m.group(1))
            anio = int(m.group(2))
            if anio < 100: anio += 2000
            return pd.Series([anio, mes])
        return pd.Series([pd.NA, pd.NA])

    df[["anio", "mes"]] = df["periodo"].apply(_parse)
    return df.dropna(subset=["anio", "mes", "valor"]).reset_index(drop=True)


# ============================================================
# Cálculo
# ============================================================
print("=" * 74)
print("  Prima salarial EC — La Rioja")
print("=" * 74)

print("\n[1/3] Parseando remuneraciones...")
df_remun = parsear_hoja_remuneraciones(RUTA_REMUN, HOJA_REMUN)
ec = df_remun[df_remun["rama"].isin(CIIU_EC.keys())].copy()

print("[2/3] Cargando salario provincial...")
sal_prov = salario_provincial_mensual(RUTA_SAL_PROV, "La Rioja")

print("[3/3] Calculando primas...")

def prima_mes_a_mes(ciiu_set, etiqueta):
    filas = []
    for (anio, mes), g in ec[ec["anio"].isin(ANIOS)].groupby(["anio", "mes"]):
        sub = g[g["rama"].isin(ciiu_set)]
        if sub.empty: continue
        sal_ec = sub["remuneracion"].mean()
        sp_row = sal_prov[(sal_prov["anio"] == anio) & (sal_prov["mes"] == mes)]
        if sp_row.empty: continue
        sp = sp_row["valor"].iloc[0]
        if pd.isna(sp) or sp == 0: continue
        filas.append({"anio": anio, "prima": (sal_ec / sp - 1) * 100})
    if not filas:
        return pd.Series(dtype=float, name=etiqueta)
    return pd.DataFrame(filas).groupby("anio")["prima"].mean().round(2).rename(etiqueta)


nucleo_sw = prima_mes_a_mes(CIIU_NUCLEO_SW, "prima_nucleo_software")
nucleo_amplio = prima_mes_a_mes(CIIU_NUCLEO_AMPLIO, "prima_nucleo_amplio")
completo = prima_mes_a_mes(CIIU_COMPLETO, "prima_afip_dgip_completo")

out = pd.concat([nucleo_sw, nucleo_amplio, completo], axis=1).reset_index()
out = out.sort_values("anio").reset_index(drop=True)

print("\n=== Prima salarial EC (% sobre salario provincial) ===")
print(out.to_string(index=False))
print("\n  prima_nucleo_software    → 7220 + 7250 + 7290 (recomendado dashboard)")
print("  prima_nucleo_amplio      → + 7300 (I+D) + 7430 (publicidad)")
print("  prima_afip_dgip_completo → los 8 CIIU (incluye proxies)")

# ============================================================
# Exportar
# ============================================================
PROCESSED.mkdir(parents=True, exist_ok=True)
salida_xlsx = PROCESSED / "prima_salarial_ec.xlsx"
salida_csv = PROCESSED / "prima_salarial_ec.csv"

with pd.ExcelWriter(salida_xlsx, engine="openpyxl") as w:
    out.to_excel(w, sheet_name="Prima_anual", index=False)

out.to_csv(salida_csv, index=False)

print(f"\n✅ {salida_xlsx}")
print(f"✅ {salida_csv}")