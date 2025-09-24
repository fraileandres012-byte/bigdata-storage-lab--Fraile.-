# Diccionario de Datos Canónico

Este documento define el **esquema canónico** que unifica los CSVs heterogéneos hacia un modelo estándar.  
El objetivo es garantizar consistencia, calidad y trazabilidad a lo largo del pipeline.

---

## Esquema Canónico

| Campo   | Tipo   | Formato / Unidad | Descripción                           |
|---------|--------|------------------|---------------------------------------|
| `date`  | Date   | `YYYY-MM-DD`     | Fecha de la transacción.              |
| `partner` | String | Texto libre      | Nombre o identificador del socio/proveedor/cliente. |
| `amount` | Float | EUR (€)          | Importe monetario en euros.           |

---

## Mapeos de Origen → Canónico

Ejemplos típicos de columnas heterogéneas que deben transformarse:

| Origen (CSV) | Ejemplo valor | Campo Canónico | Transformación requerida |
|--------------|---------------|----------------|--------------------------|
| `fecha` | `15/04/2024` | `date` | Reformat `DD/MM/YYYY` → `YYYY-MM-DD` |
| `transaction_date` | `2024-04-15T09:30:00` | `date` | Extraer fecha → `YYYY-MM-DD` |
| `cliente` | `ACME S.A.` | `partner` | Normalizar a `partner` |
| `vendor_name` | `Amazon EU` | `partner` | Normalizar a `partner` |
| `importe` | `1.234,56` | `amount` | Convertir string con coma decimal → float EUR |
| `total_amount` | `1234.56` | `amount` | Parsear a float EUR |

---

## Notas
- Los campos adicionales en origen que no estén en el canónico se documentarán aparte o se descartarán.  
- El diccionario se revisará y ampliará según aparezcan nuevas fuentes.

