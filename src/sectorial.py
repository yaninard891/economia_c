"""
Módulo de análisis sectorial comparado para La Rioja.

Compara la evolución de los sectores CIIU (incluyendo Economía del
Conocimiento) en términos de empleo, empresas y salarios reales.

Fuentes:
- src.empleo (empleo, salarios OEDE y SIPA)
- src.funciones (IPC NOA para deflactar)

Uso típico:
    import src.sectorial as sec
    df = sec.serie_anual_por_seccion("La Rioja")
    idx = sec.indice_base100(df, base_anio=2003)
    cg = sec.cagr(df, desde=2003, hasta=2025)
"""
from pathlib import Path
import pandas as pd
import numpy as np

from .empleo import (
    cargar_empleo_sector_provincia,
    cargar_remuneraciones_sector_provincia,
    cargar_empresas_sipa,
    _norm_prov,
)

# ------------------------------------------------------------------
# Metadatos de secciones CIIU rev 3
# ------------------------------------------------------------------
SECCIONES_NOMBRES = {
    "A": "Agricultura, ganadería y pesca",
    "C": "Minería y petróleo",
    "D": "Industria manufacturera",
    "E": "Electricidad, gas y agua",
    "F": "Construcción",
    "G": "Comercio mayorista y minorista",
    "H": "Hotelería y restaurantes",
    "I": "Transporte y comunicaciones",
    "J": "Intermediación financiera",
    "K": "Servicios inmobiliarios y empresariales",
    "M": "Enseñanza",
    "N": "Servicios sociales y de salud",
    "O": "Servicios comunitarios y personales",
}

SECCIONES_COLORES = {
    "A": "#7fb069", "C": "#8b6f47", "D": "#e8a33d", "E": "#c4a35a",
    "F": "#b5651d", "G": "#d65a4a", "H": "#d47b8f", "I": "#5b8fb9",
    "J": "#2e5266", "K": "#7a4f9e", "M": "#4a9d7e", "N": "#5ba3b9",
    "O": "#9b7fa3", "EC": "#2c7a4b", "TIC": "#1a4d2e",
}

# Sectores sintéticos
SECTOR_EC  = "EC"
SECTOR_TIC = "TIC"

_DIVISIONES_EC  = {"64", "72", "73", "74"}
_DIVISIONES_TIC = {"64", "72"}

_EC_NOMBRE  = "Economía del Conocimiento"
_TIC_NOMBRE = "TIC núcleo"


# ==================================================================
# Serie base — anual por sección (+ EC/TIC sintéticos)
# ==================================================================

def serie_anual_por_seccion(provincia="La Rioja", agrupar_ec=True):
    """
    Serie anual por sección CIIU: puestos, empresas y salario promedio.

    Si agrupar_ec=True, agrega dos "secciones" sintéticas:
      - 'EC':  suma de divisiones 64, 72, 73, 74
      - 'TIC': suma de divisiones 64, 72

    Returns
    -------
    DataFrame: provincia | codigo | sector | anio | puestos | empresas | salario_prom
    """
    # --- Secciones reales ---
    emp = cargar_empleo_sector_provincia(provincia, solo_nivel="seccion")
    emp = emp.assign(anio=emp["fecha"].dt.year)
    emp_anual = emp.groupby(["codigo", "anio"], as_index=False)["puestos"].mean()

    sipa = cargar_empresas_sipa(provincia)
    empr_anual = (sipa[sipa["codigo"].str.isalpha()]
                  [["codigo", "anio", "empresas"]])

    sal = cargar_remuneraciones_sector_provincia(
        provincia, nivel="2dig", frecuencia="mensual", solo_nivel="seccion")
    sal = sal.assign(anio=sal["fecha"].dt.year)
    sal_anual = (sal.groupby(["codigo", "anio"], as_index=False)
                 ["remuneracion_prom"].mean())

    out = (emp_anual
           .merge(empr_anual, on=["codigo", "anio"], how="left")
           .merge(sal_anual, on=["codigo", "anio"], how="left"))
    out = out.rename(columns={"remuneracion_prom": "salario_prom"})
    out["sector"] = out["codigo"].map(SECCIONES_NOMBRES).fillna(out["codigo"])

    # --- Sectores sintéticos EC y TIC ---
    if agrupar_ec:
        for nombre, divs, etiqueta in [
            (SECTOR_EC,  _DIVISIONES_EC,  _EC_NOMBRE),
            (SECTOR_TIC, _DIVISIONES_TIC, _TIC_NOMBRE),
        ]:
            df_div = _serie_anual_divisiones(provincia, divs)
            df_div["codigo"] = nombre
            df_div["sector"] = etiqueta
            out = pd.concat([out, df_div], ignore_index=True)

    out["provincia"] = _norm_prov(provincia)
    return (out[["provincia", "codigo", "sector", "anio",
                 "puestos", "empresas", "salario_prom"]]
            .sort_values(["codigo", "anio"])
            .reset_index(drop=True))


def _serie_anual_divisiones(provincia, codigos):
    """
    Helper: agrega empleo, empresas y salario a nivel división.

    Empleo: SUMAR divisiones por trimestre, LUEGO promediar trimestres.
    Esto evita promediar divisiones entre sí (que daría la mitad del valor).
    """
    # ---------- EMPLEO: doble agregación ----------
    emp = cargar_empleo_sector_provincia(provincia, solo_nivel="division")
    emp = emp[emp["codigo"].isin(codigos)].copy()
    emp["anio"] = emp["fecha"].dt.year
    # Paso 1: sumar divisiones → total por (anio, fecha)
    por_trim = (emp.groupby(["anio", "fecha"], as_index=False)["puestos"]
                .sum())
    # Paso 2: promediar los trimestres → total anual
    emp_anual = (por_trim.groupby("anio", as_index=False)["puestos"]
                 .mean())

    # ---------- EMPRESAS: sumar divisiones (SIPA es anual) ----------
    sipa = cargar_empresas_sipa(provincia)
    sipa = sipa[sipa["codigo"].isin(codigos)].copy()
    empr_anual = sipa.groupby("anio", as_index=False)["empresas"].sum()

    # ---------- SALARIO: promedio simple de divisiones ----------
    sal = cargar_remuneraciones_sector_provincia(
        provincia, nivel="2dig", frecuencia="mensual", solo_nivel="division")
    sal = sal[sal["codigo"].isin(codigos)].copy()
    sal["anio"] = sal["fecha"].dt.year
    sal_anual = (sal.groupby("anio", as_index=False)
                 .agg(salario_prom=("remuneracion_prom", "mean")))

    return (emp_anual
            .merge(empr_anual, on="anio", how="outer")
            .merge(sal_anual, on="anio", how="outer"))


# ==================================================================
# Índices y tasas
# ==================================================================

def indice_base100(df, base_anio, valor="puestos", grupo="codigo"):
    """Índice base 100 en base_anio para cada grupo (sector)."""
    df = df.copy()
    base = (df[df["anio"] == base_anio]
            .set_index(grupo)[valor].rename("base"))
    df = df.join(base, on=grupo)
    df["indice"] = 100 * df[valor] / df["base"]
    return df.drop(columns="base")


def cagr(df, desde, hasta, valor="puestos", grupo="codigo"):
    """Tasa de crecimiento anual compuesta entre dos años."""
    d = df[df["anio"].isin([desde, hasta])].copy()
    piv = (d.pivot_table(index=["codigo", "sector"], columns="anio",
                         values=valor, aggfunc="mean")
           .reset_index())
    piv.columns.name = None
    piv = piv.rename(columns={desde: "v_desde", hasta: "v_hasta"})
    piv["n_anios"] = hasta - desde
    piv["cagr_pct"] = 100 * ((piv["v_hasta"] / piv["v_desde"]) ** (1 / piv["n_anios"]) - 1)
    return piv.sort_values("cagr_pct", ascending=False).reset_index(drop=True)


def share_sectorial(df, valor="puestos"):
    """Share % de cada sección sobre el total por año (excluye EC/TIC)."""
    d = df[df["codigo"].str.len() == 1].copy()
    total = d.groupby("anio", as_index=False)[valor].sum().rename(
        columns={valor: "total"})
    d = d.merge(total, on="anio")
    d["share_pct"] = 100 * d[valor] / d["total"]
    return d


# ==================================================================
# Salarios reales
# ==================================================================

def salario_real_por_seccion(provincia="La Rioja", df_ipc=None,
                              region_ipc="Región Noroeste", base_anio=None):
    """Salario real por sección (deflactado por IPC)."""
    if df_ipc is None:
        from .funciones import cargar_ipc_regional
        df_ipc = cargar_ipc_regional()

    ipc = (df_ipc.query(f"region == '{region_ipc}' and categoria == 'Nivel general'")
                 [["fecha", "valor"]].rename(columns={"valor": "ipc"}))
    ipc["anio"] = ipc["fecha"].dt.year
    ipc_anual = ipc.groupby("anio", as_index=False)["ipc"].mean()

    sal = cargar_remuneraciones_sector_provincia(
        provincia, nivel="2dig", frecuencia="mensual", solo_nivel="seccion")
    sal = sal.assign(anio=sal["fecha"].dt.year)
    sal_anual = (sal.groupby(["codigo", "anio"], as_index=False)
                 .agg(salario_prom=("remuneracion_prom", "mean")))

    m = sal_anual.merge(ipc_anual, on="anio", how="left")
    m["salario_real"] = m["salario_prom"] / m["ipc"]
    m["sector"] = m["codigo"].map(SECCIONES_NOMBRES).fillna(m["codigo"])
    m["provincia"] = _norm_prov(provincia)

    if base_anio is not None:
        base = (m[m["anio"] == base_anio]
                .set_index("codigo")["salario_real"].rename("base"))
        m = m.join(base, on="codigo")
        m["indice_real"] = 100 * m["salario_real"] / m["base"]

    return m.sort_values(["codigo", "anio"]).reset_index(drop=True)


# ==================================================================
# Benchmark interprovincial
# ==================================================================

def benchmark_sectorial(provincias, codigo_seccion, desde=None, hasta=None,
                        valor="puestos"):
    """Compara un sector entre provincias."""
    frames = []
    for p in provincias:
        try:
            df = serie_anual_por_seccion(p, agrupar_ec=True)
            df = df[df["codigo"] == codigo_seccion]
            frames.append(df)
        except Exception as e:
            print(f"⚠️ {p}: {e}")
    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    if desde is not None:
        out = out[out["anio"] >= desde]
    if hasta is not None:
        out = out[out["anio"] <= hasta]
    return out.sort_values(["provincia", "anio"]).reset_index(drop=True)


def benchmark_pivot(provincias, codigo_seccion, valor="puestos", anios=None):
    """Vista compacta provincia × año."""
    df = benchmark_sectorial(provincias, codigo_seccion, valor=valor)
    if df.empty:
        return df
    if anios is not None:
        df = df[df["anio"].isin(anios)]
    piv = df.pivot_table(index="provincia", columns="anio",
                         values=valor, aggfunc="mean")
    piv.columns = [int(c) for c in piv.columns]
    return piv.round(0)


# ==================================================================
# Exportación para dashboard
# ==================================================================

def exportar_json_dashboard(provincia="La Rioja",
                             path_salida="data/processed/sectorial.json"):
    """Empaqueta los análisis en un JSON listo para el dashboard."""
    import json
    from pathlib import Path as _P

    df = serie_anual_por_seccion(provincia)
    df_25 = df[df["anio"] >= 2003].copy()

    idx = indice_base100(df_25, base_anio=2003, valor="puestos")
    idx_wide = idx.pivot_table(index="anio", columns="codigo",
                                values="indice", aggfunc="mean")

    cg = cagr(df, desde=2003, hasta=2025, valor="puestos")

    sh = share_sectorial(df)
    sh_wide = sh.pivot_table(index="anio", columns="codigo",
                              values="share_pct", aggfunc="mean")

    payload = {
        "provincia": provincia,
        "anios": [int(a) for a in idx_wide.index.tolist()],
        "indice_base2003_empleo": {
            str(col): idx_wide[col].round(1).tolist()
            for col in idx_wide.columns
        },
        "cagr_2003_2025": cg.to_dict(orient="records"),
        "share_empleo": {
            str(col): sh_wide[col].round(2).tolist()
            for col in sh_wide.columns
        },
    }

    _P(path_salida).parent.mkdir(parents=True, exist_ok=True)
    with open(path_salida, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path_salida