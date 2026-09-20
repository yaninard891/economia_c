"""
Módulo de carga y análisis de empleo y salarios para La Rioja.

Fuentes:
- SerieWeb OEDE (mensual, por provincia)
- Boletín Provincial OEDE (por sector CIIU rev 3, trimestral/anual/mensual)
- Boletín Nacional OEDE (contexto nacional)
- SIPA (empresas por rama CIIU, anual) vía src.funciones

Convenciones:
- Fechas: pd.Timestamp. Mensual → día 1. Trimestral → último día del trimestre.
  Anual → 31/12.
- Empleo SerieWeb: viene en miles, se convierte a puestos.
- Salarios: pesos corrientes salvo que se indique.
- Códigos CIIU: rev 3. Se clasifican en 'seccion' (letra), 'division' (1-2 dígitos),
  'grupo' (3-4 dígitos) para poder filtrar y evitar duplicar al sumar.
- Se excluyen filas agregadas ("Total país", "Total") en todas las series.
"""
from pathlib import Path
import re
import unicodedata
import pandas as pd
import numpy as np

# ------------------------------------------------------------------
# Rutas y catálogo
# ------------------------------------------------------------------
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

FILES_EMPLEO = {
    "priv_formal_prov":   "SerieWeb_EMPLEO_PRIVADO_FORMAL_provincias.xlsx",
    "salario_priv_prov":  "SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx",
    "empleo_anual":       "provinciales_serie_empleo_anual_3.xlsx",
    "empleo_trim_2dig":   "provinciales_serie_empleo_trimestral_2dig_6.xlsx",
    "empleo_trim_4dig":   "provinciales_serie_empleo_trimestral_4dig_7.xlsx",
    "remun_anual":        "provinciales_serie_remuneraciones_anual_3.xlsx",
    "remun_mensual_2dig": "provinciales_serie_remuneraciones_mensual_2dig_8.xlsx",
    "remun_mensual_4dig": "provinciales_serie_remuneraciones_mensual_4dig_7.xlsx",
    "empleo_nacional":    "nacional_serie_empleo_trimestral_7.xlsx",
}

# ------------------------------------------------------------------
# Normalización de nombres
# ------------------------------------------------------------------
PROV_ALIAS = {
    # --- Buenos Aires (3 formas distintas según fuente) ---
    "Bs. As":                          "Buenos Aires",
    "Gran Buenos Aires":               "GBA",
    "GRAN BUENOS AIRES":               "GBA",
    "Partidos de GBA":                 "GBA",
    "Buenos Aires (sin GBA)":          "Resto BA",
    "Resto de Buenos Aires":           "Resto BA",
    "Resto Pcia. Bs. As.":             "Resto BA",
    "BUENOS AIRES":                    "Resto BA",
    # --- CABA ---
    "Capital Federal":                 "CABA",
    "CABA":                            "CABA",
    "Ciudad Autónoma de Buenos Aires": "CABA",
    "CIUDAD AUTÓNOMA DE BUENOS AIRES": "CABA",
    # --- Provincias: forma canónica con tilde ---
    "CORDOBA": "Córdoba", "CÓRDOBA": "Córdoba",
    "SANTA FE": "Santa Fe",
    "TUCUMAN": "Tucumán", "TUCUMÁN": "Tucumán",
    "LA RIOJA": "La Rioja",
    "ENTRE RIOS": "Entre Ríos", "ENTRE RÍOS": "Entre Ríos",
    "RIO NEGRO": "Río Negro", "RÍO NEGRO": "Río Negro",
    "NEUQUEN": "Neuquén", "NEUQUÉN": "Neuquén",
    "SANTA CRUZ": "Santa Cruz",
    "TIERRA DEL FUEGO": "Tierra del Fuego",
    # Variantes abreviadas (SerieWeb)
    "S del Estero": "Santiago del Estero",
    "T del Fuego":  "Tierra del Fuego",
    # Agregados (se filtran después, pero los normalizamos igual)
    "Total país":   "Total país",
    "Total":        "Total",
    "TOTAL":        "Total",
}

_ES_TOTAL = {"total", "total país", "total pais", "total nacional"}

# Mapeo nombre normalizado → nombre de hoja en los archivos sectoriales
SHEET_MAP_EMPLEO = {
    "GBA":                  "Partidos de GBA",
    "CABA":                 "Capital Federal",
    "Resto BA":             "Resto de Buenos Aires",
    "Córdoba":              "Cordoba",
    "Entre Ríos":           "Entre Rios",
    "Neuquén":              "Neuquen",
    "Río Negro":            "Rio Negro",
    "Tucumán":              "Tucuman",
    "Tierra del Fuego":     "Tierra del Fuego",
    "Santiago del Estero":  "Santiago del Estero",
}


def _norm_prov(s):
    s = str(s).strip()
    return PROV_ALIAS.get(s, s)


def _strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def _resolver_sheet(path, nombre):
    """Devuelve la hoja correcta dado un nombre normalizado o crudo."""
    hojas = pd.ExcelFile(path).sheet_names
    if nombre in hojas:
        return nombre
    raw = SHEET_MAP_EMPLEO.get(nombre)
    if raw and raw in hojas:
        return raw
    target = _strip_acc(nombre).lower()
    for h in hojas:
        if _strip_acc(h).lower() == target:
            return h
    raise ValueError(f"Hoja no encontrada para '{nombre}'. Disponibles: {hojas}")


def _parse_periodo(p, tipo):
    """
    Convierte etiqueta de período a Timestamp.
    Mensual → día 1 del mes. Trimestral → último día del trimestre.
    Anual → 31/12.
    """
    if tipo == "trim":
        m = re.search(r"(\d)\s*[ºo°]?\s*Trim\s*(\d{4})", str(p), flags=re.IGNORECASE)
        if m:
            q, y = int(m.group(1)), int(m.group(2))
            return pd.Timestamp(year=y, month=q * 3, day=1) + pd.offsets.MonthEnd(0)
        return pd.NaT
    if tipo == "anual":
        try:
            y = int(float(p))
            return pd.Timestamp(year=y, month=12, day=31)
        except (TypeError, ValueError):
            return pd.NaT
    # Mensual: parsear y forzar al primer día del mes
    dt = pd.to_datetime(p, errors="coerce")
    if pd.isna(dt):
        return pd.NaT
    return dt.to_period("M").to_timestamp()


def _nivel_codigo(c):
    """Clasifica código CIIU en 'seccion' | 'division' | 'grupo' | None.

    Maneja códigos que vienen como float ("7210.0") desde pandas cuando
    la columna tiene mezcla de enteros y strings ('s.d.').
    """
    c = str(c).strip().upper()
    if c in ("", "NAN", "NONE", "TOTAL"):
        return None
    # Normalizar "7210.0" -> "7210"
    if c.endswith(".0"):
        c = c[:-2]
    if len(c) == 1 and c.isalpha():
        return "seccion"
    if c.isdigit() and len(c) <= 2:
        return "division"
    if c.isdigit() and len(c) in (3, 4):
        return "grupo"
    return None


# ==================================================================
# 1. SerieWeb OEDE — empleo y salario privado formal por provincia
# ==================================================================

def cargar_empleo_priv_formal(desestacionalizada=False):
    """
    Serie larga mensual de empleo privado formal por provincia.

    Returns
    -------
    DataFrame: provincia | fecha | puestos | puestos_miles
    """
    sheet = "serie_desestacionalizada" if desestacionalizada else "serie_original"
    df = pd.read_excel(RAW / FILES_EMPLEO["priv_formal_prov"],
                       sheet_name=sheet, header=0)
    df = df.rename(columns={df.columns[0]: "provincia"})
    df = df[df["provincia"].notna()].copy()
    df["provincia"] = df["provincia"].map(_norm_prov)
    df = df[~df["provincia"].str.strip().str.lower().isin(_ES_TOTAL)]

    long = df.melt(id_vars="provincia", var_name="fecha", value_name="puestos_miles")
    long["fecha"] = pd.to_datetime(long["fecha"], errors="coerce")
    long["fecha"] = long["fecha"].dt.to_period("M").dt.to_timestamp()
    long = long.dropna(subset=["fecha", "puestos_miles"]).copy()
    long["puestos"] = long["puestos_miles"] * 1000
    return (long[["provincia", "fecha", "puestos", "puestos_miles"]]
            .sort_values(["provincia", "fecha"])
            .reset_index(drop=True))


def cargar_salario_priv_formal(variacion_real=False):
    """
    Serie larga mensual de salario privado formal por jurisdicción.

    Parameters
    ----------
    variacion_real : si True, devuelve la variación % interanual real
                     (en vez de salario nominal en pesos).

    Returns
    -------
    DataFrame: jurisdiccion | fecha | salario_prom   (o var_interanual_real)
    """
    if variacion_real:
        sheet, col = "Variación % interanual real", "var_interanual_real"
    else:
        sheet, col = "Remuneraciones_promedio_privado", "salario_prom"
    df = pd.read_excel(RAW / FILES_EMPLEO["salario_priv_prov"],
                       sheet_name=sheet, header=0)
    df = df.rename(columns={df.columns[0]: "jurisdiccion"})
    df = df[df["jurisdiccion"].notna()].copy()
    df["jurisdiccion"] = df["jurisdiccion"].map(_norm_prov)
    df = df[~df["jurisdiccion"].str.strip().str.lower().isin(_ES_TOTAL)]

    long = df.melt(id_vars="jurisdiccion", var_name="fecha", value_name=col)
    long["fecha"] = pd.to_datetime(long["fecha"], errors="coerce")
    long["fecha"] = long["fecha"].dt.to_period("M").dt.to_timestamp()
    long = long.dropna(subset=["fecha", col])
    return (long.sort_values(["jurisdiccion", "fecha"])
            .reset_index(drop=True))


# ==================================================================
# 2. Boletín Provincial OEDE — por sector CIIU
# ==================================================================

def _leer_hoja_sector_provincial(path, sheet, valor_nombre, tipo_fecha):
    """
    Parser robusto de hojas provinciales (empleo o remuneraciones).

    Detecta automáticamente:
      - fila de header (busca 'Rama de Actividad'/'Ramas de actividad'/
        'Ramas'/'Sector')
      - columnas de período (celdas que parsean a fecha)
      - columnas de código y rama (por longitud media de strings)
    """
    raw = pd.read_excel(path, sheet_name=sheet, header=None)

    # 1) Localizar fila de header
    hdr_row = None
    for i in range(min(12, len(raw))):
        for j in range(min(8, raw.shape[1])):
            v = str(raw.iloc[i, j]).strip().lower()
            if v in ("ramas de actividad", "rama de actividad",
                     "sector", "ramas"):
                hdr_row = i
                break
        if hdr_row is not None:
            break
    if hdr_row is None:
        raise ValueError(f"[{sheet}] no encontré fila de header")

    # 2) Encontrar columnas de período
    periodos_by_col = {}
    for j in range(raw.shape[1]):
        dt = _parse_periodo(raw.iloc[hdr_row, j], tipo_fecha)
        if pd.notna(dt):
            periodos_by_col[j] = dt
    if not periodos_by_col:
        raise ValueError(f"[{sheet}] no encontré columnas de períodos")

    val_cols = sorted(periodos_by_col.keys())
    periodos = [periodos_by_col[j] for j in val_cols]
    first_val_col = val_cols[0]

    # 3) Columnas pre-valor: código y rama
    pre_cols = list(range(first_val_col))
    if len(pre_cols) < 2:
        raise ValueError(f"[{sheet}] esperaba ≥2 columnas pre-valor, hay {pre_cols}")

    data_block = raw.iloc[hdr_row + 1:, :].reset_index(drop=True)

    def avg_str_len(c):
        s = data_block.iloc[:, c].dropna().astype(str)
        s = s[s.str.strip() != ""]
        return s.str.len().mean() if len(s) else 0

    lens = {c: avg_str_len(c) for c in pre_cols}
    rama_col = max(lens, key=lens.get)
    cod_candidates = sorted([c for c in pre_cols if c != rama_col],
                            key=lambda c: lens[c])
    cod_col = cod_candidates[0] if cod_candidates else rama_col

    # 4) Filtrar filas con rama no vacía
    rama_serie = data_block[rama_col].astype(str).str.strip()
    mask = (data_block[rama_col].notna()
            & (rama_serie != "")
            & (rama_serie.str.upper() != "NAN"))
    datos = data_block[mask].reset_index(drop=True)

    codes = (datos[cod_col].fillna("").astype(str).str.strip()
             .replace({"nan": "", "NaN": "", "None": ""}).values)
    ramas = datos[rama_col].astype(str).str.strip().values

    # 5) Construir tidy columna por columna
    frames = []
    for dt, j in zip(periodos, val_cols):
        vals = pd.to_numeric(datos.iloc[:, j], errors="coerce").values
        frames.append(pd.DataFrame({
            "codigo": codes,
            "rama":   ramas,
            "fecha":  dt,
            valor_nombre: vals,
        }))

    if not frames:
        return pd.DataFrame(columns=["codigo", "rama", "fecha",
                                     valor_nombre, "nivel"])

    tidy = pd.concat(frames, ignore_index=True)

    # 6) Filtros & clasificación
    tidy = tidy[~tidy["rama"].str.upper().str.strip().eq("TOTAL")].copy()
    tidy["nivel"] = tidy["codigo"].map(_nivel_codigo)
    tidy = tidy.dropna(subset=["fecha", valor_nombre])
    return tidy


def cargar_empleo_sector_provincia(provincia, nivel="2dig", solo_nivel=None):
    """
    Empleo (puestos) por rama CIIU, trimestral, para una provincia.

    Returns
    -------
    DataFrame: provincia | codigo | rama | fecha | puestos | nivel
    """
    key = "empleo_trim_2dig" if nivel == "2dig" else "empleo_trim_4dig"
    path = RAW / FILES_EMPLEO[key]
    sheet = _resolver_sheet(path, provincia)
    tidy = _leer_hoja_sector_provincial(path, sheet, "puestos", tipo_fecha="trim")
    if solo_nivel:
        tidy = tidy[tidy["nivel"] == solo_nivel].copy()
    tidy.insert(0, "provincia", _norm_prov(provincia))
    return tidy.sort_values(["codigo", "fecha"]).reset_index(drop=True)


def cargar_remuneraciones_sector_provincia(provincia, nivel="2dig",
                                           frecuencia="mensual", solo_nivel=None):
    """
    Remuneración promedio por rama CIIU para una provincia.

    Returns
    -------
    DataFrame: provincia | codigo | rama | fecha | remuneracion_prom | nivel
    """
    key = f"remun_{frecuencia}_{nivel}"
    tipo = "mensual" if frecuencia == "mensual" else "anual"
    path = RAW / FILES_EMPLEO[key]
    sheet = _resolver_sheet(path, provincia)
    tidy = _leer_hoja_sector_provincial(path, sheet, "remuneracion_prom",
                                        tipo_fecha=tipo)
    if solo_nivel:
        tidy = tidy[tidy["nivel"] == solo_nivel].copy()
    tidy.insert(0, "provincia", _norm_prov(provincia))
    return tidy.sort_values(["codigo", "fecha"]).reset_index(drop=True)


def cargar_remuneracion_total_provincias(frecuencia="mensual"):
    """
    Remuneración promedio (todas las ramas) por provincia — hoja 'Total'.

    Returns
    -------
    DataFrame: provincia | fecha | remuneracion_prom
    """
    key = f"remun_{frecuencia}_2dig"
    tipo = "mensual" if frecuencia == "mensual" else "anual"
    df = pd.read_excel(RAW / FILES_EMPLEO[key], sheet_name="Total", header=4)
    df = df.rename(columns={df.columns[0]: "provincia"})
    df = df[df["provincia"].notna()].copy()
    df["provincia"] = df["provincia"].astype(str).str.strip().map(_norm_prov)
    df = df[~df["provincia"].str.strip().str.lower().isin(_ES_TOTAL)]

    long = df.melt(id_vars="provincia", var_name="fecha_raw",
                   value_name="remuneracion_prom")
    long["fecha"] = long["fecha_raw"].apply(lambda p: _parse_periodo(p, tipo))
    long = long.dropna(subset=["fecha", "remuneracion_prom"])
    return (long[["provincia", "fecha", "remuneracion_prom"]]
            .sort_values(["provincia", "fecha"]).reset_index(drop=True))


# ==================================================================
# 3. Nacional — contexto
# ==================================================================

def cargar_empleo_nacional(desestacionalizado=False):
    """
    Empleo asalariado privado nacional, serie trimestral.

    Returns
    -------
    DataFrame: fecha | empleo
    """
    sheet = "C1.2" if desestacionalizado else "C1.1"
    df = pd.read_excel(RAW / FILES_EMPLEO["empleo_nacional"],
                       sheet_name=sheet, header=2)
    df = df.dropna(subset=[df.columns[0]])
    df = df.rename(columns={df.columns[0]: "periodo", df.columns[1]: "empleo"})
    df["empleo"] = pd.to_numeric(df["empleo"], errors="coerce")
    df = df[df["empleo"] > 1e5].copy()
    df["fecha"] = df["periodo"].apply(lambda p: _parse_periodo(p, "trim"))
    df = df.dropna(subset=["fecha", "empleo"])
    df = df.drop_duplicates(subset="fecha", keep="first")
    return df[["fecha", "empleo"]].sort_values("fecha").reset_index(drop=True)


# ==================================================================
# 4. Indicadores básicos
# ==================================================================

def empleo_variacion_interanual(df, valor="puestos", grupo=None):
    """Var % i.a. sobre serie tidy con columna 'fecha'."""
    grupo = grupo or [c for c in ("provincia", "codigo", "rama", "sector")
                      if c in df.columns]
    d = df.sort_values(grupo + ["fecha"]).copy()
    med_diff = d["fecha"].diff().dropna().median().days if len(d) > 2 else 30
    lag = 12 if med_diff < 200 else 4
    d["var_ia"] = d.groupby(grupo, dropna=False)[valor].pct_change(lag)
    return d


def empleo_indice_base100(df, fecha_base, valor="puestos", grupo=None):
    """Índice base 100 en fecha_base (Timestamp o 'YYYY-MM')."""
    fecha_base = pd.Timestamp(fecha_base)
    grupo = grupo or [c for c in ("provincia", "codigo", "rama", "sector")
                      if c in df.columns]
    d = df.copy()
    base = (d[d["fecha"] == fecha_base]
            .set_index(grupo)[valor].rename("base"))
    d = d.join(base, on=grupo)
    d["indice"] = 100 * d[valor] / d["base"]
    return d.drop(columns="base")


def ranking_provincias(df, fecha, valor="puestos"):
    """Ranking de provincias a una fecha dada."""
    fecha = pd.Timestamp(fecha)
    return (df[df["fecha"] == fecha]
            .sort_values(valor, ascending=False)
            .reset_index(drop=True))


def salario_real(df_salario, df_ipc, prov, deflactor="IPC"):
    """
    Deflacta salario nominal con IPC (usar la serie IPC NOA de src.funciones).

    df_salario : tidy jurisdiccion | fecha | salario_prom
    df_ipc     : tidy region | categoria | fecha | valor
    """
    ipc = (df_ipc.query(f"region == '{prov}' and categoria == '{deflactor}'")
                 [["fecha", "valor"]].rename(columns={"valor": "ipc"}))
    d = df_salario.query(f"jurisdiccion == '{prov}'").merge(ipc, on="fecha", how="left")
    d["salario_real"] = d["salario_prom"] / d["ipc"]
    return d


# ==================================================================
# 5. Economía del Conocimiento (TIC) — CIIU rev 3
# ==================================================================
# Sección I = Transporte, almacenamiento y comunicaciones.
# Sección K = Servicios inmobiliarios, empresariales y de alquiler.
# Divisiones del conocimiento:
#   64 → Telecomunicaciones y correos                (sección I)
#   72 → Actividades de informática                  (sección K)
#   73 → Investigación y desarrollo                  (sección K)
#   74 → Servicios jurídicos, contables y otros a empresas (sección K)

DIVISIONES_TIC_NUCLEO = {
    "64": "Telecomunicaciones y correos",
    "72": "Actividades de informática",
}

DIVISIONES_TIC_AMPLIADO = {
    **DIVISIONES_TIC_NUCLEO,
    "73": "Investigación y desarrollo",
    "74": "Servicios jurídicos, contables y otros a empresas",
}


def divisiones_disponibles(provincia="La Rioja"):
    """Lista divisiones CIIU presentes en el archivo sectorial provincial."""
    d = cargar_empleo_sector_provincia(provincia, nivel="2dig", solo_nivel="division")
    return (d[["codigo", "rama"]].drop_duplicates()
            .sort_values("codigo").reset_index(drop=True))


def empleo_tic_la_rioja(provincia="La Rioja", ampliado=False):
    """
    Empleo por división TIC (o conocimiento ampliado) para una provincia.

    Returns
    -------
    DataFrame: provincia | codigo | rama | fecha | puestos | nivel
    """
    d = cargar_empleo_sector_provincia(provincia, nivel="2dig", solo_nivel="division")
    codigos = set((DIVISIONES_TIC_AMPLIADO if ampliado
                   else DIVISIONES_TIC_NUCLEO).keys())
    return d[d["codigo"].isin(codigos)].copy()


def empleo_tic_serie(provincia="La Rioja", ampliado=False):
    """Serie agregada de empleo TIC (suma de todas las divisiones TIC)."""
    d = empleo_tic_la_rioja(provincia, ampliado=ampliado)
    return (d.groupby("fecha", as_index=False)["puestos"].sum()
            .sort_values("fecha").reset_index(drop=True))


def empleo_tic_benchmark(provincias, ampliado=False, fecha=None):
    """Empleo TIC por provincia (comparación benchmark)."""
    frames = []
    for p in provincias:
        try:
            d = empleo_tic_la_rioja(p, ampliado=ampliado)
            frames.append(d)
        except Exception as e:
            print(f"[!] {p}: {e}")
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if fecha is not None:
        df = df[df["fecha"] == pd.Timestamp(fecha)].copy()
    return df.sort_values(["provincia", "fecha"]).reset_index(drop=True)


def indice_especializacion_tic(provincia="La Rioja", ampliado=False):
    """
    Share de empleo TIC sobre el total provincial, por fecha.
    Denominador: suma de todas las divisiones (equivale al total sectorial).
    """
    d = cargar_empleo_sector_provincia(provincia, nivel="2dig", solo_nivel="division")
    codigos = set((DIVISIONES_TIC_AMPLIADO if ampliado
                   else DIVISIONES_TIC_NUCLEO).keys())

    total = (d.groupby("fecha", as_index=False)["puestos"].sum()
             .rename(columns={"puestos": "total"}))
    tic = (d[d["codigo"].isin(codigos)]
           .groupby("fecha", as_index=False)["puestos"].sum()
           .rename(columns={"puestos": "tic"}))

    m = tic.merge(total, on="fecha", how="inner")
    m["share_tic"] = m["tic"] / m["total"]
    m["provincia"] = _norm_prov(provincia)
    return m.sort_values("fecha").reset_index(drop=True)


def salario_tic_la_rioja(provincia="La Rioja", ampliado=False, frecuencia="mensual"):
    """Salario promedio por división TIC para la provincia."""
    d = cargar_remuneraciones_sector_provincia(
        provincia, nivel="2dig", frecuencia=frecuencia, solo_nivel="division")
    codigos = set((DIVISIONES_TIC_AMPLIADO if ampliado
                   else DIVISIONES_TIC_NUCLEO).keys())
    return d[d["codigo"].isin(codigos)].copy()


def prima_salarial_tic(provincia="La Rioja", ampliado=False, frecuencia="mensual"):
    """
    Prima salarial TIC = salario promedio TIC / salario promedio general provincial.

    Promedia las divisiones TIC sin ponderar. Si el N de divisiones TIC es
    muy distinto (p.ej. núcleo=2 vs ampliado=4) puede haber saltos; revisar
    composición antes de interpretar.
    """
    sal_tic = salario_tic_la_rioja(provincia, ampliado=ampliado,
                                    frecuencia=frecuencia)
    if sal_tic.empty:
        return pd.DataFrame(columns=["fecha", "salario_tic",
                                     "salario_general", "prima"])
    tic_prom = (sal_tic.groupby("fecha", as_index=False)["remuneracion_prom"].mean()
                .rename(columns={"remuneracion_prom": "salario_tic"}))

    total = cargar_remuneracion_total_provincias(frecuencia=frecuencia)
    total = (total[total["provincia"] == _norm_prov(provincia)]
             [["fecha", "remuneracion_prom"]]
             .rename(columns={"remuneracion_prom": "salario_general"}))

    m = tic_prom.merge(total, on="fecha", how="inner")
    m["prima"] = m["salario_tic"] / m["salario_general"]
    return m.sort_values("fecha").reset_index(drop=True)


# ==================================================================
# 6. Cruces TIC con SIPA (empresas)
# ==================================================================

def cargar_empresas_sipa(provincia="La Rioja"):
    """
    Wrapper de src.funciones.cargar_empresas_provincia con nombres
    y tipos homogéneos. Renombra 'Ramas' → 'codigo'.
    """
    from .funciones import cargar_empresas_provincia
    df = cargar_empresas_provincia(provincia)
    df = df.rename(columns={"Ramas": "codigo"})
    df["codigo"] = df["codigo"].astype(str).str.strip()
    df["anio"] = df["anio"].astype(int)
    df = df[df["empresas"].notna()].copy()
    df["provincia"] = df["provincia"].map(_norm_prov)
    return df.sort_values(["codigo", "anio"]).reset_index(drop=True)


def empresas_tic_sipa(provincia="La Rioja", ampliado=False):
    """
    Empresas TIC por año desde SIPA.
    Núcleo: divisiones 64, 72. Ampliado: +73, +74.
    """
    d = cargar_empresas_sipa(provincia)
    codigos = set((DIVISIONES_TIC_AMPLIADO if ampliado
                   else DIVISIONES_TIC_NUCLEO).keys())
    return d[d["codigo"].isin(codigos)].copy()


def divisiones_disponibles_sipa(provincia="La Rioja"):
    """Lista códigos CIIU presentes en SIPA (para chequear disponibilidad TIC)."""
    d = cargar_empresas_sipa(provincia)
    return (d[["codigo", "Descripción"]].drop_duplicates()
            .sort_values("codigo").reset_index(drop=True))


def empleo_por_empresa_tic(provincia="La Rioja", ampliado=False):
    """
    Puestos TIC / empresas TIC por año.
    Empleo trimestral se promedia a anual para alinear con SIPA (anual).
    """
    emp_tic = empleo_tic_la_rioja(provincia, ampliado=ampliado)
    if emp_tic.empty:
        return pd.DataFrame()

    emp_tic = emp_tic.copy()
    emp_tic["anio"] = emp_tic["fecha"].dt.year
    emp_anual = (emp_tic.groupby(["codigo", "anio"], as_index=False)["puestos"]
                 .mean())

    empr_tic = empresas_tic_sipa(provincia, ampliado=ampliado)
    if empr_tic.empty:
        return pd.DataFrame()

    cruce = emp_anual.merge(
        empr_tic[["codigo", "anio", "empresas"]],
        on=["codigo", "anio"], how="inner")
    cruce["puestos_por_empresa"] = cruce["puestos"] / cruce["empresas"]
    cruce["provincia"] = _norm_prov(provincia)
    return cruce.sort_values(["anio", "codigo"]).reset_index(drop=True)


def ratio_tamano_tic_vs_promedio(provincia="La Rioja", ampliado=False):
    """
    Tamaño medio de empresa TIC vs tamaño medio provincial, por año.

    - TIC: puestos TIC / empresas TIC.
    - Provincial: puestos totales (promedio de trimestres) / empresas totales
      (suma de secciones).
    """
    cruce = empleo_por_empresa_tic(provincia, ampliado=ampliado)
    if cruce.empty:
        return pd.DataFrame()

    tic = (cruce.groupby("anio", as_index=False)
           .agg(puestos_tic=("puestos", "sum"),
                empresas_tic=("empresas", "sum")))
    tic["tamano_tic"] = tic["puestos_tic"] / tic["empresas_tic"]

    # Empresas totales: sumar solo secciones (letras) para evitar doble conteo
    sipa = cargar_empresas_sipa(provincia)
    sipa_sec = sipa[sipa["codigo"].str.isalpha()]
    empr_anual = (sipa_sec.groupby("anio", as_index=False)["empresas"].sum()
                  .rename(columns={"empresas": "empresas_total"}))

    # Puestos totales: 1) sumar secciones por trimestre, 2) promediar trimestres
    emp_sec = cargar_empleo_sector_provincia(provincia, nivel="2dig",
                                             solo_nivel="seccion")
    por_trimestre = (emp_sec.groupby("fecha", as_index=False)["puestos"].sum())
    por_trimestre["anio"] = por_trimestre["fecha"].dt.year
    puestos_anual = (por_trimestre.groupby("anio", as_index=False)["puestos"].mean()
                     .rename(columns={"puestos": "puestos_total"}))

    m = puestos_anual.merge(empr_anual, on="anio", how="inner")
    m["tamano_promedio"] = m["puestos_total"] / m["empresas_total"]

    out = tic.merge(m[["anio", "tamano_promedio"]], on="anio", how="inner")
    out["ratio_tic_vs_promedio"] = out["tamano_tic"] / out["tamano_promedio"]
    out["provincia"] = _norm_prov(provincia)
    return out.sort_values("anio").reset_index(drop=True)