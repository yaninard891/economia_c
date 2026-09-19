"""
src/recaudacion_ec.py
=====================

Análisis fiscal de La Rioja a partir del archivo DNAP/CEPA:
    data/raw/Series_RecaudacionProvincial_webversion-3.xlsx

Provee:
  - Series mensuales y anuales de recaudación total y por tributo (La Rioja)
  - Cálculo del share de la Recaudación EC sobre Ingresos Brutos
  - Variaciones nominales y reales

Definición vigente:
  Recaudación EC = porción de II.BB correspondiente a Actividades de
  Economía del Conocimiento (ver src/empresas_ec.CIIU_EC).

Fuente Recaudación EC (dato duro):
  DGIP La Rioja — padrón de contribuyentes por régimen (2022-2025).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

_RAIZ = Path(__file__).resolve().parent.parent
RUTA_RECAUD = _RAIZ / "data" / "raw" / "Series_RecaudacionProvincial_webversion-3.xlsx"
RUTA_PROCESSED = _RAIZ / "data" / "processed"

# Jurisdicciones válidas (excluye fila TOTAL, notas, encabezados repetidos)
_JURISDICCIONES_VALIDAS = {
    "Buenos Aires", "CABA", "Catamarca", "Chaco", "Chubut", "Córdoba",
    "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja",
    "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan",
    "San Luis", "Santa Cruz", "Santa Fe", "S del Estero", "Santiago del Estero",
    "T del Fuego", "Tucumán",
}

# Hojas disponibles en el archivo: alias → nombre real
HOJAS = {
    "total": "TOTAL",
    "iibb": "II.BB",
    "inmobiliario": "INMOBILIARIO",
    "automotor": "AUTOMOTOR",
    "sellos": "SELLOS",
    "otros": "OTROS",
}

# ---------------------------------------------------------------------------
# Recaudación EC (dato duro DGIP La Rioja)
# ---------------------------------------------------------------------------

# Valores en millones de pesos corrientes.
# Fuente: DGIP La Rioja, padrón por régimen de tributación.
RECAUDACION_EC = {
    2022: 58.99,
    2023: 243.01,
    2024: 846.13,
    2025: 1940.91,
}

CONTRIBUYENTES_EC = {
    # año: (convenio_multilateral, locales)
    2022: (1752, 1138),
    2023: (1911, 1060),
    2024: (1947, 844),
    2025: (2075, 840),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolver_hoja(hoja: str) -> str:
    """Acepta alias ('iibb', 'total') o nombre real ('II.BB', 'TOTAL')."""
    if hoja in HOJAS:
        return HOJAS[hoja]
    if hoja in HOJAS.values():
        return hoja
    raise ValueError(
        f"Hoja inválida: {hoja}. "
        f"Alias: {list(HOJAS.keys())} | Reales: {list(HOJAS.values())}"
    )


def _normalizar_jurisdiccion(s: str) -> str:
    """Unifica variantes de nombres (S del Estero → Santiago del Estero)."""
    s = str(s).strip()
    if s == "S del Estero":
        return "Santiago del Estero"
    return s


# ---------------------------------------------------------------------------
# Carga y limpieza
# ---------------------------------------------------------------------------

def cargar_hoja(hoja: str = "TOTAL") -> pd.DataFrame:
    """
    Carga una hoja del archivo DNAP.

    Las hojas del archivo tienen DOS tablas apiladas:
      - Tabla 1 (valores absolutos en millones de $ corrientes)
      - Tabla 2 (participación % por provincia, con fórmulas)

    Esta función devuelve solo la Tabla 1.

    Devuelve un DataFrame tidy con:
        provincia | fecha | valor
    """
    hoja_real = _resolver_hoja(hoja)

    raw = pd.read_excel(RUTA_RECAUD, sheet_name=hoja_real,
                        header=0, engine="openpyxl")

    # La primera columna es la jurisdicción (nombre variable según hoja)
    col_juris = raw.columns[0]
    raw = raw.rename(columns={col_juris: "provincia"})

    # Normalizar nombres
    raw["provincia"] = raw["provincia"].map(_normalizar_jurisdiccion)

    # Filtrar solo jurisdicciones válidas (excluye TOTAL, notas, NaN)
    raw = raw[raw["provincia"].isin(_JURISDICCIONES_VALIDAS)].copy()

    # ⚠️ IMPORTANTE: la Tabla 2 repite las mismas jurisdicciones apiladas
    # abajo. Nos quedamos SOLO con la primera aparición de cada una
    # (= Tabla 1, valores absolutos).
    raw = raw.drop_duplicates(subset=["provincia"], keep="first").copy()

    # Melt: pasar columnas fecha a filas
    cols_fecha = [c for c in raw.columns if c != "provincia"]
    tidy = raw.melt(id_vars="provincia", value_vars=cols_fecha,
                    var_name="fecha", value_name="valor")

    # Parsear fecha
    tidy["fecha"] = pd.to_datetime(tidy["fecha"], errors="coerce")
    tidy = tidy.dropna(subset=["fecha"])

    # Convertir valor a numérico (los "s.d" y "=" van a quedar NaN)
    tidy["valor"] = pd.to_numeric(tidy["valor"], errors="coerce")

    tidy["anio"] = tidy["fecha"].dt.year
    tidy["mes"] = tidy["fecha"].dt.month

    return tidy[["provincia", "fecha", "anio", "mes", "valor"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Series por provincia
# ---------------------------------------------------------------------------

def serie_mensual(provincia: str = "La Rioja", hoja: str = "TOTAL") -> pd.DataFrame:
    """Serie mensual (valor en millones de $ corrientes)."""
    df = cargar_hoja(hoja)
    return (
        df[df["provincia"] == provincia]
        .sort_values("fecha")
        .reset_index(drop=True)
    )


def serie_anual(provincia: str = "La Rioja", hoja: str = "TOTAL") -> pd.DataFrame:
    """Suma anual (solo años con al menos 1 mes con dato)."""
    df = serie_mensual(provincia, hoja)
    anual = (
        df.groupby("anio", as_index=False)
        .agg(valor=("valor", "sum"),
             n_meses=("valor", "count"))
    )
    anual = anual[anual["n_meses"] >= 1].reset_index(drop=True)
    return anual


def serie_anual_multi(provincia: str = "La Rioja") -> pd.DataFrame:
    """DataFrame con todos los tributos en columnas, año en índice."""
    out = {}
    for nombre, hoja_real in HOJAS.items():
        out[nombre] = serie_anual(provincia, hoja_real).set_index("anio")["valor"]
    return pd.DataFrame(out).sort_index()


def variacion_nominal(anual: pd.DataFrame, col: str = "valor") -> pd.DataFrame:
    """Agrega columna con variación % nominal i.a."""
    df = anual.copy()
    df["var_nominal_pct"] = df[col].pct_change().mul(100).round(2)
    return df


# ---------------------------------------------------------------------------
# Recaudación EC y share sobre II.BB
# ---------------------------------------------------------------------------

def serie_recaudacion_ec() -> pd.DataFrame:
    """Serie anual de Recaudación EC (dato duro DGIP)."""
    return (
        pd.DataFrame({
            "anio": list(RECAUDACION_EC.keys()),
            "recaudacion_ec_mm": list(RECAUDACION_EC.values()),
        })
        .assign(
            contrib_multilateral=lambda d: d["anio"].map(
                {k: v[0] for k, v in CONTRIBUYENTES_EC.items()}),
            contrib_locales=lambda d: d["anio"].map(
                {k: v[1] for k, v in CONTRIBUYENTES_EC.items()}),
        )
        .assign(
            contrib_total=lambda d: d["contrib_multilateral"] + d["contrib_locales"],
            share_multilateral=lambda d: (
                d["contrib_multilateral"] / d["contrib_total"] * 100).round(1),
            var_nominal_pct=lambda d: d["recaudacion_ec_mm"].pct_change().mul(100).round(2),
        )
    )


def share_ec_iibb(provincia: str = "La Rioja",
                  anio: int = 2025) -> dict:
    """
    Calcula el peso de la Recaudación EC sobre II.BB de la provincia
    en un año dado.

    Devuelve dict con:
        anio, iibb_mm, recaudacion_ec_mm, share_pct
    """
    iibb = serie_anual(provincia, "II.BB")
    row = iibb[iibb["anio"] == anio]
    if row.empty:
        raise ValueError(f"Sin datos de II.BB para {provincia} en {anio}")
    iibb_anual = float(row["valor"].iloc[0])

    if anio not in RECAUDACION_EC:
        raise ValueError(f"Sin dato de Recaudación EC para {anio}")

    ec = RECAUDACION_EC[anio]
    return {
        "anio": anio,
        "iibb_mm": round(iibb_anual, 2),
        "recaudacion_ec_mm": ec,
        "share_pct": round(ec / iibb_anual * 100, 2),
    }


def share_ec_iibb_serie(provincia: str = "La Rioja") -> pd.DataFrame:
    """Serie 2022-2025 del share EC sobre II.BB."""
    iibb = serie_anual(provincia, "II.BB").set_index("anio")["valor"]
    filas = []
    for anio, ec in RECAUDACION_EC.items():
        if anio in iibb.index:
            iibb_anio = float(iibb.loc[anio])
            filas.append({
                "anio": anio,
                "iibb_mm": round(iibb_anio, 2),
                "recaudacion_ec_mm": ec,
                "share_pct": round(ec / iibb_anio * 100, 2),
            })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def exportar_excel(ruta_salida: Path | None = None) -> Path:
    """
    Exporta a data/processed/recaudacion_ec_rioja.xlsx:
      - total_mensual
      - iibb_mensual
      - tributos_anual
      - share_ec_iibb
    """
    RUTA_PROCESSED.mkdir(exist_ok=True)
    ruta = ruta_salida or (RUTA_PROCESSED / "recaudacion_ec_rioja.xlsx")

    with pd.ExcelWriter(ruta, engine="openpyxl") as w:
        serie_mensual("La Rioja", "TOTAL").to_excel(w, sheet_name="total_mensual", index=False)
        serie_mensual("La Rioja", "II.BB").to_excel(w, sheet_name="iibb_mensual", index=False)
        serie_anual_multi("La Rioja").to_excel(w, sheet_name="tributos_anual")
        share_ec_iibb_serie().to_excel(w, sheet_name="share_ec_iibb", index=False)

    return ruta


# ---------------------------------------------------------------------------
# CLI rápido
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Serie anual La Rioja (millones $ corrientes) ===")
    print(serie_anual_multi("La Rioja").tail(6))

    print("\n=== Recaudación EC 2022-2025 ===")
    print(serie_recaudacion_ec())

    print("\n=== Share EC sobre II.BB ===")
    print(share_ec_iibb_serie())

    print("\n=== II.BB mensual La Rioja — últimos 18 meses ===")
    iibb_m = serie_mensual("La Rioja", "II.BB").tail(18)
    print(iibb_m[["fecha", "valor"]].to_string(index=False))