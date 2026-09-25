"""
Genera todas las figuras del dashboard en PNG para el informe Quarto.
Ejecutar desde la raíz del proyecto:
    python scripts/generar_figuras_informe.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.patches import Patch, FancyBboxPatch

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

FIG = RAIZ / "informe" / "figuras"
FIG.mkdir(parents=True, exist_ok=True)

# ---------- Estilos globales ----------
COLOR_AZUL     = "#2c5f8a"
COLOR_TURQ     = "#2A9D8F"
COLOR_TURQ_L   = "#4ECDC4"
COLOR_ROJO     = "#c0392b"
COLOR_ROJO_L   = "#FF6B6B"
COLOR_AMBAR    = "#E8A33D"
COLOR_GRIS     = "#8EAFC4"
COLOR_GRIS_OSC = "#5A8BA8"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#cccccc",
    "axes.labelcolor": "#333333",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "axes.grid": True,
    "grid.alpha": 0.2,
    "grid.linestyle": "--",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
})

def _guardar(fig, nombre):
    ruta = FIG / nombre
    fig.savefig(ruta)
    plt.close(fig)
    print(f"💾 {nombre}")


# ============================================================
# 1. ESTRUCTURA EC POR ACTIVIDAD (donut)
# ============================================================
def fig_estructura_ec():
    labels = ["Informática n.c.p.", "Consultores informática",
              "Publicidad", "I+D Cs. médicas", "Reparación equipos", "Otros"]
    valores = [43.5, 33.6, 13.8, 3.0, 2.5, 3.6]
    colores = [COLOR_TURQ_L, COLOR_TURQ, "#6CB4D9", "#A8D8EA", "#1A6B8A", "#0D2B4B"]

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    wedges, texts, autotexts = ax.pie(
        valores, labels=None, autopct="%1.1f%%",
        colors=colores, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2),
        pctdistance=0.78,
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
        t.set_fontsize(9)

    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
              frameon=False, fontsize=9)
    ax.set_title("Estructura del sector EC 2025 — Distribución por actividad",
                 fontsize=11, fontweight="bold", pad=15)
    ax.text(0, 0, "77,1%\nTop 2 IT", ha="center", va="center",
            fontsize=11, fontweight="bold", color=COLOR_TURQ)
    _guardar(fig, "F30_estructura_ec.png")


# ============================================================
# 2. TRANSFORMACIÓN — Consultores vs Publicidad
# ============================================================
def fig_transformacion():
    categorias = ["Consultores\ninformática", "Publicidad"]
    v2022 = [6.1, 31.5]
    v2025 = [33.6, 13.8]

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    x = np.arange(len(categorias))
    w = 0.35
    b1 = ax.bar(x - w/2, v2022, w, label="2022", color="#1A6B8A")
    b2 = ax.bar(x + w/2, v2025, w, label="2025", color=COLOR_TURQ_L)

    for bars in [b1, b2]:
        for b in bars:
            ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.7,
                    f"{b.get_height()}%", ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(categorias)
    ax.set_ylabel("Participación en ingresos (%)")
    ax.set_title("Transformación del sector EC — 2022 vs. 2025",
                 fontsize=11, fontweight="bold")
    ax.legend(frameon=False, loc="upper right")
    ax.set_ylim(0, 40)
    _guardar(fig, "F31_transformacion.png")


# ============================================================
# 3. INGRESOS REALES EC
# ============================================================
def fig_ingresos_reales():
    anios = ["2022", "2023", "2024", "2025"]
    valores = [1694, 2342, 3051, 3945]

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    bars = ax.bar(anios, valores, color=COLOR_TURQ_L, width=0.6,
                  edgecolor=COLOR_TURQ, linewidth=1.5)
    for b, v in zip(bars, valores):
        ax.text(b.get_x()+b.get_width()/2, v+50, f"${v:,} M".replace(",", "."),
                ha="center", fontsize=9.5, fontweight="bold", color=COLOR_AZUL)

    ax.set_ylabel("$ millones (base dic-2022)")
    ax.set_title("Ingresos reales del sector EC — La Rioja 2022-2025",
                 fontsize=11, fontweight="bold")
    ax.set_ylim(0, 4500)
    _guardar(fig, "F32_ingresos_reales.png")


# ============================================================
# 4. SALARIOS POR CIIU EC
# ============================================================
def fig_salarios_ciiu():
    categorias = ["Informática n.c.p.\n(7290)", "Consultores inform.\n(7220)",
                  "Arquitectura/ing.\n(7421) [proxy]", "Servicios prof.\n(7499) [proxy]"]
    valores = [3108543, 1726147, 1016111, 978907]
    colores = [COLOR_TURQ_L, COLOR_TURQ_L, COLOR_AMBAR, COLOR_AMBAR]
    promedio_prov = 1306422

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    y = np.arange(len(categorias))
    bars = ax.barh(y, valores, color=colores, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(categorias, fontsize=9)
    ax.invert_yaxis()

    for b, v in zip(bars, valores):
        prima = (v / promedio_prov - 1) * 100
        signo = "+" if prima >= 0 else ""
        ax.text(v + 80000, b.get_y()+b.get_height()/2,
                f"${v:,.0f}  ({signo}{prima:.0f}%)".replace(",", "."),
                va="center", fontsize=9, fontweight="bold")

    ax.axvline(promedio_prov, color=COLOR_ROJO, linestyle="--", linewidth=2,
               label=f"Prom. provincial ${promedio_prov:,}".replace(",", "."))
    ax.set_xlabel("Salario promedio mensual 2025 ($)")
    ax.set_title("Remuneración promedio por CIIU EC vs. promedio provincial (2025)",
                 fontsize=11, fontweight="bold")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_xlim(0, 3800000)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(
        lambda x, p: f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}k"))
    _guardar(fig, "F33_salarios_ciiu.png")


# ============================================================
# 5. PRIMA SALARIAL NÚCLEO vs AFIP-DGIP
# ============================================================
def fig_prima_salarial():
    anios = ["2022", "2023", "2024", "2025"]
    nucleo = [53.67, 20.04, 45.75, 29.00]
    completo = [-2.41, -6.59, 21.38, 8.36]

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    x = np.arange(len(anios))
    w = 0.38
    b1 = ax.bar(x - w/2, nucleo, w, label="Núcleo software (7220, 7250, 7290)",
                color=COLOR_TURQ_L)
    b2 = ax.bar(x + w/2, completo, w, label="EC completo (8 CIIU)", color="#6CB4D9")

    for bars in [b1, b2]:
        for b in bars:
            h = b.get_height()
            y = h + 1.5 if h >= 0 else h - 3.5
            ax.text(b.get_x()+b.get_width()/2, y, f"{h:+.1f}%",
                    ha="center", fontsize=9, fontweight="bold")

    ax.axhline(0, color="#333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(anios)
    ax.set_ylabel("Prima vs. promedio provincial (%)")
    ax.set_title("Prima salarial EC — Núcleo software vs. AFIP-DGIP completo",
                 fontsize=11, fontweight="bold")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_ylim(-15, 65)
    _guardar(fig, "F34_prima_salarial.png")


# ============================================================
# 6. EMPRESAS EC POR BLOQUE (stacked)
# ============================================================
def fig_empresas_bloques():
    anios = ["2019", "2020", "2021", "2022", "2024", "2025"]
    software = [6, 11, 17, 25, 28, 25]
    ing = [29, 22, 25, 26, 31, 28]
    serv = [29, 32, 28, 40, 38, 31]
    publicidad = [6, 0, 4, 4, 5, 0]

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.bar(anios, software, label="Software y SI", color=COLOR_TURQ_L)
    ax.bar(anios, ing, bottom=software, label="Ingeniería y geología (proxy)",
           color=COLOR_TURQ)
    ax.bar(anios, serv, bottom=np.array(software)+np.array(ing),
           label="Servicios profesionales (proxy)", color="#6CB4D9")
    ax.bar(anios, publicidad,
           bottom=np.array(software)+np.array(ing)+np.array(serv),
           label="Publicidad", color="#1A6B8A")

    totales = np.array(software)+np.array(ing)+np.array(serv)+np.array(publicidad)
    for i, (a, t) in enumerate(zip(anios, totales)):
        ax.text(i, t+2, str(t), ha="center", fontsize=10, fontweight="bold")

    ax.set_ylabel("Cantidad de empresas")
    ax.set_title("Empresas EC por bloque — Definición AFIP-DGIP (2019-2025)",
                 fontsize=11, fontweight="bold")
    ax.legend(frameon=False, loc="upper left", fontsize=8.5)
    ax.set_ylim(0, 130)
    ax.text(0.99, 0.01, "2023: sin datos en la fuente",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="#888", style="italic")
    _guardar(fig, "F35_empresas_bloques.png")


# ============================================================
# 7. EMPLEO EC Y PARTICIPACIÓN
# ============================================================
def fig_empleo_share():
    anios = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
    empleo = [356, 298, 336, 445, 513, 506, 521]
    share = [1.32, 1.17, 1.28, 1.48, 1.57, 1.81, 1.93]

    fig, ax1 = plt.subplots(figsize=(6.5, 4.0))
    x = np.arange(len(anios))
    bars = ax1.bar(x, empleo, color=COLOR_TURQ_L, alpha=0.8, width=0.6,
                   label="Empleo EC (puestos)")
    for b, v in zip(bars, empleo):
        ax1.text(b.get_x()+b.get_width()/2, v+8, str(v),
                 ha="center", fontsize=9, fontweight="bold", color=COLOR_AZUL)

    ax1.set_ylabel("Empleo EC (puestos)", color=COLOR_AZUL)
    ax1.tick_params(axis="y", labelcolor=COLOR_AZUL)
    ax1.set_xticks(x)
    ax1.set_xticklabels(anios)
    ax1.set_ylim(0, 650)

    ax2 = ax1.twinx()
    ax2.plot(x, share, color=COLOR_ROJO_L, marker="o", linewidth=2.5,
             markersize=7, label="Participación EC (%)")
    for i, v in enumerate(share):
        ax2.text(i, v+0.06, f"{v:.2f}%", ha="center", fontsize=8.5,
                 fontweight="bold", color=COLOR_ROJO_L)
    ax2.set_ylabel("Participación (%)", color=COLOR_ROJO_L)
    ax2.tick_params(axis="y", labelcolor=COLOR_ROJO_L)
    ax2.set_ylim(0, 2.5)
    ax2.grid(False)

    ax1.set_title("Empleo EC y participación en el empleo provincial (2019-2025)",
                  fontsize=11, fontweight="bold")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1+h2, l1+l2, frameon=False, loc="upper left", fontsize=9)
    _guardar(fig, "F36_empleo_share.png")


# ============================================================
# 8. INTENSIDAD EMPRESARIAL POR PROVINCIA
# ============================================================
def fig_intensidad():
    provincias = ["Santiago del Estero", "Santa Fe", "La Rioja", "Jujuy",
                  "Córdoba", "Tucumán", "Salta", "Catamarca", "CABA"]
    valores = [25.63, 27.29, 31.34, 33.12, 34.55, 35.74, 38.99, 43.18, 67.95]
    colores = [COLOR_GRIS if p != "La Rioja" else COLOR_TURQ_L for p in provincias]

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    y = np.arange(len(provincias))
    bars = ax.barh(y, valores, color=colores, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(provincias, fontsize=9)
    ax.invert_yaxis()

    for b, v in zip(bars, valores):
        ax.text(v+0.5, b.get_y()+b.get_height()/2, f"{v:.1f}‰",
                va="center", fontsize=9, fontweight="bold")

    ax.set_xlabel("Empresas EC por cada 1.000 empresas totales (‰)")
    ax.set_title("Intensidad empresarial EC por provincia (2024)",
                 fontsize=11, fontweight="bold")
    ax.set_xlim(0, 75)
    _guardar(fig, "F37_intensidad.png")


# ============================================================
# 9. TENDENCIA EMPLEO FORMAL (área, desestacionalizada)
# ============================================================
def fig_empleo_tendencia():
    labels = ["Ene-22","Feb-22","Mar-22","Abr-22","May-22","Jun-22","Jul-22",
              "Ago-22","Sep-22","Oct-22","Nov-22","Dic-22","Ene-23","Feb-23",
              "Mar-23","Abr-23","May-23","Jun-23","Jul-23","Ago-23","Sep-23",
              "Oct-23","Nov-23","Dic-23","Ene-24","Feb-24","Mar-24","Abr-24",
              "May-24","Jun-24","Jul-24","Ago-24","Sep-24","Oct-24","Nov-24",
              "Dic-24","Ene-25","Feb-25","Mar-25","Abr-25","May-25","Jun-25",
              "Jul-25","Ago-25","Sep-25","Oct-25","Nov-25","Dic-25","Ene-26",
              "Feb-26","Mar-26","Abr-26","May-26","Jun-26"]
    tendencia = [29012,29674,30483,30654,29974,30652,30953,31177,31269,31767,
                 31811,31998,32556,32547,32813,32835,33134,33875,34015,33606,
                 33372,33057,32823,32453,32733,30871,29254,29640,29501,29245,
                 29084,29441,29927,29631,29788,29692,29402,29280,28509,29554,
                 29627,29246,29178,29014,28821,28612,28439,28458,28892,30134,
                 29238,29300,29188,28890]

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    x = np.arange(len(labels))
    ax.fill_between(x, tendencia, 27000, color=COLOR_TURQ_L, alpha=0.3)
    ax.plot(x, tendencia, color=COLOR_TURQ, linewidth=2.5)

    ax.set_ylabel("Puestos (tendencia desest.)")
    ax.set_xticks(x[::6])
    ax.set_xticklabels([labels[i] for i in range(0, len(labels), 6)],
                       rotation=45, ha="right", fontsize=8)
    ax.set_title("Empleo formal privado — Tendencia desestacionalizada (2022-2026)",
                 fontsize=11, fontweight="bold")
    ax.set_ylim(27000, 35000)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(
        lambda v, p: f"{v/1000:.0f}k"))

    # Anotación pico
    idx_pico = tendencia.index(max(tendencia))
    ax.annotate(f"Pico: {max(tendencia):,}".replace(",", "."),
                xy=(idx_pico, max(tendencia)),
                xytext=(idx_pico+2, max(tendencia)+700),
                fontsize=9, fontweight="bold", color=COLOR_AZUL,
                arrowprops=dict(arrowstyle="->", color=COLOR_AZUL, lw=1))
    # Último valor
    ax.annotate(f"{tendencia[-1]:,}".replace(",", "."),
                xy=(len(labels)-1, tendencia[-1]),
                xytext=(len(labels)-8, tendencia[-1]-800),
                fontsize=9, fontweight="bold", color=COLOR_ROJO_L,
                arrowprops=dict(arrowstyle="->", color=COLOR_ROJO_L, lw=1))
    _guardar(fig, "F38_empleo_tendencia.png")


# ============================================================
# 10. VARIACIÓN i.a. (barras verde/rojo)
# ============================================================
def fig_empleo_ia():
    labels = ["Ene-22","Feb-22","Mar-22","Abr-22","May-22","Jun-22","Jul-22",
              "Ago-22","Sep-22","Oct-22","Nov-22","Dic-22","Ene-23","Feb-23",
              "Mar-23","Abr-23","May-23","Jun-23","Jul-23","Ago-23","Sep-23",
              "Oct-23","Nov-23","Dic-23","Ene-24","Feb-24","Mar-24","Abr-24",
              "May-24","Jun-24","Jul-24","Ago-24","Sep-24","Oct-24","Nov-24",
              "Dic-24","Ene-25","Feb-25","Mar-25","Abr-25","May-25","Jun-25",
              "Jul-25","Ago-25","Sep-25","Oct-25","Nov-25","Dic-25","Ene-26",
              "Feb-26","Mar-26","Abr-26","May-26","Jun-26"]
    ia = [4.83,8.64,11.51,10.0,8.04,7.7,10.56,12.6,11.89,12.48,11.73,11.71,
          12.88,9.5,7.67,6.65,10.66,10.87,9.63,8.0,6.24,4.63,3.16,1.0,0.66,
          -1.7,-10.98,-9.4,-10.64,-14.55,-14.08,-12.45,-10.4,-10.23,-9.34,
          -8.2,-10.02,-8.61,-3.24,0.03,0.51,0.24,0.35,-1.84,-3.25,-3.48,-5.02,
          -4.12,-1.85,2.95,3.0,-0.76,-1.72,-0.84]

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    x = np.arange(len(labels))
    colores = [COLOR_TURQ_L if v >= 0 else COLOR_ROJO_L for v in ia]
    ax.bar(x, ia, color=colores, width=0.8)
    ax.axhline(0, color="#333", linewidth=0.8)
    ax.set_ylabel("Variación i.a. (%)")
    ax.set_xticks(x[::3])
    ax.set_xticklabels([labels[i] for i in range(0, len(labels), 3)],
                       rotation=45, ha="right", fontsize=7.5)
    ax.set_title("Variación interanual del empleo formal (2022-2026)",
                 fontsize=11, fontweight="bold")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))

    leyenda = [Patch(facecolor=COLOR_TURQ_L, label="Crecimiento"),
               Patch(facecolor=COLOR_ROJO_L, label="Caída")]
    ax.legend(handles=leyenda, frameon=False, loc="upper right",
              fontsize=8.5, ncol=2)
    _guardar(fig, "F39_empleo_ia.png")


# ============================================================
# 11. EMPLEO POR SECTOR (barras horizontales + variación i.a.)
# ============================================================
def fig_empleo_sector():
    sectores = ["Industria", "Servicios", "Comercio", "Agricultura",
                "Construcción", "Electricidad", "Minería"]
    valores = [8550, 8730, 6720, 4950, 1150, 850, 130]
    variaciones = [-5.6, -2.8, 0.9, -5.4, -14.8, 3.7, 8.3]

    def color(v):
        if v >= 0: return COLOR_TURQ_L
        if v >= -10: return COLOR_AMBAR
        return COLOR_ROJO_L
    colores = [color(v) for v in variaciones]

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    y = np.arange(len(sectores))
    bars = ax.barh(y, valores, color=colores, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(sectores, fontsize=10)
    ax.invert_yaxis()

    for b, v, pct in zip(bars, valores, variaciones):
        signo = "+" if pct >= 0 else ""
        flecha = "▲" if pct >= 0 else "▼"
        ax.text(v + 100, b.get_y()+b.get_height()/2,
                f"{v:,}  {flecha} {signo}{pct:.1f}%".replace(",", "."),
                va="center", fontsize=9, fontweight="bold")

    ax.set_xlabel("Puestos de trabajo (promedio 2025)")
    ax.set_title("Empleo por sector — La Rioja 2025 y variación i.a.",
                 fontsize=11, fontweight="bold")
    ax.set_xlim(0, 11000)
    ax.text(0.99, 0.01,
            "Verde: creció  ·  Amarillo: cayó moderado  ·  Rojo: cayó fuerte",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="#666", style="italic")
    _guardar(fig, "F40_empleo_sector.png")


# ============================================================
# EJECUTAR TODAS
# ============================================================
if __name__ == "__main__":
    print("🎨 Generando figuras para el informe...\n")
    fig_estructura_ec()
    fig_transformacion()
    fig_ingresos_reales()
    fig_salarios_ciiu()
    fig_prima_salarial()
    fig_empresas_bloques()
    fig_empleo_share()
    fig_intensidad()
    fig_empleo_tendencia()
    fig_empleo_ia()
    fig_empleo_sector()
    print(f"\n✅ Listo. {len(list(FIG.glob('F3*.png')))} figuras nuevas generadas.")
    print(f"   Carpeta: {FIG}")