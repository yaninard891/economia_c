"""Visualizaciones estándar para el informe y el dashboard.

Paleta y estilo consistentes. Cada función devuelve (fig, ax) para
permitir ajustes finos antes de exportar o embeber en Quarto.

Uso típico:
    from src.visualizaciones import fig_empleo_comparado, guardar
    fig, ax = fig_empleo_comparado()
    guardar(fig, "informe/figuras/empleo_comparado.png")

Para Quarto, dentro de una celda de codigo con echo:false,
llamar directamente a la funcion y devolver la figura.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

from src.regional import (
    comparar, salario_real_propio, ratio_salarial,
)

# ---------------------------------------------------------------------------
# Estilo global
# ---------------------------------------------------------------------------

PALETA = {
    "La Rioja":   "#1f4e79",
    "NOA":        "#e67e22",
    "Nación":     "#7f8c8d",
    "acento":     "#c0392b",
    "positivo":   "#27ae60",
    "gris_claro": "#d5dbdb",
    "gris_texto": "#566573",
}

plt.rcParams.update({
    "figure.dpi":         110,
    "savefig.dpi":        150,
    "font.family":        "DejaVu Sans",
    "font.size":          10,
    "axes.titlesize":     12,
    "axes.titleweight":   "bold",
    "axes.labelsize":     10,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.edgecolor":     PALETA["gris_texto"],
    "axes.labelcolor":    "#2c3e50",
    "xtick.color":        PALETA["gris_texto"],
    "ytick.color":        PALETA["gris_texto"],
    "grid.color":         PALETA["gris_claro"],
    "grid.linewidth":     0.6,
    "legend.frameon":     False,
    "legend.fontsize":    9,
})

FIG_DIR = Path("informe/figuras")
FIG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finalizar(
    fig: plt.Figure,
    titulo: str,
    subtitulo: str | None = None,
    fuente: str = "Fuente: OEDE-SIPA / INDEC",
    ax: plt.Axes | None = None,
) -> None:
    """Agrega título, subtítulo y fuente al pie. Layout ajustado."""
    if ax is None:
        ax = fig.axes[0]

    ax.set_title(titulo, loc="left", pad=20 if subtitulo else 12)
    if subtitulo:
        ax.text(
            0, 1.02, subtitulo,
            transform=ax.transAxes,
            fontsize=9.5, color=PALETA["gris_texto"],
            ha="left", va="bottom",
        )

    fig.text(
        0.01, -0.02, fuente,
        fontsize=8, color=PALETA["gris_texto"],
        ha="left", va="top",
    )
    fig.tight_layout()


def guardar(fig: plt.Figure, path: str | Path, dpi: int = 150) -> Path:
    """Guarda la figura y devuelve el path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    return path


def _media_movil(df: pd.DataFrame, ventana: int = 3) -> pd.DataFrame:
    """Media móvil centrada. Pensada para suavizar series mensuales ruidosas."""
    return df.rolling(window=ventana, center=True, min_periods=2).mean()


# ---------------------------------------------------------------------------
# F3 — Empleo: LR vs NOA vs Nación (índice 2019=100)
# ---------------------------------------------------------------------------

def fig_empleo_comparado(base_fecha: str = "2019-01-01", suavizar: bool = True):
    """Las 3 series de empleo formal, con opción de suavizar con MM3."""
    df = comparar("empleo", base_fecha=base_fecha).set_index("fecha")
    df_suave = _media_movil(df, ventana=3) if suavizar else None

    fig, ax = plt.subplots(figsize=(9, 4.8))

    colores = {
        "Nación":    PALETA["Nación"],
        "NOA":       PALETA["NOA"],
        "La Rioja":  PALETA["La Rioja"],
    }

    if suavizar:
        for nivel, color in colores.items():
            ax.plot(df.index, df[nivel], color=color, lw=0.7,
                    alpha=0.25, zorder=1)

    plot_df = df_suave if suavizar else df
    for nivel, color in colores.items():
        lw = 2.3 if nivel == "La Rioja" else 1.4
        ax.plot(plot_df.index, plot_df[nivel], label=nivel,
                color=color, lw=lw, zorder=2)

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.5)
    ax.set_ylabel("Índice (ene-2019 = 100)")
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f"))
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", ncol=3)

    pico = plot_df["La Rioja"].idxmax()
    ax.annotate(
        f"pico {plot_df.loc[pico, 'La Rioja']:.0f}",
        xy=(pico, plot_df.loc[pico, "La Rioja"]),
        xytext=(0, 18), textcoords="offset points",
        fontsize=8.5, color=PALETA["La Rioja"], ha="center",
        arrowprops=dict(arrowstyle="-", color=PALETA["La Rioja"], lw=0.6),
    )
    ax.annotate(
        f"{plot_df['La Rioja'].iloc[-1]:.0f}",
        xy=(plot_df.index[-1], plot_df["La Rioja"].iloc[-1]),
        xytext=(8, -4), textcoords="offset points",
        fontsize=8.5, color=PALETA["La Rioja"], ha="left",
    )

    subtitulo = "Serie desestacionalizada. Índice base enero 2019 = 100."
    if suavizar:
        subtitulo += " Línea fuerte: media móvil 3 meses. Línea tenue: serie mensual."

    _finalizar(
        fig,
        "Empleo privado formal: La Rioja, NOA y Nación",
        subtitulo,
        "Fuente: SIPA-OEDE, Secretaría de Trabajo, Empleo y Seguridad Social.",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# F4 — Zoom del ciclo riojano 2019–2026
# ---------------------------------------------------------------------------

def fig_empleo_zoom(suavizar: bool = True):
    """Zoom 2019+ con anotaciones del despegue y el colapso."""
    df = comparar("empleo", base_fecha="2019-01-01").set_index("fecha")
    df = df[df.index >= "2019-01-01"]
    df_suave = _media_movil(df, ventana=3) if suavizar else None

    fig, ax = plt.subplots(figsize=(9, 4.8))

    ax.plot(df.index, df["NOA"], label="NOA",
            color=PALETA["NOA"], lw=1.3, alpha=0.85)
    ax.plot(df.index, df["Nación"], label="Nación",
            color=PALETA["Nación"], lw=1.3, alpha=0.85)

    if suavizar:
        ax.plot(df.index, df["La Rioja"], color=PALETA["La Rioja"],
                lw=0.8, alpha=0.3, zorder=1)
        ax.plot(df_suave.index, df_suave["La Rioja"], label="La Rioja (MM3)",
                color=PALETA["La Rioja"], lw=2.4, zorder=3)
    else:
        ax.plot(df.index, df["La Rioja"], label="La Rioja",
                color=PALETA["La Rioja"], lw=2.2, zorder=3)

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.5)
    ax.set_ylabel("Índice (ene-2019 = 100)")
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", ncol=3)

    ax.axvspan(pd.Timestamp("2023-01-01"), pd.Timestamp("2024-12-31"),
               color=PALETA["positivo"], alpha=0.08)
    ax.axvspan(pd.Timestamp("2025-01-01"), pd.Timestamp("2026-12-31"),
               color=PALETA["acento"], alpha=0.08)

    ax.text(pd.Timestamp("2023-07-01"), ax.get_ylim()[1] * 0.98,
            "boom", ha="center", va="top",
            fontsize=9, color=PALETA["positivo"], style="italic")
    ax.text(pd.Timestamp("2025-06-01"), ax.get_ylim()[1] * 0.98,
            "bust", ha="center", va="top",
            fontsize=9, color=PALETA["acento"], style="italic")

    subtitulo = "Empleo privado formal desestacionalizado. Índice base ene-2019 = 100."
    if suavizar:
        subtitulo += " La Rioja: MM3 (fuerte) sobre serie mensual (tenue)."

    _finalizar(
        fig,
        "El ciclo riojano: despegue 2023–2024 y caída 2025–2026",
        subtitulo,
        "Fuente: SIPA-OEDE. El sombreado marca las fases del ciclo provincial.",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# F6 — Salario real (construido con IPC NOA)
# ---------------------------------------------------------------------------

def fig_salario_real_propio(base_fecha: str = "2017-01-01", suavizar: bool = True):
    """Salario real de las 3 jurisdicciones, base ene-2017 = 100."""
    df = salario_real_propio(base_fecha=base_fecha).set_index("fecha")
    df_suave = _media_movil(df, ventana=3) if suavizar else None

    fig, ax = plt.subplots(figsize=(9, 4.8))

    colores = {
        "Nación":   PALETA["Nación"],
        "NOA":      PALETA["NOA"],
        "La Rioja": PALETA["La Rioja"],
    }

    if suavizar:
        for nivel, color in colores.items():
            ax.plot(df.index, df[nivel], color=color, lw=0.7,
                    alpha=0.25, zorder=1)

    plot_df = df_suave if suavizar else df
    for nivel, color in colores.items():
        lw = 2.3 if nivel == "La Rioja" else 1.4
        ax.plot(plot_df.index, plot_df[nivel], label=nivel,
                color=color, lw=lw, zorder=2)

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.5)
    ax.set_ylabel(f"Índice (ene-{base_fecha[:4]} = 100)")
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", ncol=3)

    min_f = plot_df["La Rioja"].idxmin()
    ax.annotate(
        f"piso {plot_df.loc[min_f, 'La Rioja']:.0f}",
        xy=(min_f, plot_df.loc[min_f, "La Rioja"]),
        xytext=(0, -20), textcoords="offset points",
        fontsize=8.5, color=PALETA["La Rioja"], ha="center",
        arrowprops=dict(arrowstyle="-", color=PALETA["La Rioja"], lw=0.6),
    )

    subtitulo = (f"Deflactado por IPC NOA (Región Noroeste, INDEC). "
                 f"Base ene-{base_fecha[:4]} = 100.")
    if suavizar:
        subtitulo += " Línea fuerte: MM3."

    _finalizar(
        fig,
        "Salario real por puesto: La Rioja, NOA y Nación",
        subtitulo,
        "Fuente: SIPA-OEDE (remuneraciones) e INDEC (IPC regional).",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# F7 — Ratio salarial LR / Nación y LR / NOA
# ---------------------------------------------------------------------------

def fig_ratio_salarial(suavizar: bool = False):
    """Ratio La Rioja / Nación y La Rioja / NOA del salario nominal."""
    r_nac = ratio_salarial("La Rioja", "Nación").set_index("fecha")
    r_noa = ratio_salarial("La Rioja", "NOA").set_index("fecha")
    df = pd.concat([r_nac, r_noa], axis=1)
    df = df[df.index >= "2017-01-01"]
    df_suave = _media_movil(df, ventana=3) if suavizar else None

    fig, ax = plt.subplots(figsize=(9, 4.8))

    if suavizar:
        ax.plot(df.index, df["La Rioja_sobre_Nación"],
                color=PALETA["La Rioja"], lw=0.7, alpha=0.25)
        ax.plot(df.index, df["La Rioja_sobre_NOA"],
                color=PALETA["NOA"], lw=0.7, alpha=0.25)
        plot_df = df_suave
    else:
        plot_df = df

    ax.plot(plot_df.index, plot_df["La Rioja_sobre_Nación"],
            label="La Rioja / Nación",
            color=PALETA["La Rioja"], lw=2.2)
    ax.plot(plot_df.index, plot_df["La Rioja_sobre_NOA"],
            label="La Rioja / NOA",
            color=PALETA["NOA"], lw=1.6)
    ax.axhline(1.0, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.6)

    ax.set_ylabel("Ratio salarial")
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f"))
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", ncol=2)

    ax.text(plot_df.index[-1], plot_df["La Rioja_sobre_Nación"].iloc[-1],
            f"  {plot_df['La Rioja_sobre_Nación'].iloc[-1]:.2f}",
            va="center", ha="left", fontsize=8.5,
            color=PALETA["La Rioja"])
    ax.text(plot_df.index[-1], plot_df["La Rioja_sobre_NOA"].iloc[-1],
            f"  {plot_df['La Rioja_sobre_NOA'].iloc[-1]:.2f}",
            va="center", ha="left", fontsize=8.5,
            color=PALETA["NOA"])

    subtitulo = "Salario nominal promedio por puesto. Ratio = remuneración LR / contraparte."
    if suavizar:
        subtitulo += " Línea fuerte: MM3."

    _finalizar(
        fig,
        "La brecha salarial riojana se amplía",
        subtitulo,
        "Fuente: SIPA-OEDE. Ratio < 1 indica que La Rioja paga menos.",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# DGIP — Régimen de promoción tecnológica
# ---------------------------------------------------------------------------

def _cargar_dgip():
    """Carga la serie DGIP tecnológico de los 2 PDFs disponibles."""
    import src.dgip as dg
    pdfs = [
        "reports/bibliografia/dgip_informe_tecnologico_2022-2023.pdf",
        "reports/bibliografia/dgip_informe_tecnologico_2024-2025.pdf",
    ]
    return dg.cargar_dgip_tecnologico_multi(pdfs)


def _dgip_indice_real(total: pd.DataFrame) -> pd.DataFrame:
    """Calcula índice real de impuesto DGIP, base 2022 = 100.

    Deflacta por IPC NOA (promedio anual) y normaliza.
    """
    from src.regional import cargar_ipc_noa

    ipc = cargar_ipc_noa()
    ipc_anual = ipc.groupby(ipc.index.year).mean()
    total = total.copy()
    total["ipc_anual"] = total["anio"].map(ipc_anual)
    total["impuesto_real"] = total["impuesto_total"] / total["ipc_anual"]
    base = total.loc[total["anio"] == 2022, "impuesto_real"].iloc[0]
    total["indice_real"] = 100 * total["impuesto_real"] / base
    return total


def fig_dgip_real():
    """Recaudación DGIP real (deflactada por IPC NOA), base 2022 = 100."""
    import src.dgip as dg

    df = _cargar_dgip()
    total = dg.dgip_total_anual(df)
    total = _dgip_indice_real(total)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(total["anio"].astype(str), total["indice_real"],
                  color=PALETA["La Rioja"], width=0.55)
    for bar, val in zip(bars, total["indice_real"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 6,
                f"{val:.0f}", ha="center", va="bottom",
                fontsize=10, color=PALETA["La Rioja"], fontweight="bold")

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.6)
    ax.set_ylabel("Índice real (2022 = 100)")
    ax.set_ylim(0, total["indice_real"].max() * 1.18)
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)

    _finalizar(
        fig,
        "Recaudación DGIP real: ×3,16 entre 2022 y 2025",
        "Impuesto tecnológico DGIP deflactado por IPC NOA (INDEC). Base 2022 = 100.",
        "Fuente: DGIP La Rioja (informes 2022-23 y 2024-25) e INDEC (IPC regional).",
        ax,
    )
    return fig, ax


def fig_dgip_contribuyentes():
    """Contribuyentes DGIP: convenio multilateral vs locales (2022–2025)."""
    import src.dgip as dg

    df = _cargar_dgip()
    total = dg.dgip_total_anual(df)
    anios = total["anio"].astype(str).tolist()
    x = list(range(len(anios)))
    w = 0.38

    fig, ax = plt.subplots(figsize=(8, 4.5))
    b1 = ax.bar([i - w / 2 for i in x], total["contrib_conv"], w,
                label="Convenio multilateral", color=PALETA["Nación"])
    b2 = ax.bar([i + w / 2 for i in x], total["contrib_local"], w,
                label="Contribuyentes locales", color=PALETA["acento"])

    for bars in (b1, b2):
        for bar in bars:
            v = int(bar.get_height())
            ax.text(bar.get_x() + bar.get_width() / 2, v + 25,
                    f"{v:,}".replace(",", "."),
                    ha="center", va="bottom", fontsize=8.5)

    ax.set_xticks(x)
    ax.set_xticklabels(anios)
    ax.set_ylabel("Cantidad de contribuyentes")
    ax.legend(loc="upper right", ncol=2)
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(0, total["contrib_conv"].max() * 1.15)

    _finalizar(
        fig,
        "Contribuyentes DGIP: más convenio multilateral, menos locales",
        "Contribuyentes declarados por año. Los locales cayeron 26% entre 2022 y 2025.",
        "Fuente: DGIP La Rioja.",
        ax,
    )
    return fig, ax


def fig_dgip_estructura(anio: int = 2025, top_n: int = 3):
    """Top actividades que concentran el impuesto DGIP en un año."""
    df = _cargar_dgip()
    sub = df[df["anio"] == anio].copy()
    sub = (sub.groupby("actividad")["impuesto_total"].sum()
           .sort_values(ascending=False))

    top = sub.head(top_n)
    resto = sub.iloc[top_n:].sum()
    total = sub.sum()

    labels = [f"{a[:55]}" for a in top.index] + ["Resto (10 actividades)"]
    valores = list(top.values) + [resto]
    shares = [100 * v / total for v in valores]

    colores = [PALETA["La Rioja"], "#3498db", PALETA["NOA"],
               PALETA["gris_claro"]]

    fig, ax = plt.subplots(figsize=(9, 4.2))
    y_pos = list(range(len(labels)))[::-1]
    bars = ax.barh(y_pos, valores, color=colores[:len(labels)], height=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, max(valores) * 1.35)

    for bar, s, v in zip(bars, shares, valores):
        ax.text(bar.get_width() + total * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{s:.1f}%  (${v/1e6:,.0f} M)",
                va="center", fontsize=9, color="#2c3e50")

    ax.set_xlabel(f"Impuesto DGIP {anio} (millones de $)")
    ax.xaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, p: f"{x/1e6:,.0f}"))
    ax.grid(True, axis="x", alpha=0.4)
    ax.set_axisbelow(True)

    _finalizar(
        fig,
        f"Concentración del impuesto DGIP tecnológico ({anio})",
        f"Tres actividades concentran {sum(shares[:top_n]):.1f}% del impuesto total del régimen.",
        "Fuente: DGIP La Rioja.",
        ax,
    )
    return fig, ax


def fig_dgip_nominal_vs_real():
    """Impuesto DGIP nominal vs real, ambos indexados a 100 en 2022."""
    import src.dgip as dg

    df = _cargar_dgip()
    total = dg.dgip_total_anual(df).copy()

    base_nom = total.loc[total["anio"] == 2022, "impuesto_total"].iloc[0]
    total["indice_nominal"] = 100 * total["impuesto_total"] / base_nom

    total = _dgip_indice_real(total)

    fig, ax = plt.subplots(figsize=(9, 4.8))

    ax.plot(total["anio"], total["indice_nominal"],
            marker="o", markersize=8, lw=2.4,
            color=PALETA["Nación"], label="Nominal")
    ax.plot(total["anio"], total["indice_real"],
            marker="o", markersize=8, lw=2.4,
            color=PALETA["La Rioja"], label="Real (deflactado IPC NOA)")

    for _, row in total.iterrows():
        ax.text(row["anio"], row["indice_nominal"] + 50,
                f"{row['indice_nominal']:.0f}",
                ha="center", va="bottom", fontsize=9,
                color=PALETA["Nación"], fontweight="bold")
        ax.text(row["anio"], row["indice_real"] - 50,
                f"{row['indice_real']:.0f}",
                ha="center", va="top", fontsize=9,
                color=PALETA["La Rioja"], fontweight="bold")

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.6)
    ax.set_ylabel("Índice (2022 = 100)")
    ax.set_xticks(total["anio"])
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")

    _finalizar(
        fig,
        "Recaudación DGIP: nominal vs real",
        "La brecha entre las dos series es el efecto inflacionario. Base 2022 = 100.",
        "Fuente: DGIP La Rioja (informes 2022-23 y 2024-25) e INDEC (IPC NOA).",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# M1 — IPC interanual con bandas de gobierno
# ---------------------------------------------------------------------------

def fig_ipc_gobiernos():
    """IPC variación interanual (Región NOA vs Total nacional) con bandas
    de gobierno. Períodos: Macri (hasta dic-2019), FdT (dic-2019 a
    dic-2023), Milei (dic-2023 en adelante). La serie arranca en 2017-01,
    por lo que el primer período queda parcial."""
    from src.funciones import cargar_ipc_regional

    df = cargar_ipc_regional()

    def _ia(df_sub):
        s = df_sub.set_index("fecha")["valor"].sort_index()
        if s.abs().max() < 1:  # decimal → porcentaje
            s = s * 100
        idx = (1 + s / 100).cumprod()
        return (idx / idx.shift(12) - 1).dropna() * 100

    noa = df[(df["region"] == "Región Noroeste") &
             (df["categoria"] == "Nivel general")]
    nac = df[(df["region"] == "Total nacional") &
             (df["categoria"] == "Nivel general")]

    ia_noa = _ia(noa)
    ia_nac = _ia(nac)

    fig, ax = plt.subplots(figsize=(10, 5))

    gobiernos = [
        ("Macri\n(2015-2019)", "2015-12-10", "2019-12-10", "#7f8c8d"),
        ("FdT\n(2019-2023)",   "2019-12-10", "2023-12-10", "#3498db"),
        ("Milei\n(2023-2027)", "2023-12-10", "2027-12-10", "#9b59b6"),
    ]
    ymax = max(ia_noa.max(), ia_nac.max())
    for nombre, ini, fin, color in gobiernos:
        ax.axvspan(pd.Timestamp(ini), pd.Timestamp(fin),
                   color=color, alpha=0.06, zorder=0)
        centro = pd.Timestamp(ini) + (pd.Timestamp(fin) - pd.Timestamp(ini)) / 2
        ax.text(centro, ymax * 1.02, nombre,
                ha="center", va="bottom", fontsize=9,
                color=color, fontweight="bold")

    ax.plot(ia_noa.index, ia_noa.values,
            color=PALETA["La Rioja"], lw=2.4, label="Región NOA")
    ax.plot(ia_nac.index, ia_nac.values,
            color=PALETA["Nación"], lw=1.4, label="Total nacional",
            alpha=0.85)

    pico_fecha = ia_noa.idxmax()
    pico_val = ia_noa.max()
    ax.annotate(
        f"pico {pico_val:.0f}%",
        xy=(pico_fecha, pico_val),
        xytext=(10, 10), textcoords="offset points",
        fontsize=9, color=PALETA["La Rioja"], fontweight="bold",
        arrowprops=dict(arrowstyle="-", color=PALETA["La Rioja"], lw=0.7),
    )

    ax.set_ylabel("Variación interanual (%)")
    ax.set_ylim(0, ymax * 1.12)
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", ncol=2)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))

    _finalizar(
        fig,
        "Inflación interanual: Región NOA vs Nación",
        "IPC Nivel general, variación i.a. calculada sobre índice acumulado. "
        "Bandas: períodos de gobierno. La serie arranca en 2017.",
        "Fuente: INDEC, IPC por región.",
        ax,
    )
    return fig, ax