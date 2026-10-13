# ============================================
# Análisis de empleo privado formal — La Rioja
# Desestacionalización con X-13ARIMA-SEATS
# ============================================

# 1. Instalar 'seasonal' si no está
if (!require("seasonal", quietly = TRUE)) {
  install.packages("seasonal")
}
library(seasonal)

# 2. Datos de empleo privado formal (en puestos)
#    Serie: Abr-23 a Jun-26 (39 meses)
empleo <- c(
  34866, 34329, 33740, 32593, 31886, 31274, 31051, 30693, 29977,
  31289, 36709, 33582, 31589, 30678, 28830, 28005, 27917, 28020,
  27873, 27826, 27519, 28155, 33550, 32495, 31597, 30835, 28900,
  28103, 27404, 27110, 26904, 26430, 26385, 27634, 34539, 33471,
  31358, 30305, 28656
)

# 3. Crear serie temporal (mensual, empieza Abr-23)
serie_ts <- ts(empleo, start = c(2023, 4), frequency = 12)

# 4. Aplicar ajuste estacional con X-13
ajuste <- seas(serie_ts)

# 5. Extraer serie desestacionalizada
serie_desest <- final(ajuste)

# 6. Mostrar resultados
cat("\n============================================\n")
cat("SERIE DESESTACIONALIZADA (X-13 SEATS)\n")
cat("============================================\n\n")
print(round(serie_desest, 0))

# 7. Estadísticas clave
cat("\n============================================\n")
cat("ESTADÍSTICAS CLAVE\n")
cat("============================================\n")

# Crear etiquetas de meses
meses <- c("Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic")
fechas <- seq(as.Date("2023-04-01"), by = "month", length.out = length(empleo))
labels <- paste0(meses[as.integer(format(fechas, "%m"))], "-", substr(format(fechas, "%Y"), 3, 4))

max_idx <- which.max(serie_desest)
min_idx <- which.min(serie_desest)
ult_idx <- length(serie_desest)

cat("  Pico:    ", round(serie_desest[max_idx]), " (", labels[max_idx], ")\n")
cat("  Mínimo:  ", round(serie_desest[min_idx]), " (", labels[min_idx], ")\n")
cat("  Último:  ", round(serie_desest[ult_idx]), " (", labels[ult_idx], ")\n")

# 8. Exportar a CSV para usar en el HTML
df_export <- data.frame(
  mes = labels,
  empleo_original = empleo,
  empleo_desest = round(as.numeric(serie_desest), 0)
)

write.csv(df_export, "r/serie_desestacionalizada.csv", row.names = FALSE)
cat("\n✅ CSV exportado: r/serie_desestacionalizada.csv\n")

# 9. Gráfico
plot(ajuste, main = "Desestacionalización X-13 — Empleo privado formal La Rioja")