"""
src/empresas_ec.py
==================
Análisis de empresas de Economía del Conocimiento (EC) para una provincia,
a partir de `provinciales_serie_empresas3_2.xlsx`
(SIPA - Observatorio de Empleo y Dinámica Empresarial, STEySS).

Definición única y oficial: Ley 27.506 de Economía del Conocimiento
(mapeada de CLAE 2018 a CIIU rev. 3, que es la clasificación que usa el Excel).
"""

from __future__ import annotations
import re
from pathlib import Path
import pandas as pd


# ===========================================================================
# 1. Definición oficial — Ley 27.506 (mapeada a CIIU rev. 3)
# ===========================================================================

LEY_27_506: frozenset[str] = frozenset({
    # --- a) Software y servicios informáticos y digitales ---
    "6420",   # Telecomunicaciones
    "7210",   # Consultores en equipo de informática
    "7220",   # Consultores en informática y suministro de software
    "7230",   # Procesamiento de datos
    "7240",   # Bases de datos
    "7250",   # Mantenimiento de maq. oficina e informática
    "7290",   # Actividades de informática n.c.p.

    # --- b) Producción y postproducción audiovisual ---
    "2211",   # Edición de libros, folletos, partituras
    "2212",   # Edición de periódicos, revistas
    "2219",   # Edición n.c.p.
    "2230",   # Reproducción de grabaciones
    "9211",   # Producción y distribución de filmes
    "9212",   # Exhibición de filmes
    "9213",   # Radio y televisión
    "9214",   # Servicios teatrales y musicales
    "9219",   # Espectáculos artísticos y diversión
    "9220",   # Agencias de noticias

    # --- c) Biotecnología y bioeconomía ---
    "2423",   # Farmacéutica, sustancias medicinales y botánicos

    # --- d) Servicios geológicos, electrónica y comunicaciones ---
    "3210",   # Componentes electrónicos
    "3220",   # Transmisores de radio y TV
    "3230",   # Receptores de radio y TV

    # --- e) Servicios profesionales de exportación ---
    "7421",   # Arquitectura e ingeniería
    "7422",   # Ensayos y análisis técnicos
    "7430",   # Publicidad

    # --- f) Nanotecnología y nanociencia ---
    "7300",   # Investigación y desarrollo

    # --- g) Industria aeroespacial y satelital ---
    "3530",   # Fabricación y reparación de aeronaves

    # --- h) Ingeniería para la industria nuclear ---
    "2330",   # Elaboración de combustible nuclear

    # --- i) Industria 4.0 (automatización, robótica, IoT) ---
    "2911", "2912", "2913", "2914", "2915", "2919",
    "2921", "2922", "2923", "2924", "2925", "2926", "2927", "2929",
    "2930",
    "3000",   # Maquinaria de oficina, contabilidad e informática
    "3310", "3311", "3320", "3330",
})

DEFINICIONES: dict[str, frozenset[str]] = {"ley_27_506": LEY_27_506}

ETIQUETAS: dict[str, str] = {"ley_27_506": "Ley 27.506 (definición oficial)"}


# ===========================================================================
# 2. Lectura del Excel provincial
# ===========================================================================

def _encontrar_hoja(xl: pd.ExcelFile, provincia: str) -> str:
    objetivo = provincia.strip().lower()
    for hoja in xl.sheet_names:
        if hoja.strip().lower() == objetivo:
            return hoja
    for hoja in xl.sheet_names:
        if objetivo in hoja.strip().lower():
            return hoja
    raise ValueError(f"Hoja '{provincia}' no encontrada. Hojas: {xl.sheet_names}")


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


def parsear_hoja(ruta: Path, hoja: str) -> pd.DataFrame:
    raw = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")

    header_row = None
    for i in range(min(20, len(raw))):
        vals = raw.iloc[i].astype(str).str.strip().str.lower().tolist()
        if "ramas" in vals and any("descrip" in v for v in vals):
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"Encabezado no hallado en '{hoja}'")

    df = raw.iloc[header_row + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_row]]

    col_rama, col_desc = df.columns[0], df.columns[1]
    anios = [c for c in df.columns if re.fullmatch(r"\d{4}", c)]

    df = df.rename(columns={col_rama: "rama", col_desc: "descripcion"})
    df["rama"] = df["rama"].astype(str).str.strip()
    df = df[df["rama"].str.fullmatch(r"\d{3,4}")].copy()

    tidy = df.melt(
        id_vars=["rama", "descripcion"],
        value_vars=anios,
        var_name="anio",
        value_name="empresas",
    )
    tidy["anio"] = tidy["anio"].astype(int)
    tidy["empresas"] = tidy["empresas"].map(_a_int).astype("Int64")
    return tidy.reset_index(drop=True)


# ===========================================================================
# 3. API pública
# ===========================================================================

def cargar_provincia(ruta: Path, provincia: str = "La Rioja") -> pd.DataFrame:
    with pd.ExcelFile(ruta, engine="openpyxl") as xl:
        hoja = _encontrar_hoja(xl, provincia)
    return parsear_hoja(ruta, hoja)


def filtrar_ec(df: pd.DataFrame, definicion: str = "ley_27_506",
               anios: list[int] | None = None) -> pd.DataFrame:
    if definicion not in DEFINICIONES:
        raise KeyError(f"Definición '{definicion}' inválida. Opciones: {list(DEFINICIONES)}")
    out = df[df["rama"].isin(DEFINICIONES[definicion])].copy()
    if anios is not None:
        out = out[out["anio"].isin(anios)]
    return out


def serie_empresas(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("anio", as_index=False)["empresas"]
          .sum(min_count=1)
          .rename(columns={"empresas": "total_empresas"})
    )


def serie_ec(df: pd.DataFrame, definicion: str = "ley_27_506") -> pd.DataFrame:
    sub = filtrar_ec(df, definicion)
    return (
        sub.groupby("anio", as_index=False)["empresas"]
           .sum(min_count=1)
           .rename(columns={"empresas": "empresas_ec"})
    )


def detalle_ramas(df: pd.DataFrame, anio: int,
                  definicion: str = "ley_27_506") -> pd.DataFrame:
    sub = filtrar_ec(df, definicion, anios=[anio])
    sub = (sub[["rama", "descripcion", "empresas"]]
           .sort_values("empresas", ascending=False)
           .reset_index(drop=True))
    total = sub["empresas"].sum()
    sub["pct"] = (sub["empresas"] / total * 100).round(2) if total and total > 0 else 0.0
    sub["acumulado"] = sub["empresas"].cumsum()
    return sub


def listar_ramas_definicion(definicion: str = "ley_27_506") -> pd.DataFrame:
    if definicion not in DEFINICIONES:
        raise KeyError(f"Definición '{definicion}' inválida.")
    return pd.DataFrame({"rama": sorted(DEFINICIONES[definicion]),
                         "definicion": definicion})


def benchmark_provincias(
    ruta: Path,
    anio: int,
    definicion: str = "ley_27_506",
    provincias: list[str] | None = None,
) -> pd.DataFrame:
    if provincias is None:
        provincias = [
            "La Rioja", "Catamarca", "Jujuy", "Salta",
            "Santiago del Estero", "Tucumán",
            "Córdoba", "Santa Fé", "CABA",
        ]
    filas = []
    with pd.ExcelFile(ruta, engine="openpyxl") as xl:
        for prov in provincias:
            try:
                hoja = _encontrar_hoja(xl, prov)
                df = parsear_hoja(ruta, hoja)
            except Exception:
                continue
            ec_serie = serie_ec(df, definicion)
            tot_serie = serie_empresas(df)
            ec = ec_serie.loc[ec_serie["anio"] == anio, "empresas_ec"]
            tot = tot_serie.loc[tot_serie["anio"] == anio, "total_empresas"]
            filas.append({
                "provincia": prov,
                "anio": anio,
                "empresas_total": tot.iloc[0] if not tot.empty else pd.NA,
                "empresas_ec": ec.iloc[0] if not ec.empty else pd.NA,
            })
    out = pd.DataFrame(filas)
    if not out.empty:
        out["share_ec_pct"] = (out["empresas_ec"] / out["empresas_total"] * 100).round(2)
        out = out.sort_values("empresas_ec", ascending=False).reset_index(drop=True)
    return out


# ===========================================================================
# 4. Exportadores
# ===========================================================================

def exportar_excel_empresas(df: pd.DataFrame, anio_actual: int,
                            ruta_salida: Path, provincia: str = "La Rioja",
                            ruta_excel: Path | None = None) -> None:
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as w:
        serie_empresas(df).to_excel(w, sheet_name="Serie_total", index=False)
        serie_ec(df, "ley_27_506").to_excel(w, sheet_name="EC_por_anio", index=False)
        detalle_ramas(df, anio_actual, "ley_27_506").to_excel(
            w, sheet_name=f"Detalle_ley_{anio_actual}", index=False)
        if ruta_excel is not None:
            benchmark_provincias(ruta_excel, anio_actual, "ley_27_506").to_excel(
                w, sheet_name=f"Benchmark_{anio_actual}", index=False)
        listar_ramas_definicion("ley_27_506").to_excel(
            w, sheet_name="Codigos_ley_27_506", index=False)
    print(f"[OK] Excel empresas → {ruta_salida}")


def exportar_excel_ec(df: pd.DataFrame, ruta_salida: Path,
                      provincia: str = "La Rioja") -> None:
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as w:
        sub = filtrar_ec(df, "ley_27_506")
        pivot = (sub.pivot_table(index="anio", columns="rama",
                                 values="empresas", aggfunc="sum").sort_index())
        pivot["TOTAL"] = pivot.sum(axis=1, min_count=1)
        pivot.to_excel(w, sheet_name="Serie_ley_27_506")
        serie_ec(df, "ley_27_506").to_excel(
            w, sheet_name="Totales_por_anio", index=False)
        listar_ramas_definicion("ley_27_506").to_excel(
            w, sheet_name="Codigos_ley_27_506", index=False)
    print(f"[OK] Excel EC → {ruta_salida}")