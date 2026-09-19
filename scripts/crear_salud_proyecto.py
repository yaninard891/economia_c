"""
Genera notebooks/01_salud_proyecto.ipynb — chequeo integral del proyecto.
Ejecutar UNA vez:  python scripts/crear_salud_proyecto.py
"""
from pathlib import Path
import nbformat as nbf

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "notebooks" / "01_salud_proyecto.ipynb"
OUT.parent.mkdir(parents=True, exist_ok=True)

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.14.5"},
}

celdas = []

def md(texto):
    celdas.append(nbf.v4.new_markdown_cell(texto.strip()))

def code(fuente):
    celdas.append(nbf.v4.new_code_cell(fuente.strip()))

# ============================================================
# 0. Portada
# ============================================================
md("""
# 01 · Salud del proyecto — Economía de La Rioja

Chequeo integral end-to-end del pipeline. Ejecutar con **Kernel → Restart & Run All**.

**Qué verifica:**
1. Setup de rutas e imports
2. Presencia de archivos fuente en `data/raw/`
3. Presencia de archivos procesados en `data/processed/`
4. Empresas EC (AFIP-DGIP) — serie 2019-2025
5. Empleo EC — serie 2019-2025
6. Benchmark 9 provincias (intensidad empresarial)
7. Prima salarial EC — 3 definiciones
8. DGIP — recaudación y contribuyentes
9. Empleo comparado LR / NOA / Nación
10. Resumen final con semáforos

**Definición vigente:** AFIP-DGIP (8 CIIU) — ver `src/empresas_ec.py`
""")

# ============================================================
# 1. Setup
# ============================================================
md("## 1 · Setup")

code("""
import os
import sys
import importlib
from pathlib import Path

if Path.cwd().name == "notebooks":
    os.chdir(Path.cwd().parent)
sys.path.insert(0, str(Path.cwd()))

print("CWD:", Path.cwd())
print("Python:", sys.version.split()[0])
print("src OK:", (Path.cwd() / "src").exists())

for mod in ["empresas_ec", "prima_salarial", "regional", "dgip", "empleo", "sectorial"]:
    try:
        importlib.import_module(f"src.{mod}")
    except Exception as e:
        print(f"  [!] src.{mod}: {e}")
""")

# ============================================================
# 2. Archivos en data/raw
# ============================================================
md("## 2 · Archivos fuente (data/raw)")

code("""
RAW = Path("data/raw")

CLAVE_RAW = [
    "provinciales_serie_empresas3_2.xlsx",
    "provinciales_serie_empleo_trimestral_4dig_7.xlsx",
    "provinciales_serie_remuneraciones_mensual_4dig_7.xlsx",
    "SerieWeb_EMPLEO_PRIVADO_FORMAL_provincias.xlsx",
    "SerieWeb_SALARIO_PRIVADO_FORMAL_provincias.xlsx",
    "empresas_ec_rioja.csv",
    "total_provincial_rioja.csv",
]

print(f"{'Archivo':<60} {'Estado':>10} {'Tamaño':>12}")
print("-" * 84)
faltan_raw = []
for nombre in CLAVE_RAW:
    p = RAW / nombre
    if p.exists():
        kb = p.stat().st_size / 1024
        print(f"{nombre:<60} {'OK':>10} {kb:>10,.0f} KB")
    else:
        print(f"{nombre:<60} {'FALTA':>10} {'-':>12}")
        faltan_raw.append(nombre)

print(f"\\nTotal archivos en data/raw: {len(list(RAW.iterdir()))}")
if faltan_raw:
    print(f"Faltan: {faltan_raw}")
""")

# ============================================================
# 3. Archivos procesados
# ============================================================
md("## 3 · Archivos procesados (data/processed)")

code("""
PROCESSED = Path("data/processed")

CLAVE_PROC = [
    "empleo_ec_rioja.xlsx",
    "empresas_ec_rioja.xlsx",
    "empresas_ec_rioja_2022_2025.xlsx",
    "intensidad_provincias.csv",
    "prima_salarial_ec.xlsx",
]

print(f"{'Archivo':<45} {'Estado':>10} {'Tamaño':>12}")
print("-" * 70)
faltan_proc = []
for nombre in CLAVE_PROC:
    p = PROCESSED / nombre
    if p.exists():
        kb = p.stat().st_size / 1024
        print(f"{nombre:<45} {'OK':>10} {kb:>10,.0f} KB")
    else:
        print(f"{nombre:<45} {'ausente':>10} {'-':>12}")
        faltan_proc.append(nombre)

if faltan_proc:
    print(f"\\nAusentes (pueden regenerarse): {faltan_proc}")
""")

# ============================================================
# 4. Empresas EC
# ============================================================
md("## 4 · Empresas EC (AFIP-DGIP)")

code("""
from src.empresas_ec import (
    cargar_ec, serie_ec, por_bloque, participacion_total,
    benchmark_provincias, CIIU_EC,
)

df_ec = cargar_ec()
serie = serie_ec(df_ec)

print("Serie anual de empresas EC:")
print(serie.to_string(index=False))

v2024 = serie.loc[serie["anio"] == 2024, "total_ec"].iloc[0]
assert v2024 == 102, f"Esperado 102 en 2024, encontre {v2024}"
print(f"\\nOK: 2024 = {v2024:.0f} empresas")

part = participacion_total(df_ec)
print("\\nParticipacion sobre total provincial:")
print(part.to_string(index=False))
""")

# ============================================================
# 5. Empleo EC
# ============================================================
md("## 5 · Empleo EC")

code("""
import pandas as pd

empleo_ec = pd.read_excel("data/processed/empleo_ec_rioja.xlsx",
                           sheet_name="Empleo_EC_anual")
print("Empleo EC promedio anual:")
print(empleo_ec.to_string(index=False))

anios = empleo_ec["anio"].tolist()
assert 2019 in anios and 2025 in anios, "Faltan anios extremos"
print(f"\\nOK: Serie completa {min(anios)}-{max(anios)} ({len(anios)} anios)")
""")

# ============================================================
# 6. Benchmark 9 provincias
# ============================================================
md("## 6 · Benchmark 9 provincias — intensidad EC 2024")

code("""
bench = benchmark_provincias("2024")
print(bench.to_string(index=False))

lr = bench[bench["provincia"] == "La Rioja"]["intensidad_pm"].iloc[0]
assert 31.0 < lr < 32.0, f"La Rioja esperada ~31.3, encontre {lr}"
print(f"\\nOK: La Rioja = {lr:.2f} por mil (esperado ~31.34)")
""")

# ============================================================
# 7. Prima salarial
# ============================================================
md("## 7 · Prima salarial EC — 3 definiciones")

code("""
from src.prima_salarial import (
    parsear_hoja_remuneraciones, salario_provincial_mensual,
    RUTA_REMUN, RUTA_SAL_PROV, HOJA_REMUN,
    CIIU_NUCLEO_SW, CIIU_NUCLEO_AMPLIO, CIIU_COMPLETO,
)

df_remun = parsear_hoja_remuneraciones(RUTA_REMUN, HOJA_REMUN)
ec_remun = df_remun[df_remun["rama"].isin(CIIU_EC.keys())].copy()
sal_prov = salario_provincial_mensual(RUTA_SAL_PROV, "La Rioja")

def prima_mes(ciiu_set, etiqueta):
    filas = []
    anios_ok = [2019,2020,2021,2022,2023,2024,2025]
    for (a, m), g in ec_remun[ec_remun["anio"].isin(anios_ok)].groupby(["anio","mes"]):
        sub = g[g["rama"].isin(ciiu_set)]
        if sub.empty: continue
        sp_row = sal_prov[(sal_prov["anio"]==a) & (sal_prov["mes"]==m)]
        if sp_row.empty: continue
        sp = sp_row["valor"].iloc[0]
        if pd.isna(sp) or sp == 0: continue
        filas.append({"anio": a, "prima": (sub["remuneracion"].mean()/sp - 1)*100})
    if not filas:
        return pd.Series(dtype=float, name=etiqueta)
    return pd.DataFrame(filas).groupby("anio")["prima"].mean().round(2).rename(etiqueta)

sw = prima_mes(CIIU_NUCLEO_SW, "nucleo_software")
amp = prima_mes(CIIU_NUCLEO_AMPLIO, "nucleo_amplio")
comp = prima_mes(CIIU_COMPLETO, "afip_dgip_completo")

print(pd.concat([sw, amp, comp], axis=1).to_string())

v2025 = sw.loc[2025]
assert v2025 > 0, f"Prima nucleo software 2025 esperada >0, encontre {v2025}"
print(f"\\nOK: Prima nucleo software 2025 = +{v2025:.2f}%")
""")

# ============================================================
# 8. DGIP
# ============================================================
md("## 8 · DGIP — recaudación y contribuyentes")

code("""
try:
    import src.dgip as dg
    bib = Path("reports/bibliografia")
    pdfs = sorted(bib.glob("dgip_*.pdf"))
    if pdfs:
        df_dgip = dg.cargar_dgip_tecnologico_multi(pdfs)
        tot = dg.dgip_total_anual(df_dgip)
        print("DGIP total anual:")
        print(tot.to_string(index=False))
    else:
        print("Sin PDFs dgip_*.pdf en reports/bibliografia - se omite")
except Exception as e:
    print(f"DGIP: {e}")
""")

# ============================================================
# 9. Empleo comparado
# ============================================================
md("## 9 · Empleo comparado LR / NOA / Nación")

code("""
try:
    from src.regional import serie_provincia, serie_nacional, serie_noa

    emp_lr = serie_provincia("La Rioja", "empleo")
    emp_nac = serie_nacional("empleo")
    emp_noa = serie_noa("empleo")

    print("Empleo LR (ultimos 3):")
    print(emp_lr.tail(3).to_string())
    print("\\nEmpleo Nacion (ultimos 3):")
    print(emp_nac.tail(3).to_string())
    print("\\nEmpleo NOA (ultimos 3):")
    print(emp_noa.tail(3).to_string())
    print("\\nOK: Series LR/NOA/Nacion")
except Exception as e:
    print(f"Regional: {e}")
""")

# ============================================================
# 10. Resumen final
# ============================================================
md("## 10 · Resumen — semáforos del proyecto")

code("""
print("=" * 60)
print("  RESUMEN DEL PROYECTO")
print("=" * 60)
print()
print(f"  Empresas EC 2024:         {v2024:.0f}  (esperado 102)")
print(f"  Intensidad LR 2024:       {lr:.2f} por mil  (esperado ~31.34)")
print(f"  Prima nucleo software:    +{sw.loc[2025]:.2f}%  (2025)")
print(f"  Prima AFIP-DGIP completa: +{comp.loc[2025]:.2f}%  (2025)")
print()
print(f"  data/raw OK:              {len(CLAVE_RAW) - len(faltan_raw)}/{len(CLAVE_RAW)}")
print(f"  data/processed OK:        {len(CLAVE_PROC) - len(faltan_proc)}/{len(CLAVE_PROC)}")
print()
print("=" * 60)
print("  Chequeo completado")
print("=" * 60)
""")

# ============================================================
# Escribir
# ============================================================
nb["cells"] = celdas
nbf.write(nb, str(OUT))
print(f"OK: Generado {OUT}")
print(f"    Celdas: {len(celdas)}")
