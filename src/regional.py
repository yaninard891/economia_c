"""Series provinciales SIPA/OEDE: empleo y salario privado formal.

Fuentes
-------
- SerieWeb_EMPLEO_PRIVADO_FORMAL_provincias.xlsx (3 hojas)
  · serie_original: miles de puestos, 2009-01 → 2026-06
  · serie_desestacionalizada: idem, ajustado por estacionalidad
  · variaciones %: variación i.a. en decimal, 2022-01 → 2026-06
- SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx (3 hojas)
  · Remuneraciones_promedio_privado: $ corrientes, 2010-01 → 2026-03
  · Variación % interanual real: decimal, 2022-01 → 2026-03
  · Comentarios: metadatos (no especifica deflactor de la serie real)

Notas metodológicas
-------------------
- NOA = Catamarca, Jujuy, La Rioja, Salta, S del Estero, Tucumán.
- Empleo NOA: suma simple de las 6 provincias.
- Salario NOA: promedio PONDERADO por empleo provincial del mismo mes.
- Nación: fila 'Total país' (empleo) / 'Total' (salario), no se recalcula.
- Salario real INDEC: solo se puede usar como variación i.a.; el índice
  acumulado (base ene-2022=100) es una reconstrucción nuestra.
- IPC NOA (funciones.py) arranca en 2017-01: la serie de salario real
  propio se recorta a ese rango.
- Últimos 2-3 meses de salario nominal son provisorios (menos casos
  reportados): marcar como preliminares en gráficos.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from .config import PROVINCIA_FOCO
except ImportError:
    PROVINCIA_FOCO = "La Rioja"

# ---------------------------------------------------------------------------
# Ruta de datos ABSOLUTA (independiente del working directory)
# ---------------------------------------------------------------------------
_RAIZ = Path(__file__).resolve().parent.parent
RAW = _RAIZ / "data" / "raw"

FILE_EMPLEO = "SerieWeb_EMPLEO_PRIVADO_FORMAL_provincias.xlsx"
FILE_SALARIO = "SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx"

HOJA_EMPLEO = {
    "original": "serie_original",
    "desestacionalizada": "serie_desestacionalizada",
    "var_interanual": "variaciones %",
}
HOJA_SALARIO = {
    "nivel": "Remuneraciones_promedio_privado",
    "var_real_interanual": "Variación % interanual real",
}

NOA_PROVINCIAS = ["Catamarca", "Jujuy", "La Rioja",
                  "Salta", "S del Estero", "Tucumán"]

_FILAS_BASURA = ("Fuente:", "(*)", "Nota:", "Observatorio")
_MESES_ABREV = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parsear_fechas_header(celdas) -> list:
    """Acepta datetimes reales o strings tipo 'ene-22', 'dic-24*', 'jun-25*'.

    Los meses con SAC vienen en el Excel como strings con asterisco,
    paréntesis o espacios ('dic-24*'). Se limpian antes de parsear.
    """
    out = []
    for c in celdas:
        # 1. Si ya es datetime/Timestamp, se usa directo
        if isinstance(c, (pd.Timestamp, datetime.datetime, datetime.date)):
            out.append(pd.Timestamp(c))
            continue

        # 2. Si es string, limpiar asteriscos, paréntesis y espacios del final
        if isinstance(c, str):
            s = c.strip()
            s = re.sub(r"[\s\*\(\)]+$", "", s)  # 'dic-24*' -> 'dic-24'
            if not s:
                out.append(pd.NaT)
                continue

            # 2a. Probar parseo directo (cubre '2024-12-01', '2024-12')
            f = pd.to_datetime(s, errors="coerce")
            if pd.notna(f) and f.year >= 2000:
                out.append(pd.Timestamp(f))
                continue

            # 2b. Mes textual + año: 'dic-24' o 'dic-2024'
            partes = s.lower().replace(".", "").split("-")
            if len(partes) == 2 and partes[0] in _MESES_ABREV:
                try:
                    anio = int(partes[1])
                    anio += 2000 if anio < 50 else 1900
                    out.append(pd.Timestamp(year=anio,
                                            month=_MESES_ABREV[partes[0]],
                                            day=1))
                except (ValueError, TypeError):
                    out.append(pd.NaT)
            else:
                out.append(pd.NaT)
        else:
            out.append(pd.NaT)
    return out


def _cargar_long(path: Path, hoja: str) -> pd.DataFrame:
    """Lee una hoja estándar SerieWeb → long: fecha | jurisdiccion | valor."""
    raw = pd.read_excel(path, sheet_name=hoja, header=None)
    fechas = _parsear_fechas_header(raw.iloc[0, 1:])
    cols_validas = [1 + i for i, f in enumerate(fechas) if pd.notna(f)]
    fechas_validas = [fechas[i] for i in range(len(fechas))
                      if pd.notna(fechas[i])]

    cuerpo = raw.iloc[1:, [0] + cols_validas].copy()
    cuerpo.columns = ["jurisdiccion"] + fechas_validas
    cuerpo = cuerpo[~cuerpo["jurisdiccion"].astype(str)
                    .str.startswith(_FILAS_BASURA)]
    cuerpo = cuerpo.dropna(subset=["jurisdiccion"])
    cuerpo["jurisdiccion"] = cuerpo["jurisdiccion"].astype(str).str.strip()

    long = cuerpo.melt(id_vars="jurisdiccion", var_name="fecha",
                       value_name="valor")
    long["fecha"] = pd.to_datetime(long["fecha"])
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")
    return (long.dropna(subset=["valor"])
            .sort_values(["fecha", "jurisdiccion"])
            .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

def cargar_empleo(tipo: str = "desestacionalizada") -> pd.DataFrame:
    """Long: fecha | jurisdiccion | valor.

    tipo ∈ {'original', 'desestacionalizada', 'var_interanual'}
    """
    if tipo not in HOJA_EMPLEO:
        raise ValueError(f"tipo inválido: {tipo}. Opciones: {list(HOJA_EMPLEO)}")
    return _cargar_long(RAW / FILE_EMPLEO, HOJA_EMPLEO[tipo])


def cargar_salario(tipo: str = "nivel") -> pd.DataFrame:
    """Long: fecha | jurisdiccion | valor.

    tipo ∈ {'nivel', 'var_real_interanual'}
    """
    if tipo not in HOJA_SALARIO:
        raise ValueError(f"tipo inválido: {tipo}. Opciones: {list(HOJA_SALARIO)}")
    return _cargar_long(RAW / FILE_SALARIO, HOJA_SALARIO[tipo])


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _nombre_total(indicador: str) -> str:
    return "Total país" if indicador == "empleo" else "Total"


def _serie_jurisdiccion(jurisdiccion: str, indicador: str, tipo: str) -> pd.Series:
    df = cargar_empleo(tipo) if indicador == "empleo" else cargar_salario(tipo)
    sub = df[df["jurisdiccion"] == jurisdiccion].sort_values("fecha")
    return sub.set_index("fecha")["valor"]


def _serie_noa(indicador: str, tipo: str) -> pd.Series:
    """NOA agregado. Empleo: suma. Salario: promedio ponderado por empleo."""
    if indicador == "empleo":
        df = cargar_empleo(tipo)
        sub = df[df["jurisdiccion"].isin(NOA_PROVINCIAS)]
        return sub.groupby("fecha")["valor"].sum().sort_index()

    # Salario: promedio ponderado por empleo
    sal = cargar_salario(tipo)
    emp = cargar_empleo("desestacionalizada")
    s = sal[sal["jurisdiccion"].isin(NOA_PROVINCIAS)].copy()
    e = emp[emp["jurisdiccion"].isin(NOA_PROVINCIAS)].copy()
    m = s.merge(e, on=["fecha", "jurisdiccion"], suffixes=("_sal", "_emp"))
    m["pond"] = m["valor_sal"] * m["valor_emp"]
    agg = m.groupby("fecha").agg(pond=("pond", "sum"),
                                 emp=("valor_emp", "sum"))
    return (agg["pond"] / agg["emp"]).sort_index()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def serie_nacional(indicador: str, tipo: str | None = None) -> pd.Series:
    """Serie de la fila Total país/Total."""
    if tipo is None:
        tipo = "desestacionalizada" if indicador == "empleo" else "nivel"
    return _serie_jurisdiccion(_nombre_total(indicador), indicador, tipo)


def serie_provincia(provincia: str, indicador: str,
                    tipo: str | None = None) -> pd.Series:
    """Serie de una provincia."""
    if tipo is None:
        tipo = "desestacionalizada" if indicador == "empleo" else "nivel"
    return _serie_jurisdiccion(provincia, indicador, tipo)


def serie_noa(indicador: str, tipo: str | None = None) -> pd.Series:
    """Serie agregada del NOA."""
    if tipo is None:
        tipo = "desestacionalizada" if indicador == "empleo" else "nivel"
    return _serie_noa(indicador, tipo)


def cargar_ipc_noa() -> pd.Series:
    """Índice IPC NOA (Región Noroeste, Nivel general), base 100 = 2017-01.

    Acumula las variaciones mensuales de funciones.cargar_ipc_regional().
    Detecta automáticamente si vienen en decimal o en porcentaje.
    Rango disponible: 2017-01 → últimos meses.
    """
    from .funciones import cargar_ipc_regional

    df = cargar_ipc_regional()
    noa = df[(df["region"] == "Región Noroeste") &
             (df["categoria"] == "Nivel general")].copy()
    noa = noa.dropna(subset=["valor"]).sort_values("fecha").reset_index(drop=True)
    if noa.empty:
        raise ValueError("No hay datos de IPC NOA/Nivel general")

    max_abs = noa["valor"].abs().max()
    factor = 1 + (noa["valor"] if max_abs < 1 else noa["valor"] / 100)
    indice = factor.cumprod() * 100
    indice.index = pd.DatetimeIndex(noa["fecha"])
    indice.name = "ipc_noa"
    return indice


def comparar(
    indicador: str,
    niveles: Iterable[str] = ("Nación", "NOA", "La Rioja"),
    empleo_tipo: str = "desestacionalizada",
    base_fecha: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Wide: fecha | Nación | NOA | La Rioja. Sin deflactar.

    - indicador='empleo': usa empleo_tipo (default desestacionalizada).
    - indicador='salario': siempre nivel nominal.
    - base_fecha: si se pasa, normaliza cada serie a 100 en ese mes.
    """
    tipo = empleo_tipo if indicador == "empleo" else "nivel"

    partes: dict[str, pd.Series] = {}
    for nivel in niveles:
        if nivel == "Nación":
            partes[nivel] = serie_nacional(indicador, tipo)
        elif nivel == "NOA":
            partes[nivel] = serie_noa(indicador, tipo)
        else:
            partes[nivel] = serie_provincia(nivel, indicador, tipo)

    wide = pd.DataFrame(partes).sort_index()

    if base_fecha is not None:
        base = pd.Timestamp(base_fecha)
        if base not in wide.index:
            raise ValueError(f"{base.date()} no está en el índice")
        wide = wide / wide.loc[base] * 100

    return wide.reset_index()


def salario_real_propio(
    niveles: Iterable[str] = ("Nación", "NOA", "La Rioja"),
    base_fecha: str | pd.Timestamp = "2017-01-01",
) -> pd.DataFrame:
    """Salario real construido con IPC NOA (serie disponible 2017+).

    Deflacta el salario nominal por el IPC NOA y normaliza a 100 en
    base_fecha. Recorta al rango donde el IPC existe (evita NaN).
    """
    ipc = cargar_ipc_noa()
    nominal = comparar("salario", niveles=niveles).set_index("fecha")

    # Recortar al rango del IPC para no arrastrar NaN
    nominal = nominal.loc[nominal.index >= ipc.index.min()]

    ipc_al = ipc.reindex(nominal.index, method="ffill")
    if ipc_al.isna().any():
        raise ValueError("IPC NOA tiene NaN tras reindex — revisar.")

    real = nominal.div(ipc_al, axis=0) * 100

    base = pd.Timestamp(base_fecha)
    if base not in real.index:
        raise ValueError(f"{base.date()} no está en el índice")
    real = real / real.loc[base] * 100
    return real.reset_index()


def salario_real_indec(
    niveles: Iterable[str] = ("Nación", "NOA", "La Rioja"),
    base_fecha: str | pd.Timestamp = "2022-01-01",
) -> pd.DataFrame:
    """Índice acumulado de la serie oficial 'Var % interanual real' (2022+).

    Como la serie es i.a., se ancla en base_fecha y se propaga 12 meses
    hacia adelante. Los 11 meses siguientes a base_fecha quedan en NaN
    (no se pueden derivar sin los valores del año previo).

    Resultado: solo los mismos meses del año que base_fecha quedan
    poblados (ej. si base=2022-01, solo eneros 2022–2026).
    """
    df = cargar_salario("var_real_interanual")
    partes: dict[str, pd.Series] = {}
    for nivel in niveles:
        if nivel == "Nación":
            s = df[df["jurisdiccion"] == "Total"]
            partes[nivel] = s.set_index("fecha")["valor"].sort_index()
        elif nivel == "NOA":
            emp = cargar_empleo("desestacionalizada")
            var_noa = df[df["jurisdiccion"].isin(NOA_PROVINCIAS)]
            piv = (var_noa.merge(emp, on=["fecha", "jurisdiccion"],
                                 suffixes=("_var", "_emp"))
                   .assign(pond=lambda x: x["valor_var"] * x["valor_emp"]))
            agg = piv.groupby("fecha").agg(p=("pond", "sum"),
                                           e=("valor_emp", "sum"))
            partes[nivel] = (agg["p"] / agg["e"]).sort_index()
        else:
            s = df[df["jurisdiccion"] == nivel]
            partes[nivel] = s.set_index("fecha")["valor"].sort_index()

    var_wide = pd.DataFrame(partes).sort_index()

    # Construir índice: nivel_real(m) = nivel_real(m-12) * (1 + var(m))
    out = pd.DataFrame(index=var_wide.index, columns=var_wide.columns,
                       dtype=float)
    base = pd.Timestamp(base_fecha)
    out.loc[base] = 100.0
    for col in var_wide.columns:
        for f in var_wide.index:
            if f == base:
                continue
            f_menos12 = f - pd.DateOffset(months=12)
            if (f_menos12 in out.index
                    and pd.notna(out.loc[f_menos12, col])
                    and pd.notna(var_wide.loc[f, col])):
                out.loc[f, col] = (out.loc[f_menos12, col]
                                   * (1 + var_wide.loc[f, col]))
    return out.reset_index()


def ratio_salarial(
    numerador: str = "La Rioja",
    denominador: str = "NOA",
    nominal: bool = True,
) -> pd.DataFrame:
    """Ratio de salario entre dos jurisdicciones (default LR / NOA)."""
    if nominal:
        num = serie_provincia(numerador, "salario", "nivel")
        if denominador == "NOA":
            den = serie_noa("salario", "nivel")
        elif denominador == "Nación":
            den = serie_nacional("salario", "nivel")
        else:
            den = serie_provincia(denominador, "salario", "nivel")
    else:
        wide = salario_real_propio(niveles=(numerador, denominador))
        wide = wide.set_index("fecha")
        num, den = wide[numerador], wide[denominador]

    out = pd.DataFrame({f"{numerador}_sobre_{denominador}": num / den})
    return out.reset_index()