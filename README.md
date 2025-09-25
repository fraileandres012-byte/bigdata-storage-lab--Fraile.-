# bigdata-storage-lab--Fraile.-
## 🧠 Prompts de reflexión (responder en el README)

1) **V dominante hoy y V dominante si 2× tráfico (3 líneas)**
   - *Respuesta (3 líneas):*  
     1) [Escribe aquí la V dominante actual (Volumen/Velocidad/Variedad/Veracidad/Valor) y por qué.]  
     2) [Explica cómo cambiaría con 2× tráfico y cuál sería la nueva V dominante.]  
     3) [Consecuencia operativa o de arquitectura de ese cambio.]

2) **Trade-off elegido (p. ej., más compresión vs. más CPU)**
   - *Respuesta:*  
     - Decisión: [Describe el trade-off concreto.]  
     - Por qué: [Justificación técnica/negocio.]  
     - Cómo lo mediré: [Métrica(s), dataset, procedimiento y umbrales de aceptación.]

3) **“Inmutable + linaje” → veracidad**
   - *Respuesta:*  
     - Beneficio: [Cómo la inmutabilidad y el linaje aumentan trazabilidad y confianza.]  
     - Coste añadido: [Almacenamiento, complejidad operativa, latencia o mantenimiento.]  
     - Compensación: [Por qué el beneficio supera el coste en este caso.]

4) **KPI principal y SLA del dashboard**
   - *Respuesta:*  
     - KPI: [Define el KPI clave y su fórmula.]  
     - SLA/latencia: [p. ej., T+15 min / diario 08:00.]  
     - Decisión habilitada: [Qué decisión concreta permite y por qué esa latencia es suficiente.]

5) **Riesgo principal del diseño y mitigación**
   - *Respuesta:*  
     - Riesgo: [Punto único de fallo, datos corruptos, schema drift, costes, etc.]  
     - Impacto: [Qué rompe y a quién afecta.]  
     - Mitigación técnica: [Medida concreta: validaciones, idempotencia, versionado de esquemas, retries/backoff, particionado, monitorización/alertas.]
