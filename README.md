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
    
     ### Plantilla general
| V prioritaria                                         | Elecciones (Ingesta / Storage / Compute / Analítica)                                                                                                                                                                                        | Riesgos clave                                                     | Mitigaciones                                                                                                | Métrica de éxito                                                                        |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| \[Volumen / Velocidad / Variedad / Veracidad / Valor] | **Ingesta:** \[batch / micro-batch / streaming]. **Storage:** \[CSV/Parquet, particionado (por fecha/entidad), inmutable + linaje]. **Compute:** \[pandas/pyarrow / Spark / ventanas temporales]. **Analítica:** \[KPIs, alertas, modelos]. | \[schema drift, PII, duplicados, datos tardíos, outliers, costes] | \[validaciones, data contracts, deduplicación, watermarking, enmascarado PII, particionado, monitorización] | \[SLA latencia, % filas válidas, cobertura, coste/consulta, precisión/recall, frescura] |


### E-commerce
| V prioritaria                                | Elecciones (Ingesta / Storage / Compute / Analítica)                                                                                                                                                                                                                                                                                      | Riesgos clave                                                                   | Mitigaciones                                                                                                                              | Métrica de éxito                                                                                                     |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Valor** (y **Velocidad** a escala horaria) | **Ingesta:** micro-batches cada 60 min desde sistemas de pedidos. **Storage:** Parquet inmutable, particionado por `date` y opcional por `partner` (Bronze→Silver→Gold) con linaje. **Compute:** agregaciones por hora/mes (pandas/pyarrow; escalar a Spark si crece). **Analítica:** KPIs de revenue, AOV, tasa de repetición, cohortes. | *Schema drift* en catálogos/SKUs, PII en datos, outliers en precios/cantidades. | Data contracts + validaciones (tipos, rangos), normalización de moneda, reglas anti-outliers, eliminación/anonimización de PII en Bronze. | **SLA** T+15 min, **% válidas** ≥ 98%, **frescura** ≤ 1 h, **consistencia** (revenue diario concilia con ERP ±0.5%). |


### Sensores IoT
| V prioritaria                 | Elecciones (Ingesta / Storage / Compute / Analítica)                                                                                                                                                                                                                                                                                                      | Riesgos clave                                                                           | Mitigaciones                                                                                                                                        | Métrica de éxito                                                                                                       |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Velocidad** (y **Volumen**) | **Ingesta:** streaming o micro-batches de 1–5 min. **Storage:** Parquet/Delta append-only, particionado por `date`/`hour` y `sensor_id`; compaction periódica. **Compute:** ventanas deslizantes para medias/mín-máx y detección de anomalías; deduplicación por `sensor_id+ts`. **Analítica:** panel de salud (temperatura/humedad), alertas por umbral. | Datos tardíos/duplicados, huecos en series (pérdida de paquetes), drift en calibración. | Watermarking y *late arrival handling*, claves de deduplicación, *forward/backfill* limitado, recalibración programada, monitorización de latencia. | **Latencia de alerta** ≤ 2 min, **completitud** ≥ 97%, **tasa de duplicados** ≤ 0.5%, **MTTA**/MTTR mejoran mes a mes. |


### Logs de fraude
| V prioritaria                                | Elecciones (Ingesta / Storage / Compute / Analítica)                                                                                                                                                                                                                                                                                                                | Riesgos clave                                                                                           | Mitigaciones                                                                                                                                              | Métrica de éxito                                                                                                                                           |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Veracidad** (y **Velocidad** para scoring) | **Ingesta:** append-only en tiempo casi real desde pasarela de pagos. **Storage:** Bronze crudo con linaje; Silver normalizado; **Gold** como *feature table* por usuario/tarjeta/ventana. **Compute:** scoring en tiempo real + agregaciones históricas; ventanas 5–30 min. **Analítica:** panel de precisión/recall, tasa de falsos positivos, pérdidas evitadas. | *Class imbalance*, *concept drift* (patrones cambian), costo de falsos positivos, latencia de decisión. | Umbrales adaptativos, reentrenos periódicos, *drift monitoring*, *A/B* de reglas/modelos, *fallback* a heurísticas, límites de latencia por ruta crítica. | **Precision\@K** y **Recall** objetivo (p.ej. ≥ 0.85/≥ 0.70), **FPR** ≤ 1%, **latencia de scoring** ≤ 300 ms, **pérdida evitada** ↑ trimestre a trimestre. |


- **Checklist rápido:**
- [ ] Repo público creado  
- [ ] `src/__init__.py` existe  
- [ ] Carpetas `data/*` con `.gitkeep`

---

### 2) Pegar archivos base (15–20 min)
- **Acción:** Copia/pega en GitHub el contenido que ya tienes:
- `requirements.txt` ➜ `streamlit`, `pandas`, `pyarrow`, `python-dateutil`
- `src/ingest.py`, `src/validate.py`, `src/transform.py` (funciones entregadas)
- `streamlit_app.py` (versión con **parche de rutas** y **Gold**)
- `docs/diccionario.md`, `docs/gobernanza.md`
- `tests/checklist.md`, `tests/rubrica.md` (si lo creaste)
- **Checklist rápido:**
- [ ] `requirements.txt` con 4 líneas  
- [ ] `streamlit_app.py` importa `normalize_columns`, `to_silver`, `to_gold`  
- [ ] `src/` contiene `ingest.py`, `validate.py`, `transform.py`  
- [ ] `docs/` y `tests/` tienen sus archivos

---

### 3) Subir CSV de prueba (5–10 min)
- **Acción:** Descarga y usa los 3 CSV de ejemplo que te pasé:
- `ventas_mes.csv`, `sales_may.csv`, `partners_jun.csv`
- **En la app (local o cloud):**  
- Sube **un CSV a la vez** y configura mapping en la barra lateral:
  - `ventas_mes.csv`: `fecha → date`, `cliente → partner`, `importe → amount`
  - `sales_may.csv`: `date_time → date`, `partner_name → partner`, `sales → amount`
  - `partners_jun.csv`: `Fecha → date`, `Partner → partner`, `Importe → amount`
- **Checklist rápido:**
- [ ] Validaciones OK (sin errores críticos)  
- [ ] Se ve **Bronze** y **Silver** (y **Gold** si activaste reto C)  
- [ ] Descargas **bronze.csv**/**silver.csv** funcionan

---

### 4) Desplegar en Streamlit Community Cloud (10–15 min)
- **Acción:** En https://share.streamlit.io → **New app**:
- Repo: `bigdata-storage-lab-<apellido>`
- Branch: `main`
- **Main file:** `streamlit_app.py`
- **Deploy**
- **Checklist rápido:**
- [ ] URL pública operativa  
- [ ] `streamlit_app.py` es el main file  
- [ ] Dependencias instaladas (no errores en logs)  
- [ ] Subida de CSV y mapeo funcionando

---

### 5) Completar README con reflexiones (10–20 min)
- **Acción:** En `README.md` agrega:
- **Prompts de reflexión** (bloque con placeholders) y **responde**  
- **Tablas de decisiones por caso** (plantilla + e-commerce/IoT/fraude)  
- Enlaces útiles (app, notebook si aplica)
- **Checklist rápido:**
- [ ] Respuestas completas en Prompts (sin placeholders)  
- [ ] Tablas por caso pegadas o enlazadas desde `docs/`  
- [ ] Versión final del README sin secciones vacías

---

### 6) Entregar URLs (5 min)
- **Acción:** Reúne y comparte:
- **URL del repo GitHub**: `https://github.com/<usuario>/bigdata-storage-lab-<apellido>`
- **URL de la app** (Streamlit): `https://<usuario>-<app>.streamlit.app`
- **(Opcional) URL notebook Colab**: si añadiste el `.ipynb`, pega el enlace “Open in Colab”
- **Checklist rápido:**
- [ ] URLs accesibles sin permisos  
- [ ] README enlaza a la app/notebook  
- [ ] `tests/checklist.md` marcado

---

## ✅ Antes de entregar (control final)
- [ ] **App**: sube 1 CSV y valida que aparecen Bronze/Silver (y gráfico + KPIs)  
- [ ] **Descargas**: funcionan **bronze.csv** y **silver.csv**  
- [ ] **Repo**: contiene `src/`, `docs/`, `tests/`, `data/*/.gitkeep`  
- [ ] **README**: objetivos, decisiones (5V→elecciones), **Prompts respondidos**, tablas por caso  
- [ ] **Gobernanza**: `docs/diccionario.md` y `docs/gobernanza.md` completos  
- [ ] **Rubrica**: puedes autoevaluarte con `tests/rubrica.md` (10 puntos)  
- [ ] **URLs**: compartidas (GitHub + Streamlit [+ Colab])  


