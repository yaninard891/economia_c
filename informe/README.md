# Informe EC La Rioja

## Generar los documentos

```bash
cd informe
quarto render
```

Salida en `_output/`:
- `informe_completo.docx` — documento completo (Word)
- `resumen_web.html` — resumen web autocontenido

## Estructura

- `informe_completo.qmd` — documento principal (Word)
- `resumen_web.qmd` — resumen curado (HTML)
- `reference.docx` — plantilla de estilos Word
- `referencias.bib` — bibliografía
- `estilos_web.css` — estilos del HTML
- `figuras/` — PNGs generados por `src/visualizaciones.py`