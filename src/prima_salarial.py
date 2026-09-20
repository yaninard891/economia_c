# -*- coding: utf-8 -*-
"""
Prima salarial del sector Economía del Conocimiento en La Rioja.

Compara el salario promedio del núcleo informático (CIIU 7210+7220+7290)
contra el salario provincial oficial ponderado por empleo (SIPA-OEDE).

Denominador CORRECTO:
    Salario privado formal provincial (SerieWeb SIPA) del MISMO mes/año
    que el salario por CIIU. Si no existe exacto, se busca el más cercano
    (±2 meses). Si no, promedio anual del año. NUNCA el último mes
    disponible (infla la prima por inflación).

Definiciones vigentes:
    CIIU_NUCLEO_INFORMATICO = {7210, 7220, 7290}
    CIIU_NUCLEO_AMPLIO      = {7210, 7220, 7290, 7300, 7430}
    CIIU_COMPLETO           = {7210, 7220, 7250, 7290, 7300, 7421, 7430, 7499}

Salida:
    data/processed/prima_salarial_ec.xlsx
        Hoja "prima_anual"       -> serie anual por definición
        Hoja "salario_por_ciiu"  -> salario por CIIU (último año, completo)
        Hoja "serie_mensual"     -> serie mensual por CIIU (completo)

Notas metodológicas:
    - CIIU 7210, 7300 y 7430 NO tienen dato de salario en SIPA (solo
      aportan al conteo de empleo). salario_por_ciiu() los devuelve con
      NaN para que aparezcan en el gráfico como "s/d".
    - La hoja SIPA tiene DOS filas de encabezado: una con "Ramas"/
      "Descripción" y otra con los períodos ("1995-01", etc.).
    - Consola Windows (cp1252): usar [OK] y [!], no emojis.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent

RUTA_REMUNERACIONES = (
    RAIZ / "data" / "raw"
    / "provinciales_serie_remuneraciones_mensual_4dig_7.xlsx"
)

RUTA_SALIDA_DEFAULT = (
    RAIZ / "data" / "processed" / "prima_salarial_ec.xlsx"
)

# ---------------------------------------------------------------------------
# Definiciones vigentes de CIIU
# ---------------------------------------------------------------------------
CIIU_NUCLEO_INFORMATICO = {7210, 7220, 7290}
CIIU_NUCLEO_AMPLIO      = {7210, 7220, 7290, 7300, 7430}
CIIU_COMPLETO           = {7210, 7220, 7250, 7290, 7300, 7421, 7430, 7499}

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

MAPA_DEFINICIONES = {
    "nucleo":   CIIU_NUCLEO_INFORMATICO,
    "amplio":   CIIU_NUCLEO_AMPLIO,
    "completo": CIIU_COMPLETO,
}

# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _norm_rama(x) -> str:
    """Convierte '111.0' -> '111' y devuelve string limpio."""
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _periodo_a_anio_mes(col):
    """Devuelve (anio, mes) si la celda representa un período.

    Acepta datetime, Timestamp, 'YYYY-MM', 'YYYYMM', 'Ene-19', etc.
    """
    if col is None:
        return None, None
    if isinstance(col, (pd.Timestamp, datetime.datetime, datetime.date)):
        return col.year, col.month
    try:
        if pd.isna(col):
            return None, None
    except (TypeError, ValueError):
        pass
    s = str(col).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return None, None

    s = re.sub(r"__\d+$", "", s)

    # YYYY-MM / YYYY_MM / YYYY/MM / YYYY.MM
    m = re.match(r"^((?:19|20)\d{2})[-_/\.](\d{1,2})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))

    # YYYYMM
    m = re.match(r"^((?:19|20)\d{2})(\d{2})$", s)
    if m:
        mm = int(m.group(2))
        if 1 <= mm <= 12:
            return int(m.group(1)), mm

    # Mes textual + año
    meses = {
        "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
        "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
    }
    low = s.lower()
    m = re.search(r"(19|20)\d{2}", low)
    if m:
        anio = int(m.group(0))
        for k, v in meses.items():
            if k in low:
                return anio, v
    return None, None


def _buscar_fila_header(raw: pd.DataFrame, max_filas: int = 20) -> int:
    """Busca la fila con 'CIIU'/'CLAE'/'CODIGO'/'Ramas'/'CÓDIGO'."""
    for i in range(min(max_filas, len(raw))):
        vals = raw.iloc[i].astype(str).str.upper().fillna("").tolist()
        txt = " ".join(vals)
        if ("CIIU" in txt) or ("CLAE" in txt) or ("CODIGO" in txt) \
                or ("CÓDIGO" in txt) or ("RAMAS" in txt) or ("COD." in txt):
            return i
    return 6


def _buscar_fila_periodos(raw: pd.DataFrame, cerca_de: int,
                          ventana: int = 4, min_periodos: int = 3):
    """Busca la fila con >= min_periodos fechas válidas, cerca de 'cerca_de'."""
    for offset in range(0, ventana + 1):
        for h in (cerca_de + offset, cerca_de - offset):
            if h < 0 or h >= len(raw):
                continue
            vals = raw.iloc[h].tolist()
            n = sum(1 for v in vals if _periodo_a_anio_mes(v)[0] is not None)
            if n >= min_periodos:
                return h
    return None


def _detectar_columnas(df: pd.DataFrame) -> tuple:
    """Devuelve (col_ciiu, col_rama) buscando en las 4 primeras columnas."""
    col_ciiu, col_rama = None, None
    for c in df.columns[:4]:
        serie = df[c].dropna().astype(str).str.strip()
        if serie.empty:
            continue
        matches = serie.str.match(r"^\d{3,4}(\.0)?$").sum()
        if matches >= 3 and col_ciiu is None:
            col_ciiu = c
        elif col_ciiu is not None and col_rama is None:
            col_rama = c
    if col_ciiu is None:
        col_ciiu = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    if col_rama is None:
        col_rama = df.columns[2] if len(df.columns) > 2 else col_ciiu
    return col_ciiu, col_rama


# ---------------------------------------------------------------------------
# Parser robusto (dos filas de encabezado)
# ---------------------------------------------------------------------------
def parsear_hoja_remuneraciones(ruta=None, hoja: str = "La Rioja") -> pd.DataFrame:
    """
    Parsea la hoja de remuneraciones SIPA-OEDE para una provincia.
    Devuelve DataFrame largo: [ciiu, rama, anio, mes, salario].
    """
    if ruta is None:
        ruta = RUTA_REMUNERACIONES
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")

    raw = pd.read_excel(ruta, sheet_name=hoja, header=None)
    if raw.empty:
        raise ValueError(f"La hoja '{hoja}' está vacía.")

    header_row = _buscar_fila_header(raw)
    periodo_row = _buscar_fila_periodos(raw, cerca_de=header_row,
                                        ventana=4, min_periodos=3)
    if periodo_row is None:
        periodo_row = header_row

    data_start = max(header_row, periodo_row) + 1
    if data_start >= len(raw):
        raise ValueError(
            f"La hoja '{hoja}' no tiene filas de datos después del encabezado."
        )

    # Construir nombres de columna combinando header_row + periodo_row
    nombres = []
    for j in range(raw.shape[1]):
        v_h = str(raw.iloc[header_row, j]).strip()
        v_p_raw = raw.iloc[periodo_row, j]
        v_p = str(v_p_raw).strip()

        anio_p, mes_p = _periodo_a_anio_mes(v_p_raw)
        if anio_p is not None:
            nombres.append(f"{anio_p}-{mes_p:02d}")
        elif v_h and v_h.lower() not in ("nan", "none", ""):
            nombres.append(v_h)
        elif v_p and v_p.lower() not in ("nan", "none", ""):
            nombres.append(v_p)
        else:
            nombres.append(f"col_{j}")

    # Desambiguar nombres duplicados
    vistos = {}
    finales = []
    for n in nombres:
        if n in vistos:
            vistos[n] += 1
            finales.append(f"{n}__{vistos[n]}")
        else:
            vistos[n] = 0
            finales.append(n)

    df = raw.iloc[data_start:].copy().reset_index(drop=True)
    df.columns = finales

    col_ciiu, col_rama = _detectar_columnas(df)
    df = df.rename(columns={col_ciiu: "ciiu_raw", col_rama: "rama"})
    df = df.copy()  # defragmentar

    df["ciiu"] = pd.to_numeric(df["ciiu_raw"], errors="coerce")
    df = df.dropna(subset=["ciiu"]).copy()
    df["ciiu"] = df["ciiu"].astype(int)
    df["rama"] = df["rama"].apply(_norm_rama)

    # Columnas de período
    cols_periodo = []
    for c in df.columns:
        if c in ("ciiu_raw", "ciiu", "rama"):
            continue
        anio, mes = _periodo_a_anio_mes(c)
        if anio is not None and mes is not None:
            cols_periodo.append((c, anio, mes))

    if not cols_periodo:
        raise ValueError(
            f"No se detectaron columnas de período en la hoja '{hoja}'. "
            f"Columnas disponibles: {list(df.columns)[:12]}..."
        )

    # Melt a formato largo
    registros = []
    for c, anio, mes in cols_periodo:
        tmp = df[["ciiu", "rama", c]].copy()
        tmp.columns = ["ciiu", "rama", "salario"]
        tmp["anio"] = anio
        tmp["mes"] = mes
        registros.append(tmp)

    largo = pd.concat(registros, ignore_index=True)
    largo["salario"] = pd.to_numeric(largo["salario"], errors="coerce")
    largo = largo.dropna(subset=["salario"])
    largo = largo[largo["salario"] > 0]

    largo = (largo[["ciiu", "rama", "anio", "mes", "salario"]]
             .sort_values(["anio", "mes", "ciiu"])
             .reset_index(drop=True))
    return largo


# ---------------------------------------------------------------------------
# Salario provincial de referencia (ponderado por empleo)
# ---------------------------------------------------------------------------
def salario_provincial_mensual(prov: str = "La Rioja") -> pd.DataFrame:
    """Serie mensual del salario privado formal provincial ponderado por empleo.

    Fuente: SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx
    vía regional.cargar_salario("nivel").

    Devuelve DataFrame[anio, mes, salario_prov] ordenado por (anio, mes).
    """
    from src import regional  # import tardío para evitar circularidad

    df = regional.cargar_salario(tipo="nivel")
    df = df.copy()

    if "jurisdiccion" in df.columns:
        mask = df["jurisdiccion"].astype(str).str.contains(
            prov, case=False, na=False
        )
        df = df[mask]

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha", "valor"]).copy()

    df["anio"] = df["fecha"].dt.year.astype(int)
    df["mes"] = df["fecha"].dt.month.astype(int)
    df = df.rename(columns={"valor": "salario_prov"})

    df = (df[["anio", "mes", "salario_prov"]]
          .groupby(["anio", "mes"], as_index=False)["salario_prov"].mean()
          .sort_values(["anio", "mes"])
          .reset_index(drop=True))
    return df


# ---------------------------------------------------------------------------
# Salario por CIIU (con definición y fallback de mes)
# ---------------------------------------------------------------------------
def salario_por_ciiu(
    anio: int = 2024,
    mes: int | None = None,
    prov: str = "La Rioja",
    definicion: str = "completo",
) -> pd.DataFrame:
    """
    Devuelve el salario por CIIU dentro de la definición elegida.

    Parámetros
    ----------
    anio : int
        Año de referencia. Si no hay dato, fallback al último año disponible.
    mes : int | None
        Mes de referencia. Si None, usa el último mes del año.
        Si el mes pedido no existe, fallback al último mes disponible.
    prov : str
        Provincia (nombre de hoja en el archivo SIPA).
    definicion : {"nucleo", "amplio", "completo"}

    Devuelve
    --------
    DataFrame[ciiu, rama, salario, prima, anio, mes]
        Incluye las ramas sin dato con salario=NaN y prima=NaN.
    """
    if definicion not in MAPA_DEFINICIONES:
        raise ValueError(
            f"definicion inválida: {definicion!r}. "
            f"Opciones: {list(MAPA_DEFINICIONES.keys())}"
        )
    codigos = MAPA_DEFINICIONES[definicion]

    # 1. Datos disponibles
    df = parsear_hoja_remuneraciones(hoja=prov)

    # 2. Filtrar por año (con fallback)
    anios_disponibles = sorted(df["anio"].unique())
    anio_uso = anio
    if anio not in anios_disponibles:
        anio_uso = anios_disponibles[-1]
        print(f"[!] Año {anio} no disponible. Fallback a {anio_uso}.")

    df_anio = df[df["anio"] == anio_uso].copy()

    # 3. Filtrar por mes (con fallback)
    meses_disponibles = sorted(df_anio["mes"].unique())
    if not meses_disponibles:
        raise ValueError(f"No hay datos para el año {anio_uso} en {prov}.")

    if mes is None:
        mes_uso = meses_disponibles[-1]
    elif mes in meses_disponibles:
        mes_uso = mes
    else:
        mes_uso = meses_disponibles[-1]
        print(
            f"[!] Mes {mes} no disponible en {anio_uso}. "
            f"Fallback a mes {mes_uso}."
        )

    df_mes = df_anio[df_anio["mes"] == mes_uso].copy()

    # 4. Filtrar por definición
    df_def = df_mes[df_mes["ciiu"].isin(codigos)].copy()

    # 5. Salario provincial: mismo (anio, mes) o el más cercano (±2 meses).
    #    NO usar el último disponible (infla la prima por inflación).
    prov_mensual = salario_provincial_mensual(prov=prov)
    prov_mensual = prov_mensual.dropna(subset=["salario_prov"]).copy()
    prov_mensual["_dist"] = (
        (prov_mensual["anio"] - anio_uso) * 12
        + (prov_mensual["mes"] - mes_uso)
    ).abs()

    candidatos = prov_mensual[prov_mensual["_dist"] <= 2].sort_values("_dist")
    if not candidatos.empty:
        salario_prov = float(candidatos["salario_prov"].iloc[0])
        d = int(candidatos["_dist"].iloc[0])
        if d > 0:
            print(
                f"[!] Sin salario provincial exacto para "
                f"{anio_uso}-{mes_uso:02d}. Usando "
                f"{int(candidatos['anio'].iloc[0])}-"
                f"{int(candidatos['mes'].iloc[0]):02d} (dist={d}m)."
            )
    else:
        prov_anual = (prov_mensual
                      .groupby("anio", as_index=False)["salario_prov"].mean())
        fila = prov_anual[prov_anual["anio"] == anio_uso]
        if fila.empty:
            raise ValueError(
                f"No hay salario provincial ni cerca de "
                f"{anio_uso}-{mes_uso:02d}. No se puede calcular prima."
            )
        salario_prov = float(fila["salario_prov"].iloc[0])
        print(
            f"[!] Sin salario provincial cerca de {anio_uso}-{mes_uso:02d}. "
            f"Usando promedio anual {anio_uso}: ${salario_prov:,.0f}"
        )

    # 6. Calcular prima
    if salario_prov and salario_prov > 0:
        df_def["prima"] = (df_def["salario"] / salario_prov - 1) * 100
    else:
        df_def["prima"] = np.nan

    # 7. Rellenar CIIU sin dato (para que aparezcan en el gráfico)
    presentes = set(df_def["ciiu"].unique())
    faltantes = sorted(codigos - presentes)
    if faltantes:
        df_falt = pd.DataFrame({
            "ciiu":    faltantes,
            "rama":    [NOMBRES_CIIU.get(c, f"CIIU {c}") for c in faltantes],
            "salario": np.nan,
            "prima":   np.nan,
            "anio":    anio_uso,
            "mes":     mes_uso,
        })
        df_def = pd.concat([df_def, df_falt], ignore_index=True)

    # 8. Ordenar: con dato primero (desc), sin dato al final
    df_def["_sin_dato"] = df_def["salario"].isna().astype(int)
    df_def = (df_def
              .sort_values(["_sin_dato", "salario"], ascending=[True, False])
              .drop(columns="_sin_dato")
              .reset_index(drop=True))

    df_def = df_def[["ciiu", "rama", "salario", "prima", "anio", "mes"]]
    return df_def


# ---------------------------------------------------------------------------
# Prima salarial anual por definición
# ---------------------------------------------------------------------------
def calcular_prima(prov: str = "La Rioja") -> pd.DataFrame:
    """
    Prima salarial anual para las tres definiciones.

    Prima = (salario_promedio_rama_EC / salario_provincial - 1) * 100

    El salario provincial de referencia se toma del MISMO mes/año que el
    salario por CIIU, o el más cercano (±2 meses). Si no hay, promedio
    anual del año. Nunca el último mes disponible global.

    Devuelve:
        DataFrame[anio, prima_nucleo_informatico, prima_nucleo_amplio,
                  prima_ec_completo]
    """
    df = parsear_hoja_remuneraciones(hoja=prov)
    prov_mensual = salario_provincial_mensual(prov=prov)
    prov_mensual = prov_mensual.dropna(subset=["salario_prov"]).copy()

    prov_anual = (prov_mensual
                  .groupby("anio", as_index=False)["salario_prov"].mean()
                  .rename(columns={"salario_prov": "salario_prov_anual"}))

    filas = []
    for anio in sorted(df["anio"].unique()):
        meses = sorted(df.loc[df["anio"] == anio, "mes"].unique())
        if not meses:
            continue
        mes = meses[-1]

        df_mes = df[(df["anio"] == anio) & (df["mes"] == mes)]

        # Salario provincial: mismo (anio, mes) o el más cercano (±2 meses).
        prov_mensual["_dist"] = (
            (prov_mensual["anio"] - anio) * 12
            + (prov_mensual["mes"] - mes)
        ).abs()
        candidatos = prov_mensual[prov_mensual["_dist"] <= 2].sort_values("_dist")

        if not candidatos.empty:
            sal_prov = float(candidatos["salario_prov"].iloc[0])
        else:
            fila_anual = prov_anual[prov_anual["anio"] == anio]
            if fila_anual.empty:
                continue
            sal_prov = float(fila_anual["salario_prov_anual"].iloc[0])

        if not sal_prov or sal_prov <= 0:
            continue

        fila = {"anio": anio}
        for nombre, codigos in MAPA_DEFINICIONES.items():
            sub = df_mes[df_mes["ciiu"].isin(codigos)]
            if sub.empty:
                fila[f"prima_{nombre}"] = np.nan
                continue
            sal_prom = sub["salario"].mean()
            fila[f"prima_{nombre}"] = (sal_prom / sal_prov - 1) * 100
        filas.append(fila)

    out = pd.DataFrame(filas)
    out = out.rename(columns={
        "prima_nucleo":   "prima_nucleo_informatico",
        "prima_amplio":   "prima_nucleo_amplio",
        "prima_completo": "prima_ec_completo",
    })

    cols = [
        "anio",
        "prima_nucleo_informatico",
        "prima_nucleo_amplio",
        "prima_ec_completo",
    ]
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan

    return out[cols].sort_values("anio").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Exportación a Excel (3 hojas)
# ---------------------------------------------------------------------------
def exportar_excel(ruta_salida=None) -> Path:
    """
    Exporta a un único Excel:
        - Hoja 1: prima_anual
        - Hoja 2: salario_por_ciiu (último año, completo)
        - Hoja 3: serie_mensual (todos los meses, definición completa)
    """
    if ruta_salida is None:
        ruta_salida = RUTA_SALIDA_DEFAULT
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    prima = calcular_prima()

    df_largo = parsear_hoja_remuneraciones()
    ultimo_anio = int(df_largo["anio"].max())
    sal_ciiu = salario_por_ciiu(anio=ultimo_anio, definicion="completo")

    serie = df_largo[df_largo["ciiu"].isin(CIIU_COMPLETO)].copy()
    serie = (serie[["anio", "mes", "ciiu", "rama", "salario"]]
             .sort_values(["anio", "mes", "ciiu"])
             .reset_index(drop=True))

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        prima.to_excel(writer, sheet_name="prima_anual", index=False)
        sal_ciiu.to_excel(writer, sheet_name="salario_por_ciiu", index=False)
        serie.to_excel(writer, sheet_name="serie_mensual", index=False)

    print(f"[OK] Exportado: {ruta_salida}")
    return ruta_salida


# ---------------------------------------------------------------------------
# Ejecución directa
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Prima salarial EC — La Rioja ===\n")

    print("--- Prima anual por definición ---")
    prima = calcular_prima()
    print(prima.to_string(index=False))

    print("\n--- Salario por CIIU (último año, definición completa) ---")
    df_ciiu = salario_por_ciiu(anio=2024, definicion="completo")
    print(df_ciiu.to_string(index=False))

    print("\n--- Exportando Excel ---")
    exportar_excel()
    print("\n[OK] Listo.")