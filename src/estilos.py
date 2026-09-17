# src/estilos.py
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from src.config import OUT_GRAF

def set_estilo():
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update({
        "figure.figsize": (11, 6),
        "axes.titlesize": 14,
        "axes.labelsize": 11,
        "figure.dpi": 120,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    })

def guardar_grafico(fig, nombre: str, subcarpeta: str | None = None):
    base = OUT_GRAF if subcarpeta is None else OUT_GRAF / subcarpeta
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{nombre}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"✔ guardado: {path.name}")
    return path