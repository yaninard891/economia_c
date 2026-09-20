# -*- coding: utf-8 -*-
"""
Empleo EC — La Rioja (CIIU 4 dígitos, alineado con prima_salarial.py).

Lee el archivo provinciales_serie_empleo_trimestral_4dig_7.xlsx del
SIPA-OEDE y devuelve el empleo de los CIIU del núcleo informático
{7210, 7220, 7290} para La Rioja.

Estructura del archivo:
    - Header en fila 6 (0-indexed).
    - Col 0: código CIIU (int).
    - Col 1: descripción de la rama.
    - Col 2+: valores trimestrales ('1° Trim 1996', '2° Trim 1996', ...).
    - Datos desde fila 8.

Salida:
    data/processed/empleo_ec_rioja.xlsx (columna empleo_ec_prom por año).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Rutas y definiciones
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent

RUTA_EMPLEO_4DIG = (
    RAIZ / "data" / "raw"
    / "provinciales_serie_empleo_trimestral_4dig_7.xlsx"
)

RUTA_SALIDA_DEFAULT = (
    RAIZ / "data" / "processed" / "empleo_ec_rioja.xlsx"
)

# Definiciones alineadas con prima_salarial.py
CIIU_NUCLEO_INFORMATICO = {7210, 7220, 7290}
CIIU_NUCLEO_AMPLIO      = {7210, 7220, 7290, 7300, 7430}
CIIU_COMPLETO           = {7210, 7220, 7250, 7290, 7300, 7421, 7430, 7499}

MAPA_DEFINICIONES = {
    "nucleo":   CIIU_NUCLEO_INFORMATICO,
    "amplio":   CIIU_NUCLEO_AMPLIO,
    "completo": CIIU_COMPLETO,
}

NOMBRES_CIIU = {
    7210: "Consultores en equipos / I+D ing.",
    7220: "Consultores informáticos",
    7250: "Reparación de equipos",
    7290: "Informática n.c.p.",
    7300: "Investigación y desarrollo",
    7421: "Arquitectura e ingeniería (proxy)",
    7430: "Publicidad",
    7499: "Servicios empresariales (proxy)",
}


# ---------------------------------------------------------------------------
# Parser del trimestre
# ---------------------------------------------------------------------------
def _trim_a_anio_trim(col):
    """'1° Trim 1996' -> (1996, 1). Devuelve (None, None) si no matchea."""
    if col is None:
        return None, None
    s = str(col).strip()
    if not s or s.lower() in ("nan", "none", ""):
        return None, None
    m = re.search(r"(\d)\s*[°º]?\s*Trim\s*(\d{4})", s, re.IGNORECASE)
    if m:
        return int(m.group(2)), int(m.group(1))
    return None, None


# ---------------------------------------------------------------------------
# Parser del archivo
# ---------------------------------------------------------------------------
def parsear_empleo_4dig(ruta=None, hoja: str = "La Rioja") -> pd.DataFrame:
    """
    Parsea el archivo de empleo trimestral 4 dígitos.

    Devuelve DataFrame largo: [ciiu, rama, anio, trimestre, empleo].
    """
    if ruta is None:
        ruta = RUTA_EMPLEO_4DIG
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")

    # Leer sin header
    raw = pd.read_excel(ruta, sheet_name=hoja, header=None)

    # Buscar fila del header: donde col0 == "Ramas"
    header_row = None
    for i in range(min(15, len(raw))):
        v = str(raw.iloc[i, 0]).strip().lower()
        if v == "ramas":
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"No se encontró la fila 'Ramas' en la hoja '{hoja}'.")

    data_start = header_row + 1
    # Saltar filas NaN después del header
    while data_start < len(raw) and pd.isna(raw.iloc[data_start, 0]):
        data_start += 1

    # Leer columnas de período desde el header
    cols_periodo = []
    for j in range(2, raw.shape[1]):
        anio, trim = _trim_a_anio_trim(raw.iloc[header_row, j])
        if anio is not None:
            cols_periodo.append((j, anio, trim))

    if not cols_periodo:
        raise ValueError(f"No se detectaron columnas de trimestre en '{hoja}'.")

    # Cuerpo
    cuerpo = raw.iloc[data_start:].copy().reset_index(drop=True)
    cuerpo = cuerpo.rename(columns={0: "ciiu_raw", 1: "rama"})

    # Normalizar CIIU
    cuerpo["ciiu"] = pd.to_numeric(cuerpo["ciiu_raw"], errors="coerce")
    cuerpo = cuerpo.dropna(subset=["ciiu"]).copy()
    cuerpo["ciiu"] = cuerpo["ciiu"].astype(int)
    cuerpo["rama"] = cuerpo["rama"].astype(str).str.strip()

    # Melt a largo
    registros = []
    for j, anio, trim in cols_periodo:
        tmp = cuerpo[["ciiu", "rama", j]].copy()
        tmp.columns = ["ciiu", "rama", "empleo"]
        tmp["anio"] = anio
        tmp["trimestre"] = trim
        registros.append(tmp)

    largo = pd.concat(registros, ignore_index=True)
    largo["empleo"] = pd.to_numeric(largo["empleo"], errors="coerce")
    largo = largo.dropna(subset=["empleo"])
    largo = largo[largo["empleo"] > 0]

    largo = (largo[["ciiu", "rama", "anio", "trimestre", "empleo"]]
             .sort_values(["anio", "trimestre", "ciiu"])
             .reset_index(drop=True))
    return largo


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def empleo_por_ciiu(
    anio: int | None = None,
    trimestre: int | None = None,
    prov: str = "La Rioja",
    definicion: str = "completo",
) -> pd.DataFrame:
    """
    Empleo por CIIU para un trimestre (o el último disponible del año).

    Devuelve DataFrame[ciiu, rama, empleo, anio, trimestre].
    Incluye los CIIU sin dato con empleo=NaN.
    """
    if definicion not in MAPA_DEFINICIONES:
        raise ValueError(
            f"definicion inválida: {definicion!r}. "
            f"Opciones: {list(MAPA_DEFINICIONES.keys())}"
        )
    codigos = MAPA_DEFINICIONES[definicion]

    df = parsear_empleo_4dig(hoja=prov)

    # Último año si no se especifica
    anios_disponibles = sorted(df["anio"].unique())
    anio_uso = anio if anio in anios_disponibles else anios_disponibles[-1]
    df_anio = df[df["anio"] == anio_uso]

    # Último trimestre del año si no se especifica
    trims_disponibles = sorted(df_anio["trimestre"].unique())
    if trimestre is None or trimestre not in trims_disponibles:
        trim_uso = trims_disponibles[-1]
    else:
        trim_uso = trimestre

    df_trim = df_anio[df_anio["trimestre"] == trim_uso].copy()
    df_def = df_trim[df_trim["ciiu"].isin(codigos)].copy()

    # Rellenar CIIU sin dato
    presentes = set(df_def["ciiu"].unique())
    faltantes = sorted(codigos - presentes)
    if faltantes:
        df_falt = pd.DataFrame({
            "ciiu":      faltantes,
            "rama":      [NOMBRES_CIIU.get(c, f"CIIU {c}") for c in faltantes],
            "empleo":    np.nan,
            "anio":      anio_uso,
            "trimestre": trim_uso,
        })
        df_def = pd.concat([df_def, df_falt], ignore_index=True)

    df_def = (df_def
              .sort_values("empleo", ascending=False, na_position="last")
              .reset_index(drop=True))

    return df_def[["ciiu", "rama", "empleo", "anio", "trimestre"]]


def empleo_ec_por_anio(
    prov: str = "La Rioja",
    definicion: str = "completo",
) -> pd.DataFrame:
    """
    Serie anual de empleo EC (promedio de los 4 trimestres).

    Devuelve DataFrame[anio, empleo_ec_prom].
    """
    codigos = MAPA_DEFINICIONES[definicion]
    df = parsear_empleo_4dig(hoja=prov)
    df = df[df["ciiu"].isin(codigos)].copy()

    # Promedio anual: primero promedio por año-trimestre, luego por año
    out = (df.groupby(["anio", "trimestre"], as_index=False)["empleo"].sum()
             .groupby("anio", as_index=False)["empleo"].mean()
             .rename(columns={"empleo": "empleo_ec_prom"})
             .sort_values("anio")
             .reset_index(drop=True))
    return out


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------
def exportar_excel(ruta_salida=None, definicion: str = "completo") -> Path:
    """Exporta la serie anual a data/processed/empleo_ec_rioja.xlsx."""
    if ruta_salida is None:
        ruta_salida = RUTA_SALIDA_DEFAULT
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    serie = empleo_ec_por_anio(definicion=definicion)
    serie.to_excel(ruta_salida, index=False)
    print(f"[OK] Exportado: {ruta_salida}")
    print(f"     Definición: {definicion}")
    print(f"     Filas: {len(serie)}")
    return ruta_salida


# ---------------------------------------------------------------------------
# Ejecución directa
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Empleo EC — La Rioja (CIIU 4 dígitos) ===\n")

    print("--- Empleo por CIIU (último trimestre disponible) ---")
    df = empleo_por_ciiu(definicion="completo")
    print(df.to_string(index=False))

    print("\n--- Empleo anual (definición completa) ---")
    serie = empleo_ec_por_anio(definicion="completo")
    print(serie.tail(10).to_string(index=False))

    print("\n--- Exportando Excel ---")
    exportar_excel()
    print("\n[OK] Listo.")