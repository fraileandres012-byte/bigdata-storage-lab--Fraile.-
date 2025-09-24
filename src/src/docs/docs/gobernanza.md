# Gobernanza de Datos

Este documento describe las políticas de gobierno de datos aplicadas en el laboratorio.

---

## Origen y Linaje
- Cada CSV debe registrarse con:
  - Nombre del archivo original.
  - Fecha de ingesta.
  - Fuente (sistema o proveedor).
- El linaje debe permitir rastrear cada KPI hasta su origen (raw → bronze → silver → gold).

---

## Validaciones mínimas
1. **Formato de fecha**: convertir todas a `YYYY-MM-DD`.  
2. **Partner**: no nulo, cadena limpia (sin espacios extra).  
3. **Amount**: debe poder convertirse a float; no se aceptan valores vacíos ni texto.  
4. **Duplicados**: se eliminan registros idénticos (date + partner + amount).  
5. **Nulos críticos**: filas con valores nulos en campos canónicos se descartan con log.  

---

## Política de mínimos privilegios
- **Repositorio GitHub**: acceso *read* para revisores externos; *write* solo para contribuyentes principales.  
- **Streamlit app**: expone únicamente KPIs y validaciones, nunca datos sensibles.  
- **Carpeta `data/`**:
  - `raw/`: acceso restringido; solo lectura por pipeline.  
  - `bronze/`, `silver/`, `gold/`: accesibles según rol, nunca editables manualmente.  

---

## Trazabilidad
- Log de ingesta con timestamp y nombre de archivo.  
- Log de validación con recuento de filas válidas/erróneas.  
- Versionado de scripts en GitHub para garantizar reproducibilidad.  
- Commit messages descriptivos con prefijos (`ingest:`, `validate:`, `transform:`).  

---

## Roles
- **Data Engineer**: diseña y mantiene el pipeline (ingesta, validación, transformaciones).  
- **Data Analyst**: consume tablas silver/gold y diseña KPIs.  
- **Data Steward**: garantiza calidad, revisa el diccionario y políticas de gobernanza.  
- **Admin**: gestiona permisos de acceso en GitHub y Streamlit.  
