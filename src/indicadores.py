# src/indicadores.py
"""
Indicadores derivados a partir de los datos tidy de src/funciones.py
"""
import numpy as np
import pandas as pd


# ============================================================
# IPC — variaciones
# ============================================================

def ipc_variacion_interanual(df: pd.DataFrame) -> pd.DataFrame:
    """
    A partir del tidy de IPC (region | categoria | fecha | valor),
    donde 'valor' es la variación MENSUAL en %, calcula la
    variación INTERANUAL (%) compuesta de los últimos 12 meses.

    Devuelve: region | categoria | fecha | var_interanual
    """
    out = []
    for (reg, cat), g in df.groupby(["region", "categoria"]):
        g = g.sort_values("fecha").copy()
        g["factor"] = 1 + g["valor"] / 100.0
        g["var_interanual"] = (
            g["factor"].rolling(12).apply(np.prod, raw=True) - 1
        ) * 100
        out.append(g[["region", "categoria", "fecha", "var_interanual"]])
    return (pd.concat(out, ignore_index=True)
              .sort_values(["region", "categoria", "fecha"])
              .reset_index(drop=True))


def ipc_acumulado_anual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variación acumulada en lo que va del año (%) para cada
    region/categoria/fecha. Se reinicia cada 1 de enero.
    """
    out = []
    for (reg, cat), g in df.groupby(["region", "categoria"]):
        g = g.sort_values("fecha").copy()
        g["factor"] = 1 + g["valor"] / 100.0
        g["anio"] = g["fecha"].dt.year
        g["acum_anual"] = (
            g.groupby("anio")["factor"]
             .transform(lambda s: s.cumprod()) - 1
        ) * 100
        out.append(g[["region", "categoria", "fecha", "acum_anual"]])
    return (pd.concat(out, ignore_index=True)
              .sort_values(["region", "categoria", "fecha"])
              .reset_index(drop=True))


def ipc_indice_base100(
    df: pd.DataFrame,
    fecha_base: str = "2017-01-01",
) -> pd.DataFrame:
    """
    Índice base 100 a partir de una fecha. Como los 'valor' son
    variaciones mensuales, se construye el nivel acumulado desde
    fecha_base.
    """
    base = pd.Timestamp(fecha_base)
    out = []
    for (reg, cat), g in df.groupby(["region", "categoria"]):
        g = g.sort_values("fecha").copy()
        g = g[g["fecha"] >= base]
        g["factor"] = 1 + g["valor"] / 100.0
        g["indice"] = g["factor"].cumprod() * 100
        g.loc[g.index[0], "indice"] = 100
        out.append(g[["region", "categoria", "fecha", "indice"]])
    return (pd.concat(out, ignore_index=True)
              .sort_values(["region", "categoria", "fecha"])
              .reset_index(drop=True))


# ============================================================
# Empresas — variaciones y estructura
# ============================================================

def empresas_variacion_interanual(df: pd.DataFrame) -> pd.DataFrame:
    """
    A partir del tidy de empresas
    (provincia | Ramas | Descripción | anio | empresas),
    calcula la variación interanual (%) del stock de empresas.

    Devuelve: provincia | Ramas | Descripción | anio | empresas | var_ia
    """
    df = df.sort_values(["provincia", "Ramas", "anio"]).copy()
    df["var_ia"] = (
        df.groupby(["provincia", "Ramas"])["empresas"]
          .pct_change() * 100
    )
    return df


def empresas_indice_base100(
    df: pd.DataFrame,
    anio_base: int = 1996,
) -> pd.DataFrame:
    """
    Índice base 100 en 'anio_base' para cada provincia/rama.
    """
    df = df.sort_values(["provincia", "Ramas", "anio"]).copy()
    base = (df[df["anio"] == anio_base]
            .set_index(["provincia", "Ramas"])["empresas"])
    df["base"] = df.set_index(["provincia", "Ramas"]).index.map(base)
    df["indice"] = df["empresas"] / df["base"] * 100
    return df.drop(columns="base")


def empresas_participacion_sectorial(
    df: pd.DataFrame,
    anio: int,
    nivel: str = "seccion",
) -> pd.DataFrame:
    """
    Participación (%) de cada rama en el total provincial, para un año.
    nivel='seccion' → usa códigos de 1 letra (A, B, C...)
    nivel='rama'    → usa códigos numéricos (1..9999)
    """
    d = df[df["anio"] == anio].copy()
    if nivel == "seccion":
        d = d[d["Ramas"].str.match(r"^[A-Z]$", na=False)]
    elif nivel == "rama":
        d = d[d["Ramas"].str.match(r"^\d{1,4}$", na=False)]

    total = d.groupby("provincia")["empresas"].transform("sum")
    d["participacion"] = d["empresas"] / total * 100
    return (d[["provincia", "Ramas", "Descripción",
               "anio", "empresas", "participacion"]]
            .sort_values(["provincia", "participacion"],
                         ascending=[True, False])
            .reset_index(drop=True))


def empresas_total_provincia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve el total de empresas por provincia y año, sumando
    SÓLO las secciones (códigos de 1 letra A-Z) para evitar
    doble conteo con las sub-ramas.

    Devuelve: provincia | anio | empresas | var_ia
    """
    sec = df[df["Ramas"].str.match(r"^[A-Z]$", na=False)].copy()
    tot = (sec.groupby(["provincia", "anio"])["empresas"]
              .sum().reset_index())
    tot = tot.sort_values(["provincia", "anio"]).copy()
    tot["var_ia"] = (
        tot.groupby("provincia")["empresas"].pct_change() * 100
    )
    return tot.reset_index(drop=True)


# ============================================================
# Utilidades de cobertura temporal
# ============================================================

def ultimo_anio_comun(df: pd.DataFrame,
                      col_prov: str = "provincia",
                      col_anio: str = "anio") -> int | None:
    """
    Devuelve el último año para el cual TODAS las provincias
    del df tienen datos (empresas no nulas).
    """
    provincias = df[col_prov].dropna().unique()
    ultimos = []
    for p in provincias:
        anios = df[(df[col_prov] == p) &
                   (df["empresas"].notna())][col_anio]
        if len(anios):
            ultimos.append(anios.max())
    return int(min(ultimos)) if ultimos else None


def anios_faltantes_por_provincia(df: pd.DataFrame,
                                  anio_min: int = 1996,
                                  anio_max: int = 2025) -> pd.DataFrame:
    """
    Devuelve una tabla provincia × año indicando qué años faltan
    respecto del rango esperado. Útil para documentar huecos en
    la fuente (ej. CABA no tiene 2023).
    """
    esperados = set(range(anio_min, anio_max + 1))
    out = []
    for p, g in df.groupby("provincia"):
        presentes = set(g["anio"].dropna().astype(int).unique())
        faltan = sorted(esperados - presentes)
        out.append({"provincia": p,
                    "anios_faltantes": faltan,
                    "n_faltantes": len(faltan)})
    return pd.DataFrame(out).sort_values("provincia").reset_index(drop=True)