"""
notebooks/recaudacion_ec_analisis.py
=====================================

Análisis fiscal de la Recaudación EC en La Rioja (2022-2026).

Genera:
  - Figuras para el informe (F20 a F23)
  - Serie procesada en data/processed/
  - Resumen por consola

Ejecutar:
  python notebooks/recaudacion_ec_analisis.py
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- Setup de paths ---
raiz = Path.cwd()
if raiz.name == "notebooks":
    raiz = raiz.parent
if str(raiz) not in sys.path:
    sys.path.insert(0, str(raiz))

from src.recaudacion_ec import (
    serie_mensual,
    serie_anual,
    serie_anual_multi,
    serie_recaudacion_ec,
    share_ec_iibb_serie,
    exportar_excel,
    RECAUDACION_EC,
)

# --- Paleta del proyecto ---
AZUL = "#0B1D35"
TURQUESA = "#4ECDC4"
AZUL_MEDIO = "#2A9D8F"
ROJO = "#FF6B6B"
GRIS = "#8EAFC4"
AZUL_CLARO = "#6CB4D9"

FIG = raiz / "informe" / "figuras"
FIG.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# 1. Carga de datos
# ===========================================================================

print("=" * 70)
print("ANÁLISIS FISCAL — RECAUDACIÓN EC LA RIOJA (2022-2026)")
print("=" * 70)

iibb_anual = serie_anual("La Rioja", "II.BB")
total_anual = serie_anual("La Rioja", "TOTAL")
share = share_ec_iibb_serie()
rec_ec = serie_recaudacion_ec()

print("\n--- II.BB anual (millones $ corrientes) ---")
print(iibb_anual.to_string(index=False))

print("\n--- Recaudación EC y share ---")
print(share.to_string(index=False))


# ===========================================================================
# 2. Índice base 2022 = 100 — Recaudación EC vs. II.BB total
# ===========================================================================

share_idx = share.copy()
share_idx["ec_idx"] = (share_idx["recaudacion_ec_mm"] /
                       share_idx["recaudacion_ec_mm"].iloc[0] * 100).round(1)
share_idx["iibb_idx"] = (share_idx["iibb_mm"] /
                         share_idx["iibb_mm"].iloc[0] * 100).round(1)

print("\n--- Índice base 2022 = 100 ---")
print(share_idx[["anio", "recaudacion_ec_mm", "ec_idx",
                 "iibb_mm", "iibb_idx"]].to_string(index=False))

# Brecha acumulada
brecha = share_idx["ec_idx"].iloc[-1] - share_idx["iibb_idx"].iloc[-1]
print(f"\nBrecha 2022→2025: EC creció {brecha:.0f} pp más que II.BB total")


# ===========================================================================
# 3. Figura F20 — Doble eje: II.BB total vs. Recaudación EC
# ===========================================================================

fig, ax1 = plt.subplots(figsize=(9, 4.2))

x = share["anio"].astype(str)
bars = ax1.bar(x, share["iibb_mm"], color=AZUL_CLARO, alpha=0.35,
               label="II.BB total (eje izq.)", width=0.55)
ax1.set_ylabel("II.BB total (millones $)", color=GRIS, fontsize=10)
ax1.tick_params(axis="y", labelcolor=GRIS)
ax1.set_xlabel("Año", color=GRIS, fontsize=10)
for spine in ax1.spines.values():
    spine.set_color(GRIS)
    spine.set_alpha(0.3)

ax2 = ax1.twinx()
ax2.plot(x, share["recaudacion_ec_mm"], color=TURQUESA,
         marker="o", linewidth=3, markersize=10,
         label="Recaudación EC (eje der.)")
ax2.set_ylabel("Recaudación EC (millones $)", color=TURQUESA, fontsize=10)
ax2.tick_params(axis="y", labelcolor=TURQUESA)
ax2.set_yscale("log")

# Anotaciones
for xi, yi in zip(x, share["recaudacion_ec_mm"]):
    ax2.annotate(f"${yi:,.0f} M",
                 xy=(xi, yi), xytext=(0, 10),
                 textcoords="offset points",
                 ha="center", fontsize=9, color=TURQUESA, fontweight="bold")

ax1.set_title("Recaudación EC vs. Ingresos Brutos totales — La Rioja 2022-2025",
              fontsize=12, color=AZUL, fontweight="bold", pad=15)
ax1.grid(axis="y", linestyle="--", alpha=0.2)

# Leyenda combinada
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2,
           loc="upper left", framealpha=0.9, fontsize=9)

plt.tight_layout()
plt.savefig(FIG / "F20_recaudacion_ec_vs_iibb.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.close()
print(f"\n✓ F20 guardada: {FIG / 'F20_recaudacion_ec_vs_iibb.png'}")


# ===========================================================================
# 4. Figura F21 — Share EC sobre II.BB (2022-2025)
# ===========================================================================

fig, ax = plt.subplots(figsize=(8, 4))

x = share["anio"].astype(str)
bars = ax.bar(x, share["share_pct"], color=TURQUESA, width=0.55)

for bar, val in zip(bars, share["share_pct"]):
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.03,
            f"{val:.2f}%",
            ha="center", va="bottom",
            fontsize=11, fontweight="bold", color=AZUL)

ax.set_ylabel("% sobre II.BB total", color=GRIS, fontsize=10)
ax.set_xlabel("Año", color=GRIS, fontsize=10)
ax.set_ylim(0, max(share["share_pct"]) * 1.3)
ax.set_title("Peso de la Recaudación EC sobre Ingresos Brutos — La Rioja 2022-2025",
             fontsize=12, color=AZUL, fontweight="bold", pad=15)
ax.grid(axis="y", linestyle="--", alpha=0.2)
for spine in ax.spines.values():
    spine.set_color(GRIS)
    spine.set_alpha(0.3)

# Anotación de crecimiento
ax.annotate(f"×{share['share_pct'].iloc[-1] / share['share_pct'].iloc[0]:.1f} en 4 años",
            xy=(3, share["share_pct"].iloc[-1]),
            xytext=(1.5, share["share_pct"].iloc[-1] * 1.15),
            fontsize=11, color=AZUL_MEDIO, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=AZUL_MEDIO, lw=1.5))

plt.tight_layout()
plt.savefig(FIG / "F21_share_ec_iibb.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.close()
print(f"✓ F21 guardada: {FIG / 'F21_share_ec_iibb.png'}")


# ===========================================================================
# 5. Figura F22 — Índice base 2022=100: EC vs. II.BB total
# ===========================================================================

fig, ax = plt.subplots(figsize=(8, 4.2))

x = share_idx["anio"].astype(str)
ax.plot(x, share_idx["ec_idx"], color=TURQUESA, marker="o",
        linewidth=3, markersize=10, label="Recaudación EC")
ax.plot(x, share_idx["iibb_idx"], color=AZUL_CLARO, marker="s",
        linewidth=2.5, markersize=8, label="II.BB total (resto de la economía)")
ax.axhline(100, color=GRIS, linestyle="--", linewidth=1, alpha=0.5)

for xi, yi in zip(x, share_idx["ec_idx"]):
    ax.annotate(f"{yi:.0f}", xy=(xi, yi), xytext=(0, 10),
                textcoords="offset points", ha="center",
                fontsize=10, color=TURQUESA, fontweight="bold")
for xi, yi in zip(x, share_idx["iibb_idx"]):
    ax.annotate(f"{yi:.0f}", xy=(xi, yi), xytext=(0, -15),
                textcoords="offset points", ha="center",
                fontsize=10, color=AZUL_CLARO, fontweight="bold")

ax.set_ylabel("Índice (2022 = 100)", color=GRIS, fontsize=10)
ax.set_xlabel("Año", color=GRIS, fontsize=10)
ax.set_title("Crecimiento comparado: Recaudación EC vs. II.BB — La Rioja 2022-2025",
             fontsize=12, color=AZUL, fontweight="bold", pad=15)
ax.grid(axis="y", linestyle="--", alpha=0.2)
ax.legend(loc="upper left", framealpha=0.9, fontsize=10)
for spine in ax.spines.values():
    spine.set_color(GRIS)
    spine.set_alpha(0.3)

plt.tight_layout()
plt.savefig(FIG / "F22_indice_ec_vs_iibb.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.close()
print(f"✓ F22 guardada: {FIG / 'F22_indice_ec_vs_iibb.png'}")


# ===========================================================================
# 6. Figura F23 — Contribuyentes por régimen (stacked)
# ===========================================================================

fig, ax = plt.subplots(figsize=(8, 4))

x = np.arange(len(rec_ec))
ancho = 0.6

ax.bar(x, rec_ec["contrib_locales"], ancho,
       label="Locales", color=AZUL_CLARO, alpha=0.85)
ax.bar(x, rec_ec["contrib_multilateral"], ancho,
       bottom=rec_ec["contrib_locales"],
       label="Convenio Multilateral", color=TURQUESA)

for xi, (loc, multi) in enumerate(zip(rec_ec["contrib_locales"],
                                       rec_ec["contrib_multilateral"])):
    ax.text(xi, loc / 2, f"{loc:,}", ha="center", va="center",
            fontsize=10, color="white", fontweight="bold")
    ax.text(xi, loc + multi / 2, f"{multi:,}", ha="center", va="center",
            fontsize=10, color="white", fontweight="bold")
    ax.text(xi, loc + multi + 60, f"Total: {loc + multi:,}",
            ha="center", va="bottom", fontsize=9, color=AZUL, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(rec_ec["anio"].astype(str))
ax.set_ylabel("Contribuyentes EC", color=GRIS, fontsize=10)
ax.set_xlabel("Año", color=GRIS, fontsize=10)
ax.set_ylim(0, rec_ec["contrib_total"].max() * 1.15)
ax.set_title("Contribuyentes EC por régimen de tributación — La Rioja 2022-2025",
             fontsize=12, color=AZUL, fontweight="bold", pad=15)
ax.legend(loc="upper left", framealpha=0.9, fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.2)
for spine in ax.spines.values():
    spine.set_color(GRIS)
    spine.set_alpha(0.3)

plt.tight_layout()
plt.savefig(FIG / "F23_contribuyentes_ec.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.close()
print(f"✓ F23 guardada: {FIG / 'F23_contribuyentes_ec.png'}")


# ===========================================================================
# 7. Export a Excel procesado
# ===========================================================================

try:
    ruta_xlsx = exportar_excel()
    print(f"\n✓ Excel procesado: {ruta_xlsx}")
except Exception as e:
    print(f"\n⚠ Error al exportar Excel: {e}")


# ===========================================================================
# 8. Resumen por consola
# ===========================================================================

print("\n" + "=" * 70)
print("HALLAZGOS CLAVE")
print("=" * 70)

ec_crec = (share["recaudacion_ec_mm"].iloc[-1] /
           share["recaudacion_ec_mm"].iloc[0])
iibb_crec = share["iibb_mm"].iloc[-1] / share["iibb_mm"].iloc[0]
share_crec = (share["share_pct"].iloc[-1] / share["share_pct"].iloc[0])

print(f"""
1. Recaudación EC: ×{ec_crec:.1f} nominal entre 2022 y 2025
   (${share['recaudacion_ec_mm'].iloc[0]:.2f} M → ${share['recaudacion_ec_mm'].iloc[-1]:,.2f} M)

2. II.BB total: ×{iibb_crec:.1f} nominal en el mismo período
   (${share['iibb_mm'].iloc[0]:,.2f} M → ${share['iibb_mm'].iloc[-1]:,.2f} M)

3. El EC crece {(ec_crec / iibb_crec):.1f}× más rápido que el II.BB total

4. Share del EC sobre II.BB: {share['share_pct'].iloc[0]:.2f}% → {share['share_pct'].iloc[-1]:.2f}%
   (×{share_crec:.1f} en 4 años)

5. Contribuyentes Locales: {rec_ec['contrib_locales'].iloc[0]:,} → {rec_ec['contrib_locales'].iloc[-1]:,}
   ({(rec_ec['contrib_locales'].iloc[-1] / rec_ec['contrib_locales'].iloc[0] - 1) * 100:+.1f}%)

6. Contribuyentes Convenio Multilateral: {rec_ec['contrib_multilateral'].iloc[0]:,} → {rec_ec['contrib_multilateral'].iloc[-1]:,}
   ({(rec_ec['contrib_multilateral'].iloc[-1] / rec_ec['contrib_multilateral'].iloc[0] - 1) * 100:+.1f}%)
""")

print("=" * 70)
print("✓ Análisis completo. Figuras F20-F23 en informe/figuras/")
print("=" * 70)