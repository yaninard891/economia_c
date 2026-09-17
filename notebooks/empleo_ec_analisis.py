"""
Análisis de empleo del sector EC (Ley 27.506) en La Rioja
==========================================================
Fuente: SIPA-OEDE, provinciales_serie_empleo_trimestral_4dig_7.xlsx
"""

import os
import sys
import re
from pathlib import Path

import pandas as pd

if Path.cwd().name == "notebooks":
    os.chdir(Path.cwd().parent)
sys.path.insert(0, str(Path.cwd()))

from src.empresas_ec import LEY_27_506, cargar_provincia, serie_ec


def parsear_hoja_empleo(ruta: Path, hoja: str) -> pd.DataFrame:
    raw = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")
    header_row = None
    for i in range(min(20, len(raw))):
        vals = raw.iloc[i].astype(str).str.strip().str.lower().tolist()
        if "ramas" in vals and any("descrip" in v for v in vals):
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"Encabezado no encontrado en '{hoja}'")

    df = raw.iloc[header_row + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_row]]
    df = df.rename(columns={df.columns[0]: "rama", df.columns[1]: "descripcion"})
    df["rama"] = df["rama"].astype(str).str.strip()
    df = df[df["rama"].str.fullmatch(r"\d{3,4}")].copy()

    cols_trim = [c for c in df.columns if re.search(r"trim", str(c), re.I)]
    tidy = df.melt(id_vars=["rama", "descripcion"],
                   value_vars=cols_trim,
                   var_name="periodo", value_name="empleo")

    def extraer(s):
        m = re.search(r"(\d)\s*[°º]?\s*Trim\s*(\d{4})", str(s), re.I)
        if m:
            return pd.Series([int(m.group(2)), int(m.group(1))])
        return pd.Series([pd.NA, pd.NA])
    tidy[["anio", "trimestre"]] = tidy["periodo"].apply(extraer)

    def _a_int(v):
        if pd.isna(v):
            return pd.NA
        s = str(v).strip()
        if s.lower() in {"s.d.", "sd", "", "nan", "-"}:
            return pd.NA
        try:
            return int(float(s))
        except ValueError:
            return pd.NA
    tidy["empleo"] = tidy["empleo"].map(_a_int).astype("Int64")
    tidy = tidy.dropna(subset=["anio", "trimestre"])
    tidy["anio"] = tidy["anio"].astype(int)
    tidy["trimestre"] = tidy["trimestre"].astype(int)
    return tidy.reset_index(drop=True)


RUTA_EMPLEO = Path("data/raw/provinciales_serie_empleo_trimestral_4dig_7.xlsx")
RUTA_EMPRESAS = Path("data/raw/provinciales_serie_empresas3_2.xlsx")
PROV = "La Rioja"
OUT = Path("data/processed/empleo_ec_rioja.xlsx")

print("=" * 74)
print(f"  Empleo del sector EC (Ley 27.506) — {PROV}")
print("=" * 74)

df = parsear_hoja_empleo(RUTA_EMPLEO, PROV)
print(f"Filas tidy:      {len(df):,}")
print(f"Ramas distintas: {df['rama'].nunique()}")
print(f"Años:            {df['anio'].min()}–{df['anio'].max()}")

df_ec = df[df["rama"].isin(LEY_27_506)].copy()
print(f"\nRamas EC con datos: {df_ec['rama'].nunique()} de {len(LEY_27_506)}")

# === FIX: sumar por trimestre, después promediar ===
df_ec_q = (df_ec
    .groupby(["anio", "trimestre"], as_index=False)["empleo"]
    .sum(min_count=1))

empleo_ec_anual = (df_ec_q
    .groupby("anio", as_index=False)["empleo"]
    .mean()
    .rename(columns={"empleo": "empleo_ec_prom"}))

df_tot_q = (df
    .groupby(["anio", "trimestre"], as_index=False)["empleo"]
    .sum(min_count=1))

empleo_tot_anual = (df_tot_q
    .groupby("anio", as_index=False)["empleo"]
    .mean()
    .rename(columns={"empleo": "empleo_total_prom"}))

comp = (empleo_ec_anual
        .merge(empleo_tot_anual, on="anio", how="outer")
        .assign(share_ec_pct=lambda d:
                (d["empleo_ec_prom"] / d["empleo_total_prom"] * 100).round(2)))

print(f"\n=== Empleo EC vs Total provincial ===")
print(comp.query("anio >= 2019").to_string(index=False))

df_emp = cargar_provincia(RUTA_EMPRESAS, PROV)
emp_ec_anual = serie_ec(df_emp, "ley_27_506")

elasticidad = (comp[["anio", "empleo_ec_prom"]]
               .merge(emp_ec_anual, on="anio", how="inner")
               .query("anio >= 2022"))

print(f"\n=== Elasticidad empleo vs empresas EC ===")
print(elasticidad.to_string(index=False))

p, u = 2022, 2025
try:
    var_emp = (elasticidad.loc[elasticidad["anio"] == u, "empresas_ec"].iloc[0] /
               elasticidad.loc[elasticidad["anio"] == p, "empresas_ec"].iloc[0] - 1) * 100
    var_emp_emp = (elasticidad.loc[elasticidad["anio"] == u, "empleo_ec_prom"].iloc[0] /
                   elasticidad.loc[elasticidad["anio"] == p, "empleo_ec_prom"].iloc[0] - 1) * 100
    print(f"\n  Var. empresas 2022→2025: {var_emp:+.1f}%")
    print(f"  Var. empleo   2022→2025: {var_emp_emp:+.1f}%")
    if var_emp != 0:
        print(f"  Elasticidad:             {var_emp_emp / var_emp:.2f}")
except Exception as e:
    print(f"  (no se pudo calcular: {e})")

OUT.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    empleo_ec_anual.to_excel(w, sheet_name="Empleo_EC_anual", index=False)
    comp.to_excel(w, sheet_name="Empleo_EC_vs_total", index=False)
    elasticidad.to_excel(w, sheet_name="Elasticidad", index=False)
    df_ec.to_excel(w, sheet_name="Empleo_EC_trimestral", index=False)

print(f"\n[OK] {OUT}")