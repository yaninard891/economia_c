"""
Módulo de Empresas de Economía del Conocimiento (EC) para La Rioja.

Definición AFIP-DGIP
--------------------
Usa los CIIU Rev. 3 equivalentes a las actividades AFIP/ARCA que generan
el impuesto DGIP tecnológico en La Rioja:

    620104  → 7220  Consultores en informática y suministros de programas
    620300  → 7210  Consultores en equipo de informática
    620900  → 7290  Servicios de informática n.c.p.
    711002  → 7421  Servicios geológicos y de prospección         [proxy]
    7210xx  → 7300  I+D experimental                              [proxy]
    731009  → 7430  Servicios de publicidad n.c.p.
    741000  → 7499  Servicios de diseño especializado             [proxy]
    749001  → 7499  Servicios de traducción e interpretación      [proxy]
    951100  → 7250  Reparación y mantenimiento de eq. informáticos

Advertencia
-----------
Los códigos 7421 y 7499 incluyen actividades NO-EC porque el SIPA no
desagrega a 6 dígitos:

    7421 → arquitectura + ingeniería civil + agrimensura + geología
    7499 → diseño + traducción + cobranzas + eventos + gestión

El conteo resultante debe leerse como "techo superior" (upper bound)
de la EC riojana, no como conteo exacto.

Uso
---
    from src.empresas_ec import (
        cargar_ec, serie_ec, por_bloque, por_codigo,
        participacion_total, resumen,
    )

    df = cargar_ec()
    print(serie_ec(df))
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
RUTA_EC = RAIZ / "data" / "raw" / "empresas_ec_rioja.csv"
RUTA_TOTAL = RAIZ / "data" / "raw" / "total_provincial_rioja.csv"

# ---------------------------------------------------------------------------
# Metadatos
# ---------------------------------------------------------------------------
# Códigos CIIU incluidos en la definición AFIP-DGIP
CIIU_EC: dict[int, str] = {
    7210: "Consultores en equipo de informática",
    7220: "Consultores en informática y suministros de programas",
    7250: "Mantenimiento y reparación de maq. informática",
    7290: "Actividades de informática n.c.p.",
    7300: "Investigación y desarrollo",
    7421: "Servicios de arquitectura e ingeniería",
    7430: "Servicios de publicidad",
    7499: "Servicios empresariales n.c.p.",
}

# Equivalencia AFIP → CIIU (para documentación)
ACTIVIDADES_AFIP: dict[int, str] = {
    7220: "620104",
    7210: "620300",
    7290: "620900",
    7421: "711002",
    7300: "7210xx",
    7430: "731009",
    7499: "741000 + 749001",
    7250: "951100",
}

# Bloques temáticos
BLOQUES: dict[str, set[int]] = {
    "Software y SI": {7210, 7220, 7250, 7290},
    "I+D": {7300},
    "Ingeniería y geología (proxy)": {7421},
    "Publicidad": {7430},
    "Servicios profesionales (proxy)": {7499},
}

# Orden de años disponibles
ANIOS = [2019, 2020, 2021, 2022, 2024, 2025]

# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------
def cargar_ec(ruta: Path | None = None) -> pd.DataFrame:
    """
    Carga el dataset de empresas EC desde el CSV curado.

    Parameters
    ----------
    ruta : Path, opcional
        Ruta al CSV. Por defecto `data/raw/empresas_ec_rioja.csv`.

    Returns
    -------
    DataFrame con columnas: anio, ciiu, actividad, empresas.
    """
    ruta = ruta or RUTA_EC
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta}.\n"
            "Creá el CSV con las columnas: anio, ciiu, actividad, empresas."
        )
    df = pd.read_csv(ruta)
    df["empresas"] = pd.to_numeric(df["empresas"], errors="coerce")
    df["ciiu"] = df["ciiu"].astype(int)
    df["anio"] = df["anio"].astype(int)
    return df


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _bloque(ciiu: int) -> str:
    """Devuelve el nombre del bloque temático para un CIIU."""
    for nombre, codigos in BLOQUES.items():
        if ciiu in codigos:
            return nombre
    return "Otros"


# ---------------------------------------------------------------------------
# Agregaciones
# ---------------------------------------------------------------------------
def serie_ec(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Serie anual del total de empresas EC.

    Returns
    -------
    DataFrame con columnas: anio, total_ec.
    """
    if df is None:
        df = cargar_ec()
    return (
        df.groupby("anio", as_index=False)["empresas"]
        .sum(min_count=1)
        .rename(columns={"empresas": "total_ec"})
    )


def por_bloque(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Total por bloque temático y año.

    Returns
    -------
    DataFrame con columnas: anio, bloque, empresas.
    """
    if df is None:
        df = cargar_ec()
    df = df.copy()
    df["bloque"] = df["ciiu"].apply(_bloque)
    return (
        df.groupby(["anio", "bloque"], as_index=False)["empresas"]
        .sum(min_count=1)
        .sort_values(["anio", "bloque"])
    )


def por_codigo(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Total por código CIIU y año (formato ancho).

    Returns
    -------
    DataFrame indexado por ciiu, con una columna por año.
    """
    if df is None:
        df = cargar_ec()
    return df.pivot_table(
        index="ciiu",
        columns="anio",
        values="empresas",
        aggfunc="sum",
    )


def participacion_total(
    df_ec: pd.DataFrame | None = None,
    ruta_total: Path | None = None,
) -> pd.DataFrame:
    """
    Participación EC sobre total provincial.

    Requiere `data/raw/total_provincial_rioja.csv` con columnas
    `anio,total_provincial`.

    Returns
    -------
    DataFrame con columnas: anio, total_ec, total_provincial, participacion_pct.
    """
    if df_ec is None:
        df_ec = cargar_ec()
    ruta_total = ruta_total or RUTA_TOTAL
    if not ruta_total.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta_total}.\n"
            "Creá el CSV con columnas: anio,total_provincial."
        )
    serie = serie_ec(df_ec)
    total = pd.read_csv(ruta_total)
    total["anio"] = total["anio"].astype(int)
    out = serie.merge(total, on="anio", how="left")
    out["participacion_pct"] = (
        out["total_ec"] / out["total_provincial"] * 100
    ).round(2)
    return out


# ---------------------------------------------------------------------------
# Resumen ejecutivo
# ---------------------------------------------------------------------------
def resumen(df: pd.DataFrame | None = None) -> dict:
    """
    Devuelve un diccionario con los indicadores clave para el dashboard.

    Returns
    -------
    dict con:
        anio_base, anio_ultimo
        total_base, total_ultimo
        crecimiento_pct
        total_2024
        bloques_2024 (dict)
        serie (DataFrame)
    """
    if df is None:
        df = cargar_ec()
    s = serie_ec(df).dropna(subset=["total_ec"]).reset_index(drop=True)
    if s.empty:
        return {}

    base = s.iloc[0]
    ultimo = s.iloc[-1]
    df24 = df[df["anio"] == 2024]
    bloques_24 = (
        df24.assign(bloque=df24["ciiu"].apply(_bloque))
        .groupby("bloque")["empresas"].sum()
        .to_dict()
    )

    return {
        "anio_base": int(base["anio"]),
        "anio_ultimo": int(ultimo["anio"]),
        "total_base": float(base["total_ec"]),
        "total_ultimo": float(ultimo["total_ec"]),
        "crecimiento_pct": round(
            (ultimo["total_ec"] / base["total_ec"] - 1) * 100, 1
        ),
        "total_2024": float(
            df[df["anio"] == 2024]["empresas"].sum(min_count=1)
        ),
        "bloques_2024": bloques_24,
        "serie": s,
    }

# ---------------------------------------------------------------------------
# Benchmark entre provincias (lee el Excel crudo de INDEC)
# ---------------------------------------------------------------------------
RUTA_EMPRESAS_RAW = RAIZ / "data" / "raw" / "provinciales_serie_empresas3_2.xlsx"

PROVINCIAS_BENCHMARK = [
    "La Rioja", "Catamarca", "Jujuy", "Salta",
    "Santiago del Estero", "Tucumán", "Córdoba",
    "Santa Fé", "CABA",
]


def _procesar_hoja_provincia(hoja: str, anio: str = "2024"):
    """Lee una hoja del Excel de INDEC y suma EC + total para el año dado."""
    try:
        df = pd.read_excel(RUTA_EMPRESAS_RAW, sheet_name=hoja, header=None)
    except Exception:
        return None, None

    # Detectar fila con los años
    fila_anios = None
    for i in range(min(15, len(df))):
        if (df.iloc[i].astype(str) == "1996").any():
            fila_anios = i
            break
    if fila_anios is None:
        return None, None

    # Detectar columna del año pedido
    col_anio = None
    for j, v in enumerate(df.iloc[fila_anios].tolist()):
        if str(v).strip() == anio:
            col_anio = j
            break
    if col_anio is None:
        return None, None

    ec, total = 0, 0
    for i in range(fila_anios + 1, len(df)):
        try:
            cod = int(float(df.iloc[i, 0]))
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


def benchmark_provincias(
    anio: str = "2024",
    provincias: list[str] | None = None,
) -> pd.DataFrame:
    """
    Calcula intensidad empresarial EC (‰) por provincia.

    Returns
    -------
    DataFrame con columnas: provincia, ec, total, intensidad_pm.
    Ordenado de mayor a menor intensidad.
    """
    provincias = provincias or PROVINCIAS_BENCHMARK
    filas = []
    for prov in provincias:
        ec, tot = _procesar_hoja_provincia(prov, anio)
        if ec is None or tot == 0:
            continue
        filas.append({
            "provincia": prov,
            "ec": ec,
            "total": tot,
            "intensidad_pm": round(ec / tot * 1000, 2),
        })
    return pd.DataFrame(filas).sort_values("intensidad_pm", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Exportación a Excel
# ---------------------------------------------------------------------------
def exportar_excel_ec(
    ruta_salida: Path | str = None,
    df: pd.DataFrame | None = None,
) -> Path:
    """
    Exporta el análisis EC a un Excel con 4 hojas:
    serie, bloques, codigos, participacion.

    Returns
    -------
    Path del archivo generado.
    """
    ruta_salida = Path(ruta_salida or (RAIZ / "data" / "processed" / "empresas_ec_rioja.xlsx"))
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    if df is None:
        df = cargar_ec()

    serie = serie_ec(df)
    bloques = por_bloque(df)
    codigos = por_codigo(df)

    try:
        part = participacion_total(df)
    except FileNotFoundError:
        part = pd.DataFrame()

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        serie.to_excel(writer, sheet_name="serie", index=False)
        bloques.to_excel(writer, sheet_name="bloques", index=False)
        codigos.to_excel(writer, sheet_name="codigos")
        if not part.empty:
            part.to_excel(writer, sheet_name="participacion", index=False)

    print(f"✅ Excel EC exportado: {ruta_salida}")
    return ruta_salida
# ---------------------------------------------------------------------------
# CLI rápida
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = cargar_ec()

    print("=== Serie EC ===")
    print(serie_ec(df).to_string(index=False))

    print("\n=== Por bloque ===")
    print(por_bloque(df).to_string(index=False))

    print("\n=== Por código (ancho) ===")
    print(por_codigo(df).to_string())

    print("\n=== Resumen ===")
    r = resumen(df)
    for k, v in r.items():
        if k != "serie":
            print(f"  {k}: {v}")