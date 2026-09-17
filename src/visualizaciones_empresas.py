"""
src/visualizaciones_empresas.py
================================
Figuras para el informe Quarto:
- Empresas totales y de Economía del Conocimiento (Ley 27.506) en La Rioja
- Empleo del sector EC y su participación en el empleo provincial
- Elasticidad empleo-empresas
- Intensidad empresarial EC por provincia

Paleta coherente con el resto del informe:
  - La Rioja: #1f4e79 (azul)
  - NOA: #e67e22 (naranja)
  - Nación: #7f8c8d (gris)
  - EC: #2eb8b8 (turquesa)
"""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


# ===========================================================================
# Configuración global
# ===========================================================================

COLOR_LR      = "#1f4e79"
COLOR_NOA     = "#e67e22"
COLOR_NACION  = "#7f8c8d"
COLOR_EC      = "#2eb8b8"
COLOR_GRIS    = "#b0b0b0"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size":   9,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.25,
    "grid.linestyle":    ":",
    "figure.dpi":        120,
    "savefig.dpi":       200,
})


# ===========================================================================
# Helpers
# ===========================================================================

def _guardar(fig, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ===========================================================================
# 1. EMPRESAS EC — Serie y benchmark
# ===========================================================================

def fig_empresas_serie(
    tot: pd.DataFrame,
    ec: pd.DataFrame,
    ruta: Path,
    anio_ini: int = 2017,
    anio_fin: int = 2025,
) -> None:
    """
    Serie de empresas totales (línea gris) y empresas EC Ley 27.506
    (turquesa, eje secundario).

    `tot` = DataFrame de serie_empresas(): anio, total_empresas
    `ec`  = DataFrame de serie_ec(): anio, empresas_ec
    """
    tot = tot[(tot["anio"] >= anio_ini) & (tot["anio"] <= anio_fin)].copy()
    ec  = ec[(ec["anio"]  >= anio_ini) & (ec["anio"]  <= anio_fin)].copy()

    merge = tot.merge(ec, on="anio", how="outer").sort_values("anio")

    fig, ax1 = plt.subplots(figsize=(7.5, 3.6))

    # Empresas totales (eje izq)
    ax1.plot(merge["anio"], merge["total_empresas"],
             marker="o", ms=5, color=COLOR_GRIS, lw=2,
             label="Empresas totales provincia")
    ax1.set_ylabel("Empresas totales", color=COLOR_GRIS)
    ax1.tick_params(axis="y", labelcolor=COLOR_GRIS)
    if merge["total_empresas"].notna().any():
        ax1.set_ylim(0, merge["total_empresas"].max() * 1.25)
    ax1.set_xticks(merge["anio"])

    # Empresas EC (eje secundario)
    ax2 = ax1.twinx()
    ax2.plot(merge["anio"], merge["empresas_ec"],
             marker="s", ms=6, color=COLOR_EC, lw=2.4,
             label="Empresas Ley 27.506")
    ax2.set_ylabel("Empresas Ley 27.506", color=COLOR_EC)
    ax2.tick_params(axis="y", labelcolor=COLOR_EC)
    if merge["empresas_ec"].notna().any():
        ax2.set_ylim(0, merge["empresas_ec"].max() * 1.6)
    ax2.grid(False)

    # Etiquetas de valor sobre la línea EC
    for _, r in merge.iterrows():
        if pd.notna(r["empresas_ec"]):
            ax2.annotate(f"{int(r['empresas_ec'])}",
                         (r["anio"], r["empresas_ec"]),
                         textcoords="offset points", xytext=(0, 7),
                         ha="center", fontsize=8, color=COLOR_EC, weight="bold")

    # Marcar hueco de 2023
    if 2023 not in merge["anio"].values:
        ax1.axvline(2023, color="#d9534f", ls="--", lw=1, alpha=0.6)
        ax1.annotate("2023: sin datos\nen la fuente",
                     xy=(2023, ax1.get_ylim()[1] * 0.94),
                     fontsize=7.5, color="#d9534f", ha="center")

    # Leyendas combinadas
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left",
               frameon=False, fontsize=8.5)

    ax1.set_title("Empresas totales y de Economía del Conocimiento — La Rioja",
                  fontsize=10, weight="bold", color=COLOR_LR, pad=10)

    _guardar(fig, ruta)


# ---------------------------------------------------------------------------

def fig_empresas_benchmark(
    bench: pd.DataFrame,
    ruta: Path,
    anio: int = 2024,
) -> None:
    """
    Barras horizontales: empresas EC por provincia (Ley 27.506).
    `bench` = DataFrame de benchmark_provincias(): provincia, empresas_ec
    """
    b = bench.dropna(subset=["empresas_ec"]).sort_values("empresas_ec",
                                                         ascending=True).copy()
    if b.empty:
        return
    colores = [COLOR_LR if p == "La Rioja" else COLOR_GRIS for p in b["provincia"]]

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    bars = ax.barh(b["provincia"], b["empresas_ec"],
                   color=colores, edgecolor="white", height=0.7)

    maxv = b["empresas_ec"].max()
    for bar, val in zip(bars, b["empresas_ec"]):
        ax.text(val + maxv * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{int(val):,}".replace(",", "."),
                va="center", fontsize=8, color="#333")

    ax.set_xlabel("Empresas Ley 27.506")
    ax.set_title(f"Empresas EC por provincia — Ley 27.506 — {anio}",
                 fontsize=10, weight="bold", color=COLOR_LR, pad=10)
    ax.set_xlim(0, maxv * 1.12)

    _guardar(fig, ruta)


# ---------------------------------------------------------------------------

def fig_empresas_top_ramas(
    det: pd.DataFrame,
    ruta: Path,
    anio: int = 2024,
    top: int = 10,
) -> None:
    """
    Barras horizontales: top ramas EC en La Rioja para un año.
    `det` = DataFrame de detalle_ramas(): rama, descripcion, empresas, pct
    """
    d = det.head(top).sort_values("empresas", ascending=True).copy()
    if d.empty:
        return

    # Acortar descripciones largas
    d["corta"] = d["descripcion"].apply(
        lambda s: s if len(s) <= 45 else s[:45] + "…"
    )

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bars = ax.barh(d["corta"], d["empresas"], color=COLOR_EC,
                   edgecolor="white", height=0.7)

    maxv = d["empresas"].max()
    for bar, val, pct in zip(bars, d["empresas"], d["pct"]):
        ax.text(val + maxv * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(val)}  ({pct:.1f}%)",
                va="center", fontsize=8, color="#333")

    ax.set_xlabel("Empresas")
    ax.set_title(f"Top {top} ramas EC — La Rioja {anio}",
                 fontsize=10, weight="bold", color=COLOR_LR, pad=10)
    ax.set_xlim(0, maxv * 1.22)

    _guardar(fig, ruta)


# ===========================================================================
# 2. EMPLEO EC — Serie y participación
# ===========================================================================

def fig_empleo_ec_serie(
    empleo_ec: pd.DataFrame,
    ruta: Path,
    anio_ini: int = 2019,
    anio_fin: int = 2025,
) -> None:
    """
    Serie de empleo EC (promedio anual de trimestres).
    `empleo_ec` debe tener columnas: anio, empleo_ec_prom.
    """
    d = empleo_ec[(empleo_ec["anio"] >= anio_ini) &
                  (empleo_ec["anio"] <= anio_fin)].copy().sort_values("anio")
    if d.empty:
        return

    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    bars = ax.bar(d["anio"], d["empleo_ec_prom"],
                  color=COLOR_EC, edgecolor="white", width=0.6)

    maxv = d["empleo_ec_prom"].max()
    for bar, val in zip(bars, d["empleo_ec_prom"]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                val + maxv * 0.015,
                f"{int(val)}", ha="center", fontsize=8.5,
                color=COLOR_LR, weight="bold")

    ax.set_ylabel("Puestos de trabajo")
    ax.set_ylim(0, maxv * 1.2)
    ax.set_xticks(d["anio"])
    ax.set_title("Empleo registrado en empresas de Economía del Conocimiento — La Rioja",
                 fontsize=10, weight="bold", color=COLOR_LR, pad=10)

    _guardar(fig, ruta)


# ---------------------------------------------------------------------------

def fig_empleo_ec_participacion(
    comp: pd.DataFrame,
    ruta: Path,
    anio_ini: int = 2019,
    anio_fin: int = 2025,
) -> None:
    """
    Doble eje: empleo EC (barras) + participación sobre empleo provincial (línea).
    `comp` debe tener: anio, empleo_ec_prom, empleo_total_prom, share_ec_pct.
    """
    d = comp[(comp["anio"] >= anio_ini) &
             (comp["anio"] <= anio_fin)].copy().sort_values("anio")
    if d.empty:
        return

    fig, ax1 = plt.subplots(figsize=(7.5, 3.6))

    bars = ax1.bar(d["anio"], d["empleo_ec_prom"],
                   color=COLOR_EC, edgecolor="white", width=0.6,
                   label="Empleo EC")
    maxv = d["empleo_ec_prom"].max()
    for bar, val in zip(bars, d["empleo_ec_prom"]):
        ax1.text(bar.get_x() + bar.get_width() / 2,
                 val + maxv * 0.02,
                 f"{int(val)}", ha="center", fontsize=8,
                 color=COLOR_LR, weight="bold")

    ax1.set_ylabel("Empleo EC (puestos)", color=COLOR_EC)
    ax1.tick_params(axis="y", labelcolor=COLOR_EC)
    ax1.set_ylim(0, maxv * 1.3)
    ax1.set_xticks(d["anio"])

    ax2 = ax1.twinx()
    ax2.plot(d["anio"], d["share_ec_pct"],
             marker="o", ms=6, color=COLOR_NOA, lw=2.4,
             label="Participación EC (%)")
    for _, r in d.iterrows():
        ax2.annotate(f"{r['share_ec_pct']:.2f}%",
                     (r["anio"], r["share_ec_pct"]),
                     textcoords="offset points", xytext=(0, 8),
                     ha="center", fontsize=8, color=COLOR_NOA, weight="bold")

    ax2.set_ylabel("Participación EC (%)", color=COLOR_NOA)
    ax2.tick_params(axis="y", labelcolor=COLOR_NOA)
    ax2.set_ylim(0, max(d["share_ec_pct"].max() * 1.5, 1))
    ax2.grid(False)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left",
               frameon=False, fontsize=8.5)

    ax1.set_title("Empleo EC y su participación en el empleo provincial",
                  fontsize=10, weight="bold", color=COLOR_LR, pad=10)

    _guardar(fig, ruta)


# ===========================================================================
# 3. ELASTICIDAD — Empresas vs Empleo
# ===========================================================================

def fig_elasticidad(
    elasticidad: pd.DataFrame,
    ruta: Path,
    anio_ini: int = 2022,
) -> None:
    """
    Serie doble: empresas EC y empleo EC (índice base año_ini = 100).
    `elasticidad` debe tener: anio, empresas_ec, empleo_ec_prom.
    """
    d = elasticidad[elasticidad["anio"] >= anio_ini].copy().sort_values("anio")
    if d.empty or len(d) < 2:
        return

    base_emp = d["empresas_ec"].iloc[0]
    base_emp_emp = d["empleo_ec_prom"].iloc[0]
    if base_emp == 0 or base_emp_emp == 0:
        return

    d["idx_emp"]     = d["empresas_ec"] / base_emp * 100
    d["idx_emp_emp"] = d["empleo_ec_prom"] / base_emp_emp * 100

    fig, ax = plt.subplots(figsize=(7.5, 3.6))

    ax.plot(d["anio"], d["idx_emp"],
            marker="o", ms=6, color=COLOR_EC, lw=2.6,
            label="Empresas EC")
    ax.plot(d["anio"], d["idx_emp_emp"],
            marker="s", ms=5, color=COLOR_NOA, lw=2,
            linestyle="--", label="Empleo EC")

    for _, r in d.iterrows():
        ax.annotate(f"{r['idx_emp']:.1f}",
                    (r["anio"], r["idx_emp"]),
                    textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8, color=COLOR_EC, weight="bold")
        ax.annotate(f"{r['idx_emp_emp']:.1f}",
                    (r["anio"], r["idx_emp_emp"]),
                    textcoords="offset points", xytext=(0, -14),
                    ha="center", fontsize=8, color=COLOR_NOA)

    ax.axhline(100, color="#888", ls=":", lw=1)
    ax.set_ylabel("Índice (2022 = 100)")
    ax.set_xticks(d["anio"])
    ax.set_ylim(85, 125)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("Elasticidad: empresas EC vs. empleo EC (2022 = 100)",
                 fontsize=10, weight="bold", color=COLOR_LR, pad=10)

    _guardar(fig, ruta)


# ===========================================================================
# 4. INTENSIDAD EMPRESARIAL
# ===========================================================================

def fig_intensidad_empresarial(
    intensidades: pd.DataFrame,
    ruta: Path,
    prov_destacada: str = "La Rioja",
) -> None:
    """
    Barras horizontales con intensidad EC (‰) por provincia.
    `intensidades` debe tener: provincia, intensidad_permil.
    """
    d = intensidades.dropna(subset=["intensidad_permil"]).sort_values(
        "intensidad_permil", ascending=True).copy()
    if d.empty:
        return

    colores = [COLOR_EC if p == prov_destacada else COLOR_GRIS
               for p in d["provincia"]]

    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    bars = ax.barh(d["provincia"], d["intensidad_permil"],
                   color=colores, edgecolor="white", height=0.7)

    maxv = d["intensidad_permil"].max()
    for bar, val in zip(bars, d["intensidad_permil"]):
        ax.text(val + maxv * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}‰", va="center", fontsize=8.5,
                color="#333", weight="bold")

    ax.set_xlabel("Empresas EC por cada 1.000 empresas totales (‰)")
    ax.set_title("Intensidad empresarial EC por provincia — 2024",
                 fontsize=10, weight="bold", color=COLOR_LR, pad=10)
    ax.set_xlim(0, maxv * 1.15)

    _guardar(fig, ruta)