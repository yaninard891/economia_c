"""
Genera figura de ingresos brutos nominales del sector EC en La Rioja (2022-2025).
"""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# Valores en millones de pesos corrientes
datos = {
    2022: 2_013,
    2023: 6_367,
    2024: 19_959,
    2025: 40_955,
}

anios = list(datos.keys())
valores = list(datos.values())

fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)

# Última barra destacada
colores = ["#1e3a5f", "#1e3a5f", "#1e3a5f", "#2bb3a3"]
barras = ax.bar([str(a) for a in anios], valores, color=colores, width=0.6)

# Etiquetas encima
for barra, valor in zip(barras, valores):
    ax.text(
        barra.get_x() + barra.get_width() / 2,
        barra.get_height() + 800,
        f"${valor:,} M".replace(",", "."),
        ha="center", va="bottom",
        fontsize=12, fontweight="bold", color="#1a1a1a",
    )

# Eje Y
ax.set_ylabel("Ingresos brutos (millones de $ corrientes)", fontsize=10)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", ".")))

# Título
ax.set_title(
    "Ingresos brutos del sector EC — La Rioja (2022–2025)",
    fontsize=13, fontweight="bold", pad=15,
)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(axis="x", labelsize=12)
ax.tick_params(axis="y", labelsize=10)
ax.grid(axis="y", alpha=0.25, linestyle="--")
ax.set_axisbelow(True)

plt.tight_layout()

salida = Path("informe/figuras/F42_ingresos_nominales.png")
salida.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(salida, bbox_inches="tight")
print(f"✅ Figura guardada: {salida}")
plt.close()