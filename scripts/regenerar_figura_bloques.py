"""
Regenera F35_empresas_bloques.png con los números visibles en cada segmento.
"""
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.empresas_ec import cargar_ec, por_bloque

# --- Obtener datos ---
df = cargar_ec()
bloques_df = por_bloque(df)

# --- Filtrar años y bloques relevantes ---
ANIOS = [2022, 2024, 2025]
bloques_df = bloques_df[bloques_df["anio"].isin(ANIOS)]

# Excluir I+D (sin datos) y ordenar bloques
orden_bloques = [
    "Servicios profesionales (proxy)",
    "Ingeniería y geología (proxy)",
    "Software y SI",
    "Publicidad",
]
bloques_df = bloques_df[bloques_df["bloque"].isin(orden_bloques)]

# --- Pivotear ---
pivot = bloques_df.pivot(index="anio", columns="bloque", values="empresas").fillna(0)
pivot = pivot.reindex(columns=orden_bloques, fill_value=0)

# --- Colores (consistentes con dashboard) ---
colores = {
    "Servicios profesionales (proxy)": "#5b9bd5",   # celeste
    "Ingeniería y geología (proxy)":   "#2bb3a3",   # turquesa
    "Software y SI":                    "#1e6f5c",   # verde oscuro
    "Publicidad":                       "#1e3a5f",   # azul oscuro
}

# --- Figura más grande ---
fig, ax = plt.subplots(figsize=(11, 6.5), dpi=150)

anios_str = [str(a) for a in pivot.index]
x = np.arange(len(anios_str))
ancho = 0.6

# --- Dibujar barras apiladas ---
bottom = np.zeros(len(anios_str))

for bloque in orden_bloques:
    valores = pivot[bloque].values
    barras = ax.bar(x, valores, ancho, bottom=bottom,
                    label=bloque, color=colores[bloque],
                    edgecolor="white", linewidth=1.2)
    
    # --- Números dentro de cada segmento ---
    for barra, valor in zip(barras, valores):
        if valor > 0:
            # Centro del segmento
            y_centro = barra.get_y() + barra.get_height() / 2
            # Texto blanco si el segmento es alto, negro si es chico
            color_texto = "white" if valor >= 6 else "#1a1a1a"
            ax.text(
                barra.get_x() + barra.get_width() / 2,
                y_centro,
                f"{int(valor)}",
                ha="center", va="center",
                fontsize=12, fontweight="bold", color=color_texto,
            )
    bottom += valores

# --- Totales arriba de cada barra ---
for i, total in enumerate(bottom):
    ax.text(
        i, total + 2,
        f"{int(total)}",
        ha="center", va="bottom",
        fontsize=14, fontweight="bold", color="#1a1a1a",
    )

# --- Ejes y estética ---
ax.set_xticks(x)
ax.set_xticklabels(anios_str, fontsize=13)
ax.set_ylabel("N° de empresas EC", fontsize=11)
ax.set_title(
    "Empresas EC por bloque — Definición ARCA-DGIP (2022, 2024, 2025)",
    fontsize=13, fontweight="bold", pad=15,
)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.2, linestyle="--")
ax.set_axisbelow(True)
ax.set_ylim(0, max(bottom) * 1.15)

# --- Leyenda abajo, horizontal ---
ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.08),
    ncol=2,
    frameon=False,
    fontsize=11,
)

plt.tight_layout()

# --- Guardar ---
salida = Path(__file__).resolve().parent.parent / "informe" / "figuras" / "F35_empresas_bloques.png"
plt.savefig(salida, bbox_inches="tight", dpi=150)
print(f"✅ Figura guardada: {salida}")
plt.close()