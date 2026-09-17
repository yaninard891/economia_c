# src/dgip.py
"""
Parser de los informes DGIP La Rioja — Actividades tecnológicas.
Extrae la tabla de recaudación de Ingresos Brutos por actividad CIIU.
Incluye deflactado por IPC, cruce con stock de empresas SIPA e índices
nominales/reales.
"""
import re
from pathlib import Path

import pandas as pd
import pdfplumber


# ============================================================
# Helpers de parsing
# ============================================================

def _parse_int(s):
    """'331' → 331 ; '-' o vacío → None"""
    if s is None:
        return None
    s = str(s).strip()
    if s in ("", "-", "s.d.", "None"):
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_monto(s):
    """'$ 1.283.750.000,27' → 1283750000.27 ; '-' o vacío → None"""
    if s is None:
        return None
    s = str(s).strip()
    if s in ("", "-", "s.d.", "None"):
        return None
    s = s.replace("$", "").strip()
    # formato argentino: 1.234.567,89 → 1234567.89
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# ============================================================
# Parser principal
# ============================================================

def cargar_dgip_tecnologico(pdf_path: str | Path) -> pd.DataFrame:
    """
    Lee un informe DGIP de actividades tecnológicas (2 años por PDF).
    Devuelve tidy:
        cod | actividad | anio | contrib_conv | base_conv |
        contrib_local | base_local | impuesto_total
    """
    pdf_path = Path(pdf_path)
    with pdfplumber.open(pdf_path) as pdf:
        tabla = pdf.pages[0].extract_tables()[0]

    # --- Detectar los dos años en la fila 0 ---
    fila0 = tabla[0]
    anios = [str(c).strip() for c in fila0
             if c and re.match(r"^\d{4}$", str(c).strip())]
    if len(anios) != 2:
        raise ValueError(
            f"No pude detectar los 2 años en {pdf_path.name}. "
            f"Encontré: {anios}"
        )
    anio1, anio2 = int(anios[0]), int(anios[1])

    # --- Filas de datos (salteo los 2 headers) ---
    filas = []
    for row in tabla[2:]:
        cod = row[0]
        # Cortar cuando ya no hay código de 6 dígitos (TOTALES, vacías)
        if not cod or not re.match(r"^\d{6}$", str(cod).strip()):
            continue
        cod = str(cod).strip()
        act = (row[1] or "").replace("\n", " ").strip()

        # Bloque año 1: cols 2-6 | Bloque año 2: cols 7-11
        for anio, bloque in [(anio1, row[2:7]), (anio2, row[7:12])]:
            filas.append({
                "cod":             cod,
                "actividad":       act,
                "anio":            anio,
                "contrib_conv":    _parse_int(bloque[0]),
                "base_conv":       _parse_monto(bloque[1]),
                "contrib_local":   _parse_int(bloque[2]),
                "base_local":      _parse_monto(bloque[3]),
                "impuesto_total":  _parse_monto(bloque[4]),
            })

    return (pd.DataFrame(filas)
              .sort_values(["cod", "anio"])
              .reset_index(drop=True))


def cargar_dgip_tecnologico_multi(pdf_paths: list) -> pd.DataFrame:
    """Concatena varios PDFs (ej. 22-23 + 24-25) en una sola serie."""
    return (pd.concat([cargar_dgip_tecnologico(p) for p in pdf_paths],
                      ignore_index=True)
              .sort_values(["cod", "anio"])
              .reset_index(drop=True))


# ============================================================
# Indicadores DGIP
# ============================================================

def dgip_variacion_interanual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variación interanual (%) por actividad para cada métrica:
    contrib_conv, contrib_local, base_conv, base_local, impuesto_total.
    """
    df = df.sort_values(["cod", "anio"]).copy()
    for col in ["contrib_conv", "contrib_local",
                "base_conv", "base_local", "impuesto_total"]:
        df[f"var_ia_{col}"] = (
            df.groupby("cod")[col].pct_change() * 100
        )
    return df


def dgip_total_anual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Suma de todas las actividades por año (los 'totales' del informe,
    recalculados por nosotros).
    """
    return (df.groupby("anio")[["contrib_conv", "contrib_local",
                                 "base_conv", "base_local",
                                 "impuesto_total"]]
              .sum().reset_index())


def dgip_participacion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Participación (%) de cada actividad en el impuesto total del año.
    """
    df = df.copy()
    tot = df.groupby("anio")["impuesto_total"].transform("sum")
    df["participacion"] = df["impuesto_total"] / tot * 100
    return df


# ============================================================
# Deflactado con IPC
# ============================================================

def dgip_deflactar(
    df_dgip: pd.DataFrame,
    df_ipc: pd.DataFrame,
    anio_base: int = 2024,
    region: str = "Región Noroeste",
    categoria: str = "Nivel general",
) -> pd.DataFrame:
    """
    Convierte los montos nominales de DGIP a pesos constantes del
    anio_base, usando el IPC NOA (o la región que pases).

    Estrategia:
    - Del tidy IPC calculamos un índice de nivel mensual acumulado.
    - Se promedia ese índice por año.
    - Factor de deflactado: indice(anio_base) / indice(anio).
    - Aplicamos ese factor a base_conv, base_local, impuesto_total.

    Nota: el 'indice' arranca en 100 en el primer mes disponible
    del tidy (2017-01). No importa el valor absoluto, sólo el cociente.
    """
    # Índice mensual acumulado (base 100 en el primer mes del tidy)
    ipc = (df_ipc[(df_ipc["region"] == region) &
                  (df_ipc["categoria"] == categoria)]
           .sort_values("fecha").copy())
    ipc["factor"] = 1 + ipc["valor"] / 100
    ipc["indice"] = ipc["factor"].cumprod() * 100

    # Promedio anual del índice
    ipc["anio"] = ipc["fecha"].dt.year
    ind_anual = ipc.groupby("anio")["indice"].mean()

    if anio_base not in ind_anual.index:
        raise ValueError(f"Año base {anio_base} sin datos de IPC")

    factor_base = ind_anual.loc[anio_base]

    out = df_dgip.copy()
    out["factor_deflactor"] = out["anio"].map(
        lambda a: factor_base / ind_anual.loc[a]
        if a in ind_anual.index else None
    )
    for col in ["base_conv", "base_local", "impuesto_total"]:
        out[f"{col}_const"] = out[col] * out["factor_deflactor"]

    return out


# ============================================================
# Cruce DGIP × SIPA (empresas)
# ============================================================

def dgip_cruce_sipa(
    df_dgip: pd.DataFrame,
    df_sipa: pd.DataFrame,
    ramas_sipa: list[str] | None = None,
) -> pd.DataFrame:
    """
    Cruza la recaudación DGIP con el stock de empresas SIPA.

    df_sipa: tidy con provincia | Ramas | Descripción | anio | empresas
    ramas_sipa: lista de prefijos de rama SIPA (2 dígitos) a sumar.
        Ej: ['62','63','72','73','74','95'] para servicios técnicos.

    Devuelve: anio | empresas_sipa | contrib_conv | contrib_local |
              impuesto_total | impuesto_por_empresa |
              contrib_total | ratio_contrib_empresas
    """
    df_sipa = df_sipa.copy()

    # Si nos pasan ramas, filtramos; si no, usamos todas las secciones A-Z
    if ramas_sipa:
        df_sipa["rama2"] = df_sipa["Ramas"].str[:2]
        df_sipa = df_sipa[df_sipa["rama2"].isin(ramas_sipa)]
    else:
        df_sipa = df_sipa[df_sipa["Ramas"].str.match(r"^[A-Z]$", na=False)]

    empresas_anual = (df_sipa.groupby("anio")["empresas"]
                             .sum().reset_index()
                             .rename(columns={"empresas": "empresas_sipa"}))

    # DGIP: totales por año
    dgip_anual = (df_dgip.groupby("anio")
                  .agg(contrib_conv=("contrib_conv", "sum"),
                       contrib_local=("contrib_local", "sum"),
                       impuesto_total=("impuesto_total", "sum"))
                  .reset_index())

    out = dgip_anual.merge(empresas_anual, on="anio", how="left")
    out["impuesto_por_empresa"] = (out["impuesto_total"] /
                                   out["empresas_sipa"])
    out["contrib_total"] = out["contrib_conv"] + out["contrib_local"]
    out["ratio_contrib_empresas"] = (out["contrib_total"] /
                                     out["empresas_sipa"])
    return out


# ============================================================
# Índice base 100 (nominal o real)
# ============================================================

def dgip_indice(
    df_dgip: pd.DataFrame,
    anio_base: int = 2022,
    df_ipc: pd.DataFrame | None = None,
    real: bool = False,
    region: str = "Región Noroeste",
    categoria: str = "Nivel general",
) -> pd.DataFrame:
    """
    Índice base 100 = anio_base sobre impuesto, contribuyentes y base.

    real=False  → usa valores nominales (incluye inflación).
    real=True   → usa valores en pesos constantes del anio_base
                  (requiere pasar df_ipc). Mide crecimiento REAL.

    Devuelve: anio | impuesto_idx | contrib_conv_idx |
              contrib_local_idx | base_conv_idx
    """
    if real:
        if df_ipc is None:
            raise ValueError("real=True requiere df_ipc")
        df_def = dgip_deflactar(df_dgip, df_ipc,
                                anio_base=anio_base,
                                region=region, categoria=categoria)
        agg = (df_def.groupby("anio")
               .agg(impuesto_total=("impuesto_total_const", "sum"),
                    base_conv=("base_conv_const", "sum"),
                    contrib_conv=("contrib_conv", "sum"),
                    contrib_local=("contrib_local", "sum"))
               .reset_index())
    else:
        agg = (df_dgip.groupby("anio")
               .agg(impuesto_total=("impuesto_total", "sum"),
                    base_conv=("base_conv", "sum"),
                    contrib_conv=("contrib_conv", "sum"),
                    contrib_local=("contrib_local", "sum"))
               .reset_index())

    agg = agg.sort_values("anio")

    if anio_base not in agg["anio"].values:
        raise ValueError(f"Año base {anio_base} sin datos")

    base_row = agg[agg["anio"] == anio_base].iloc[0]

    for col, out in [("impuesto_total", "impuesto_idx"),
                     ("contrib_conv", "contrib_conv_idx"),
                     ("contrib_local", "contrib_local_idx"),
                     ("base_conv", "base_conv_idx")]:
        agg[out] = agg[col] / base_row[col] * 100

    return agg[["anio", "impuesto_idx", "contrib_conv_idx",
                "contrib_local_idx", "base_conv_idx"]]