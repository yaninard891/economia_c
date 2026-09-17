"""Visualizaciones específicas para el dashboard.

Todas recortadas a 2022-01 → actualidad. Paleta y estilo consistentes
con `src/visualizaciones.py`. Cada función devuelve (fig, ax) para
exportar como PNG o SVG.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

from src.visualizaciones import (
    PALETA, _finalizar, _media_movil, guardar,
    _cargar_dgip, _dgip_indice_real,
)

# Fecha de corte inferior para el dashboard
DESDE = "2022-01-01"

FIG_DIR_DASH = Path("dashboard/figuras")
FIG_DIR_DASH.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# DASH-1 — Contexto macro: VAB La Rioja 2022–2025
# ---------------------------------------------------------------------------

def dash_opex_rioja():
    """VAB nominal de La Rioja y share del país, 2022–2025.

    Solo 4 puntos anuales: se grafica con barras + línea dual.
    """
    from src.emae import opex_serie_provincia

    rioja = opex_serie_provincia("La Rioja")
    rioja = rioja[rioja["anio"] >= 2022].reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.bar(rioja["anio"].astype(str), rioja["vab_musd"],
                  color=PALETA["La Rioja"], width=0.5, label="VAB (USD M)")
    for bar, v in zip(bars, rioja["vab_musd"]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 5,
                f"{v:.0f}", ha="center", va="bottom",
                fontsize=10, color=PALETA["La Rioja"], fontweight="bold")
    ax.set_ylabel("VAB (millones USD)", color=PALETA["La Rioja"])
    ax.tick_params(axis="y", colors=PALETA["La Rioja"])
    ax.set_ylim(0, rioja["vab_musd"].max() * 1.2)
    ax.grid(True, axis="y", alpha=0.3)

    ax2 = ax.twinx()
    ax2.plot(rioja["anio"].astype(str), rioja["share_pais_pct"],
             marker="o", markersize=9, lw=2.4,
             color=PALETA["Nación"], label="Share del país")
    for x, v in zip(rioja["anio"].astype(str), rioja["share_pais_pct"]):
        ax2.text(x, v + 0.008, f"{v:.2f}%",
                 ha="center", va="bottom", fontsize=9,
                 color=PALETA["Nación"])
    ax2.set_ylabel("% del VAB nacional", color=PALETA["Nación"])
    ax2.tick_params(axis="y", colors=PALETA["Nación"])
    ax2.set_ylim(0, rioja["share_pais_pct"].max() * 1.25)
    ax2.spines["top"].set_visible(False)

    # Anotación de la caída 2025
    ax.annotate(
        "−25,7%",
        xy=(3, rioja["vab_musd"].iloc[-1] * 0.5),
        xytext=(0, 0), textcoords="offset points",
        fontsize=12, color=PALETA["acento"], fontweight="bold",
        ha="center",
    )

    _finalizar(
        fig,
        "La Rioja en el producto nacional (2022–2025)",
        "VAB nominal (barras) y participación en el VAB nacional (línea).",
        "Fuente: INDEC-OPEX.",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# DASH-2 — Benchmark provincial 2022–2025
# ---------------------------------------------------------------------------

def dash_opex_benchmark():
    """Crecimiento % del VAB provincial 2022→2025, comparado."""
    from src.emae import opex_benchmark

    provincias = ["La Rioja", "Córdoba", "Santa Fe", "Tucumán",
                  "Ciudad Autónoma de Buenos Aires", "San Juan", "Neuquén"]
    bm = opex_benchmark(provincias=provincias)
    bm = bm[bm.index >= 2022]

    # Para cada provincia, crecimiento 2022 → 2025
    crec = []
    for p in provincias:
        if p not in bm.columns:
            continue
        v0 = bm[p].loc[2022]
        v1 = bm[p].loc[2025]
        crec.append({"provincia": p, "crec_pct": 100 * (v1 / v0 - 1)})

    df = pd.DataFrame(crec).sort_values("crec_pct")
    etiquetas = [p.replace("Ciudad Autónoma de Buenos Aires", "CABA")
                 for p in df["provincia"]]
    colores = [PALETA["La Rioja"] if p == "La Rioja"
               else PALETA["gris_texto"] for p in df["provincia"]]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    y = list(range(len(df)))[::-1]
    bars = ax.barh(y, df["crec_pct"], color=colores, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas, fontsize=10)
    for bar, v in zip(bars, df["crec_pct"]):
        offset = 3 if v >= 0 else -3
        ha = "left" if v >= 0 else "right"
        ax.text(v + offset, bar.get_y() + bar.get_height() / 2,
                f"{v:+.1f}%", va="center", ha=ha, fontsize=9,
                color="#2c3e50", fontweight="bold")
    ax.axvline(0, color=PALETA["gris_texto"], lw=0.8)
    ax.set_xlabel("Crecimiento del VAB 2022 → 2025 (%)")
    ax.grid(True, axis="x", alpha=0.4)
    ax.set_axisbelow(True)

    _finalizar(
        fig,
        "Crecimiento del VAB provincial (2022 → 2025)",
        "Variación porcentual acumulada en dólares corrientes. La Rioja es la única con caída.",
        "Fuente: INDEC-OPEX.",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# DASH-3 — Empleo: LR vs NOA vs Nación (2022 → actualidad)
# ---------------------------------------------------------------------------

def dash_empleo_ciclo():
    """Empleo desestacionalizado, base ene-2022 = 100."""
    from src.regional import comparar

    df = comparar("empleo", base_fecha="2022-01-01").set_index("fecha")
    df = df[df.index >= DESDE]
    df_mm = _media_movil(df, ventana=3)

    fig, ax = plt.subplots(figsize=(10, 4.8))

    for nivel, color in [("Nación", PALETA["Nación"]),
                         ("NOA", PALETA["NOA"]),
                         ("La Rioja", PALETA["La Rioja"])]:
        lw = 2.4 if nivel == "La Rioja" else 1.4
        ax.plot(df_mm.index, df_mm[nivel], label=nivel, color=color, lw=lw)

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.5)
    ax.set_ylabel("Índice (ene-2022 = 100)")
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", ncol=3)

    pico = df_mm["La Rioja"].idxmax()
    ax.annotate(
        f"pico {df_mm.loc[pico, 'La Rioja']:.0f}",
        xy=(pico, df_mm.loc[pico, "La Rioja"]),
        xytext=(0, 15), textcoords="offset points",
        fontsize=9, color=PALETA["La Rioja"], ha="center", fontweight="bold",
        arrowprops=dict(arrowstyle="-", color=PALETA["La Rioja"], lw=0.6),
    )

    _finalizar(
        fig,
        "Empleo privado formal: La Rioja, NOA y Nación",
        "Serie desestacionalizada, base ene-2022 = 100, media móvil 3 meses.",
        "Fuente: SIPA-OEDE.",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# DASH-4 — Salario real: LR vs NOA vs Nación (2022 → actualidad)
# ---------------------------------------------------------------------------

def dash_salario_real():
    """Salario real deflactado por IPC NOA, base ene-2022 = 100."""
    from src.regional import salario_real_propio

    df = salario_real_propio(base_fecha="2022-01-01").set_index("fecha")
    df = df[df.index >= DESDE]
    df_mm = _media_movil(df, ventana=3)

    fig, ax = plt.subplots(figsize=(10, 4.8))

    for nivel, color in [("Nación", PALETA["Nación"]),
                         ("NOA", PALETA["NOA"]),
                         ("La Rioja", PALETA["La Rioja"])]:
        lw = 2.4 if nivel == "La Rioja" else 1.4
        ax.plot(df_mm.index, df_mm[nivel], label=nivel, color=color, lw=lw)

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.5)
    ax.set_ylabel("Índice (ene-2022 = 100)")
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", ncol=3)

    # Ratio final
    ratio_lr_nac = df_mm["La Rioja"].iloc[-1] / df_mm["Nación"].iloc[-1]
    ax.text(
        0.98, 0.95,
        f"Ratio LR/Nación: {ratio_lr_nac:.2f}",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=10, color=PALETA["La Rioja"], fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                  edgecolor=PALETA["gris_claro"], linewidth=0.8),
    )

    _finalizar(
        fig,
        "Salario real por puesto: La Rioja, NOA y Nación",
        "Deflactado por IPC NOA. Base ene-2022 = 100, media móvil 3 meses.",
        "Fuente: SIPA-OEDE e INDEC (IPC regional).",
        ax,
    )
    return fig, ax


# ---------------------------------------------------------------------------
# DASH-5 — DGIP: nominal vs real
# ---------------------------------------------------------------------------

def dash_dgip():
    """DGIP 2022–2025: nominal vs real."""
    import src.dgip as dg

    df = _cargar_dgip()
    total = dg.dgip_total_anual(df).copy()

    base_nom = total.loc[total["anio"] == 2022, "impuesto_total"].iloc[0]
    total["indice_nominal"] = 100 * total["impuesto_total"] / base_nom
    total = _dgip_indice_real(total)

    fig, ax = plt.subplots(figsize=(9, 4.8))

    ax.plot(total["anio"], total["indice_nominal"],
            marker="o", markersize=10, lw=2.6,
            color=PALETA["Nación"], label="Nominal")
    ax.plot(total["anio"], total["indice_real"],
            marker="o", markersize=10, lw=2.6,
            color=PALETA["La Rioja"], label="Real (deflactado IPC NOA)")

    for _, row in total.iterrows():
        ax.text(row["anio"], row["indice_nominal"] + 80,
                f"{row['indice_nominal']:.0f}",
                ha="center", va="bottom", fontsize=10,
                color=PALETA["Nación"], fontweight="bold")
        ax.text(row["anio"], row["indice_real"] - 80,
                f"{row['indice_real']:.0f}",
                ha="center", va="top", fontsize=10,
                color=PALETA["La Rioja"], fontweight="bold")

    ax.axhline(100, color=PALETA["gris_texto"], lw=0.8, ls="--", alpha=0.6)
    ax.set_ylabel("Índice (2022 = 100)")
    ax.set_xticks(total["anio"])
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")

    _finalizar(
        fig,
        "DGIP tecnológico: ingreso nominal vs real (2022–2025)",
        "Índice base 2022 = 100. La brecha entre las series es el efecto inflacionario.",
        "Fuente: DGIP La Rioja e INDEC (IPC NOA).",
        ax,
    )
    return fig, ax