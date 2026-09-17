# src/funciones.py
import warnings
import pandas as pd
from pathlib import Path

from src.config import FILE_IPC, FILES_EMPRESAS, PROVINCIAS_BENCHMARK, PROVINCIA_FOCO

warnings.filterwarnings("ignore", category=UserWarning)


# ============================================================
# IPC — Índice de Precios al Consumidor (INDEC)
# ============================================================

# Fila donde está el encabezado de cada región en la hoja
# "Variación mensual IPC Nacional"
REGIONES_IPC = {
    "Total nacional":    5,
    "Región GBA":        35,
    "Región Pampeana":   65,
    "Región Noroeste":   95,    # ← NOA (incluye La Rioja)
    "Región Noreste":    125,
    "Región Cuyo":       155,
    "Región Patagonia":  185,
}

# Categorías en el orden en que aparecen dentro de cada bloque regional
CATEGORIAS_IPC = [
    "Nivel general",
    "Alimentos y bebidas no alcohólicas",
    "Bebidas alcohólicas y tabaco",
    "Prendas de vestir y calzado",
    "Vivienda, agua, electricidad, gas y otros combustibles",
    "Equipamiento y mantenimiento del hogar",
    "Salud",
    "Transporte",
    "Comunicación",
    "Recreación y cultura",
    "Educación",
    "Restaurantes y hoteles",
    "Bienes y servicios varios",
    "Estacional",
    "Núcleo",
    "Regulados",
    "Bienes",
    "Servicios",
]


def listar_hojas_ipc() -> list[str]:
    """Devuelve los nombres de todas las hojas del archivo IPC."""
    return pd.ExcelFile(FILE_IPC).sheet_names


def cargar_ipc_regional(
    hoja: str = "Variación mensual IPC Nacional",
) -> pd.DataFrame:
    """
    Lee una hoja del IPC con apertura regional y devuelve un DataFrame tidy:
        region | categoria | fecha | valor

    Estructura verificada del Excel:
    - Fila 5: encabezado con fechas (col 0 = 'Total nacional', col 1+ = meses)
    - Filas 5, 35, 65, 95, 125, 155, 185: encabezados de cada región
    - Cada bloque tiene 18 filas de categorías a partir de (fila_region + 4)

    Notas:
    - Comparación de etiquetas case-insensitive (INDEC escribe
      "Nivel General" en Patagonia y "Nivel general" en el resto).
    - Corrección de fechas: se fuerza día 1 de cada mes por errores de
      tipeo del INDEC (ej. 2026-03-26 en lugar de 2026-03-01).
    """
    df = pd.read_excel(FILE_IPC, sheet_name=hoja, header=None)
    n_filas = len(df)

    # Fechas: fila 5, columnas 1 en adelante
    fechas = pd.to_datetime(df.iloc[5, 1:].values, errors="coerce")
    # Forzar día 1 de cada mes (corrige typos del INDEC tipo 2026-03-26)
    fechas = pd.DatetimeIndex(fechas).to_period("M").to_timestamp()

    filas = []
    for region, fila_header in REGIONES_IPC.items():
        fila_inicio = fila_header + 4  # primera categoría ("Nivel general")
        idx_cat = 0

        for offset in range(30):
            if idx_cat >= len(CATEGORIAS_IPC):
                break

            fila = fila_inicio + offset
            if fila >= n_filas:
                break

            label_raw = str(df.iloc[fila, 0]).strip()
            # Comparación case-insensitive
            if label_raw.lower() != CATEGORIAS_IPC[idx_cat].lower():
                continue

            label = CATEGORIAS_IPC[idx_cat]  # guardamos la versión canónica
            valores = df.iloc[fila, 1:].values
            for f, v in zip(fechas, valores):
                if pd.isna(f):
                    continue
                filas.append({
                    "region":    region,
                    "categoria": label,
                    "fecha":     f,
                    "valor":     pd.to_numeric(v, errors="coerce"),
                })
            idx_cat += 1

    out = pd.DataFrame(filas)
    return out.sort_values(
        ["region", "categoria", "fecha"]
    ).reset_index(drop=True)


# ============================================================
# Empresas por provincia (SIPA - OEDE)
# ============================================================

# Hojas que NO son provincias (carátulas, notas, agregados, trimestres)
HOJAS_IGNORAR = {
    # metadatos
    "Caratula", "Carátula", "Indice", "Índice", "Metodología",
    "Hoja1",
    # agregados / no-provincia
    "GBA", "Partidos de GBA", "Resto de Buenos Aires",
    "T1", "T2", "T3", "T4", "T5", "T6", "T7",
}

# Alias de hojas duplicadas por tilde / variantes de nombre.
# clave = nombre tal como aparece en el Excel,
# valor = nombre canónico que usamos en el proyecto.
ALIAS_HOJAS = {
    "Capital Federal": "CABA",
    "Cordoba":         "Córdoba",
    "Entre Rios":      "Entre Ríos",
    "Neuquen":         "Neuquén",
    "Rio Negro":       "Río Negro",
    "Santa Fe":        "Santa Fé",
    "Tucuman":         "Tucumán",
}


def _normalizar_hoja(nombre: str) -> str:
    """Aplica alias para unificar variantes de nombre de hoja."""
    return ALIAS_HOJAS.get(nombre, nombre)


def listar_hojas_empresas() -> list[str]:
    """
    Devuelve las hojas únicas entre los 3 archivos, sin metadatos,
    sin agregados y con nombres normalizados (sin duplicados por tilde).
    """
    vistas = set()
    for f in FILES_EMPRESAS:
        if f.exists():
            for h in pd.ExcelFile(f).sheet_names:
                if h in HOJAS_IGNORAR:
                    continue
                vistas.add(_normalizar_hoja(h))
    return sorted(vistas)


def _archivo_y_hoja_real(hoja: str) -> tuple[Path, str] | None:
    """
    Busca en cuál de los 3 archivos está la hoja pedida (aplicando alias).
    Devuelve (path, nombre_real_de_hoja) o None si no existe.
    """
    # 1) Intentar con el nombre tal cual
    for f in FILES_EMPRESAS:
        if f.exists():
            sheets = pd.ExcelFile(f).sheet_names
            if hoja in sheets:
                return f, hoja
    # 2) Intentar mapeando el canónico → variante del Excel
    variantes = [k for k, v in ALIAS_HOJAS.items() if v == hoja]
    for f in FILES_EMPRESAS:
        if f.exists():
            sheets = pd.ExcelFile(f).sheet_names
            for var in variantes:
                if var in sheets:
                    return f, var
    return None


def cargar_empresas_provincia(
    provincia: str,
    fila_header: int | None = None,
) -> pd.DataFrame:
    """
    Carga la hoja de una provincia y devuelve un DataFrame tidy:
        provincia | Ramas | Descripción | anio | empresas

    Detección automática del header: se elige la fila (dentro de las
    primeras 30) que contenga más valores tipo año (1990-2100). Es
    robusto ante variaciones de layout entre provincias.

    Acepta códigos de sección (letra A-Z) y de actividad (1 a 4 dígitos).
    """
    res = _archivo_y_hoja_real(provincia)
    if res is None:
        raise ValueError(
            f"'{provincia}' no existe en ninguno de los 3 archivos.\n"
            f"Disponibles: {listar_hojas_empresas()}"
        )
    archivo, hoja_real = res

    # --- Detección automática del header por cantidad de "años" ---
    if fila_header is None:
        raw = pd.read_excel(
            archivo, sheet_name=hoja_real,
            header=None, engine="openpyxl", nrows=30,
        )
        mejor_fila, mejor_score = None, 0
        for i in range(len(raw)):
            score = 0
            for v in raw.iloc[i].values:
                try:
                    n = int(float(v))
                    if 1990 <= n <= 2100:
                        score += 1
                except (ValueError, TypeError):
                    continue
            if score > mejor_score:
                mejor_score = score
                mejor_fila = i
        if mejor_fila is None or mejor_score < 5:
            raise ValueError(
                f"No pude detectar la fila de header en '{provincia}' "
                f"(mejor score: {mejor_score}). Pasala con fila_header=..."
            )
        fila_header = mejor_fila

    df = pd.read_excel(
        archivo,
        sheet_name=hoja_real,
        header=fila_header,
        engine="openpyxl",
    )

    # --- Renombrar las dos primeras columnas ---
    cols = list(df.columns)
    cols[0] = "Ramas"
    cols[1] = "Descripción"
    df.columns = [str(c).strip() for c in cols]

    # --- Filtrar filas de datos ---
    df = df[df["Ramas"].notna()].copy()
    df["Ramas"] = df["Ramas"].astype(str).str.strip()

    # Códigos válidos: una letra (sección) o 1-4 dígitos (actividad)
    mask = df["Ramas"].str.match(r"^([A-Z]|\d{1,4})$", na=False)
    df = df[mask].copy()

    # --- Detectar columnas de años (1990-2100) ---
    anios = []
    for c in df.columns:
        if c in ("Ramas", "Descripción"):
            continue
        try:
            n = int(float(c))
            if 1990 <= n <= 2100:
                anios.append(c)
        except (ValueError, TypeError):
            continue

    df_long = df.melt(
        id_vars=["Ramas", "Descripción"],
        value_vars=anios,
        var_name="anio",
        value_name="empresas",
    )

    df_long["empresas"] = pd.to_numeric(
        df_long["empresas"].replace({"s.d.": None}),
        errors="coerce",
    )
    df_long = df_long.dropna(subset=["anio"]).reset_index(drop=True)
    df_long["anio"] = df_long["anio"].astype(int)
    df_long["provincia"] = provincia

    return df_long[["provincia", "Ramas", "Descripción", "anio", "empresas"]]


def cargar_empresas_benchmark(
    provincias: list[str] | None = None,
    ramas_2d: list[str] | None = None,
) -> pd.DataFrame:
    """
    Concatena varias provincias y opcionalmente filtra por prefijo
    de 2 dígitos (ej. ['72','73','64'] para TIC).
    """
    if provincias is None:
        provincias = [PROVINCIA_FOCO] + PROVINCIAS_BENCHMARK

    df = pd.concat(
        [cargar_empresas_provincia(p) for p in provincias],
        ignore_index=True,
    )

    if ramas_2d:
        df["rama2"] = df["Ramas"].str[:2]
        df = df[df["rama2"].isin(ramas_2d)].copy()

    return df