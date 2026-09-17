"""OPEX (VAB provincial) y EMAE (actividad nacional) — INDEC.

Fuentes
-------
- sh_opex_regiones_economicas_provincias_1993_2025.xls
  VAB a precios corrientes, millones de USD, 1993-2025 (9 hojas).
- sh_emae_actividad_base2004.xls
  Índice mensual base 2004=100, apertura por letras CIIU rev 3.

Advertencias
------------
- OPEX es VAB TOTAL provincial: NO tiene apertura sectorial. Para
  "%EC del VAB" haría falta el PBG sectorial (otra fuente, no en raw/).
- EMAE 'Tabla Letras' NO trae un total explícito: la última columna es
  'Impuestos netos de subsidios'. El total mensual va por
  sh_emae_mensual_base2004.xls (ver cargar_emae_mensual, por confirmar).
- CIIU rev 3: la EC núcleo (div 64) vive en la letra I
  ('Transporte y comunicaciones'); la EC ampliada (72+73+74) en la K
  ('Act. inmobiliarias, empresariales y de alquiler').
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from .config import PROVINCIA_FOCO, PROVINCIAS_BENCHMARK
except ImportError:  # ejecución suelta desde notebooks
    PROVINCIA_FOCO = "La Rioja"
    PROVINCIAS_BENCHMARK = [
        "Ciudad Autónoma de Buenos Aires",
        "Córdoba",
        "Santa Fe",
        "Tucumán",
    ]

RAW = Path("data/raw")

FILE_OPEX = "sh_opex_regiones_economicas_provincias_1993_2025.xls"
FILE_EMAE_ACT = "sh_emae_actividad_base2004.xls"
FILE_EMAE_MENS = "sh_emae_mensual_base2004.xls"

_REGIONES = {
    "Pampeana", "Patagonia", "Noroeste (NOA)", "Noreste (NEA)",
    "Cuyo", "Indeterminado",
}
_FOOTER_PREFIX = ("Nota:", "Fuente:", "Fecha de última actualización")
_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extraer_anio(v) -> int | None:
    """Extrae un año 1990-2030 de celdas tipo 1993, 1994.0, '2025*', '2004'."""
    if isinstance(v, (int, float)) and not pd.isna(v):
        iv = int(float(v))
        return iv if 1990 <= iv <= 2030 else None
    if isinstance(v, str):
        m = re.match(r"^(\d{4})", v.strip())
        if m:
            iv = int(m.group(1))
            return iv if 1990 <= iv <= 2030 else None
    return None


def _es_numero(v) -> bool:
    try:
        return not pd.isna(v) and float(v) == float(v)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# OPEX
# ---------------------------------------------------------------------------

def _parsear_hoja_opex(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Convierte una hoja OPEX (formato viejo 15-col o nuevo 8-col) a long.

    Estructura detectada:
      fila_unidad - 2 : header    ("Años", "Variación porcentual", ...)
      fila_unidad - 1 : subheader (años concretos)
      fila_unidad     : "Millones de USD"
      fila_unidad + 1 : primera fila de datos
    Los años viven entre el label "Años" y el label "Variación porcentual".
    """
    # 1) Localizar la fila de unidad ("Millones de USD")
    fila_unidad = None
    for i in range(min(12, len(df_raw))):
        if any(isinstance(v, str) and "Millones de USD" in v
               for v in df_raw.iloc[i].values):
            fila_unidad = i
            break
    if fila_unidad is None:
        raise ValueError("Hoja OPEX: no se encontró 'Millones de USD'")

    fila_header = fila_unidad - 2
    fila_sub = fila_unidad - 1
    if fila_header < 0 or fila_sub < 0:
        raise ValueError("Hoja OPEX: estructura de headers inesperada")

    # 2) Delimitar el bloque de años usando los labels del header
    header_vals = df_raw.iloc[fila_header].tolist()
    idx_anios = idx_var = None
    for i, c in enumerate(header_vals):
        if isinstance(c, str):
            cs = c.strip()
            if cs == "Años":
                idx_anios = i
            elif cs.startswith("Variación porcentual"):
                idx_var = i
                break
    if idx_anios is None or idx_var is None or idx_var <= idx_anios:
        raise ValueError(
            f"Hoja OPEX: no se pudo delimitar bloque de años "
            f"(idx_anios={idx_anios}, idx_var={idx_var})"
        )

    # 3) Años SOLO dentro del bloque [idx_anios, idx_var)
    anios_cols: dict[int, int] = {}
    for c in range(idx_anios, idx_var):
        a = _extraer_anio(df_raw.iat[fila_sub, c])
        if a is not None:
            anios_cols[c] = a
    if not anios_cols:
        raise ValueError("Hoja OPEX: no se detectaron columnas de años")

    # 4) Recortar filas de datos y footer
    datos = df_raw.iloc[fila_unidad + 1:].reset_index(drop=True)
    cortes = [i for i, v in enumerate(datos.iloc[:, 0])
              if isinstance(v, str) and v.startswith(_FOOTER_PREFIX)]
    if cortes:
        datos = datos.iloc[:cortes[0]].copy()

    col0 = datos.iloc[:, 0]
    col1 = datos.iloc[:, 1]
    region_ffill = col0.where(col0.isin(_REGIONES)).ffill()

    # 5) Clasificar nivel de cada fila
    nivel: list[str] = []
    for c1 in col1:
        if isinstance(c1, str) and c1.strip().lower() == "total":
            nivel.append("pais")
        elif pd.isna(c1):
            nivel.append("region")
        else:
            nivel.append("provincia")

    # 6) Melt solo sobre las columnas de años reales
    filas: list[dict] = []
    for c, anio in anios_cols.items():
        for i in range(len(datos)):
            v = datos.iat[i, c]
            if not _es_numero(v):
                continue
            reg = region_ffill.iloc[i]
            filas.append({
                "anio": int(anio),
                "nivel": nivel[i],
                "region": reg if pd.notna(reg) else None,
                "provincia": col1.iloc[i] if nivel[i] == "provincia" else None,
                "vab_musd": float(v),
            })
    return pd.DataFrame(filas)


def cargar_opex() -> pd.DataFrame:
    """VAB provincial 1993-2025 (millones USD corrientes, OPEX/INDEC).

    Columnas: anio, nivel ('pais'|'region'|'provincia'), region, provincia,
    vab_musd.
    """
    f = RAW / FILE_OPEX
    xl = pd.ExcelFile(f)
    partes = [
        _parsear_hoja_opex(pd.read_excel(f, sheet_name=s, header=None))
        for s in xl.sheet_names
    ]
    df = pd.concat(partes, ignore_index=True)

    # Sanity check: no debe haber (provincia, año) duplicados
    prov = df[df["nivel"] == "provincia"]
    dup = prov.duplicated(["anio", "provincia"], keep=False)
    if dup.any():
        ejemplo = prov[dup].head(8)[["anio", "provincia", "vab_musd"]]
        raise ValueError(
            f"OPEX: {dup.sum()} filas duplicadas (provincia, año). "
            f"Muestra:\n{ejemplo}"
        )

    return df.sort_values(["nivel", "provincia", "anio"]).reset_index(drop=True)


def opex_serie_provincia(provincia: str = PROVINCIA_FOCO) -> pd.DataFrame:
    """VAB anual + share del total país + yoy % para una provincia."""
    df = cargar_opex()
    pais = (df[df["nivel"] == "pais"][["anio", "vab_musd"]]
            .rename(columns={"vab_musd": "vab_pais_musd"}))
    prov = (df[(df["nivel"] == "provincia") & (df["provincia"] == provincia)]
            [["anio", "vab_musd"]].copy())
    out = prov.merge(pais, on="anio", how="left").sort_values("anio")
    out["share_pais_pct"] = 100 * out["vab_musd"] / out["vab_pais_musd"]
    out["yoy_pct"] = out["vab_musd"].pct_change() * 100
    return out.reset_index(drop=True)


def opex_benchmark(provincias: Iterable[str] | None = None) -> pd.DataFrame:
    """Serie comparativa en ancho: index=anio, cols=provincia."""
    if provincias is None:
        provincias = [PROVINCIA_FOCO, *PROVINCIAS_BENCHMARK]
    df = cargar_opex()
    sub = df[(df["nivel"] == "provincia") & df["provincia"].isin(provincias)]
    wide = (sub.pivot_table(index="anio", columns="provincia",
                            values="vab_musd", aggfunc="sum")
            .sort_index())
    return wide


# ---------------------------------------------------------------------------
# EMAE
# ---------------------------------------------------------------------------

def cargar_emae_tabla_letras() -> pd.DataFrame:
    """EMAE mensual por letras CIIU rev 3 (índice 2004=100).

    Long: fecha, anio, mes, letra, letra_desc, indice.
    La fila 'Impuestos netos de subsidios' queda con letra=None.
    """
    f = RAW / FILE_EMAE_ACT
    raw = pd.read_excel(f, sheet_name="Tabla Letras", header=None)

    # Headers en fila 2 (0-indexed), cols 2..17 son las letras (16 sectores)
    headers = raw.iloc[2].tolist()
    cols_datos = list(range(2, 18))
    nombres = [headers[c] for c in cols_datos]

    datos = raw.iloc[4:].copy()[[0, 1] + cols_datos]
    datos.columns = ["anio", "mes"] + nombres
    datos["anio"] = datos["anio"].ffill()

    datos = datos[datos["mes"].isin(_MESES)]
    long = datos.melt(id_vars=["anio", "mes"], var_name="letra_desc",
                     value_name="indice")
    long["letra"] = (long["letra_desc"].astype(str)
                     .str.extract(r"^([A-Z])\s*-", expand=False))
    long["anio"] = pd.to_numeric(long["anio"], errors="coerce").astype("Int64")
    long["mes_num"] = long["mes"].map({m: i + 1 for i, m in enumerate(_MESES)})
    long["fecha"] = pd.to_datetime(
        dict(year=long["anio"].astype("float"),
             month=long["mes_num"], day=1),
        errors="coerce",
    )
    long["indice"] = pd.to_numeric(long["indice"], errors="coerce")
    long = long.dropna(subset=["indice", "fecha"])
    return (long[["fecha", "anio", "mes", "letra", "letra_desc", "indice"]]
            .sort_values(["fecha", "letra"]).reset_index(drop=True))


def cargar_emae_mensual() -> pd.DataFrame:
    """EMAE total mensual (índice 2004=100). Estructura por confirmar."""
    f = RAW / FILE_EMAE_MENS
    raw = pd.read_excel(f, sheet_name="EMAE", header=None)
    # TODO: confirmar layout real de sh_emae_mensual_base2004.xls
    # (por ahora devuelve crudo para inspección)
    return raw


def emae_serie_letra(letra: str = "K") -> pd.DataFrame:
    """Serie mensual filtrada por una letra CIIU rev 3 (I, K, etc.)."""
    return (cargar_emae_tabla_letras()
            .query("letra == @letra")
            .reset_index(drop=True))