# streamlit_app.py
# App sobria para: subir múltiples CSV, normalizar a esquema canónico,
# validar, consolidar bronze y derivar silver con KPIs y gráfico.
# Incluye un parche defensivo de rutas para evitar "ModuleNotFoundError: No module named 'src'".

from __future__ import annotations

# --- Patch defensivo de ruta para encontrar /src ---
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")

for p in (ROOT_DIR, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)
# --- Fin del patch ---

import io
from typing import List, Dict

import pandas as pd
import streamlit as st

# Intento de import con prefijo `src.` y, en fallback, sin prefijo
try:
    from src.transform import normalize_columns, to_silver
    from src.validate import basic_checks
    from src.ingest import tag_lineage, concat_bronze
except ModuleNotFoundError:
    from transform import normalize_columns, to_silver
    from validate import basic_checks
    from ingest import tag_lineage, concat_bronze


# ---------- Utilidades ----------
def read_csv_with_fallback(uploaded_file) -> pd.DataFrame:
    """
    Lee un CSV intentando primero UTF-8 y luego latin-1 (fallback).
    uploaded_file es un st.uploaded_file_manager.UploadedFile.
    """
    uploaded_file.seek(0)
    try:
        return pd.read_csv(uploaded_file)
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding="latin-1")


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convierte un DataFrame a CSV en memoria (UTF-8)."""
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


# ---------- Configuración de página ----------
st.set_page_config(
    page_title="CSV → Bronze/Silver",
    page_icon="📦",
    layout="wide",
)

st.title("De CSVs heterogéneos a un almacén analítico confiable")
st.caption("Sube múltiples CSV, normaliza columnas, valida y genera capas bronze/silver con KPIs.")

# ---------- Sidebar: mapping y ayuda ----------
with st.sidebar:
    st.header("Configuración de columnas origen")
    st.write("Indica cómo se llaman en tus CSV las columnas que corresponden a:")
    col_date = st.text_input("Columna de fecha (→ `date`)", value="date", help="Ejemplos: fecha, transaction_date, date")
    col_partner = st.text_input("Columna de partner (→ `partner`)", value="partner", help="Ejemplos: cliente, vendor_name, partner")
    col_amount = st.text_input("Columna de importe (→ `amount`)", value="amount", help="Ejemplos: importe, total_amount, amount")
    st.markdown("---")
    st.write("**Instrucciones rápidas**")
    st.write("- Sube uno o más CSVs en la sección principal.")
    st.write("- Ajusta los nombres de columnas si difieren en tus archivos.")
    st.write("- Revisa validaciones y descarga los resultados.")

mapping: Dict[str, str] = {}
if col_date.strip():
    mapping[col_date.strip()] = "date"
if col_partner.strip():
    mapping[col_partner.strip()] = "partner"
if col_amount.strip():
    mapping[col_amount.strip()] = "amount"

# ---------- Carga de archivos ----------
uploaded_files = st.file_uploader(
    "Sube uno o más archivos CSV",
    type=["csv"],
    accept_multiple_files=True,
    help="Puedes arrastrar varios a la vez.",
)

bronze_frames: List[pd.DataFrame] = []

if uploaded_files:
    st.subheader("Normalización y linaje por archivo")
    for up in uploaded_files:
        with st.expander(f"📄 {up.name}", expanded=False):
            # 1) Leer CSV con fallback
            try:
                df_raw = read_csv_with_fallback(up)
            except Exception as e:
                st.error(f"No se pudo leer `{up.name}`: {e}")
                continue

            st.write("Vista previa (primeras filas):")
            st.dataframe(df_raw.head(10), use_container_width=True)

            # 2) Normalizar columnas al canónico
            try:
                df_norm = normalize_columns(df_raw, mapping)
            except Exception as e:
                st.error(f"Error normalizando `{up.name}`: {e}")
                continue

            # 3) Anotar linaje
            df_tagged = tag_lineage(df_norm, source_name=up.name)
            bronze_frames.append(df_tagged)

            st.write("Normalizado + linaje (primeras filas):")
            st.dataframe(df_tagged.head(10), use_container_width=True)

if not uploaded_files:
    st.info("💡 Sube al menos un CSV para comenzar.")
    st.stop()

# ---------- Consolidación Bronze ----------
bronze = concat_bronze(bronze_frames)

st.subheader("Bronze unificado")
st.dataframe(bronze, use_container_width=True)

# ---------- Validaciones ----------
st.subheader("Validaciones (basic_checks)")
errors = basic_checks(bronze)

if errors:
    st.error("Se han detectado problemas:")
    for err in errors:
        st.markdown(f"- {err}")
    st.info("Corrige las columnas mapeadas o los datos de origen y vuelve a intentarlo.")
else:
    st.success("Validaciones OK: el conjunto bronze cumple los requisitos mínimos.")

# Botón descarga bronze (se ofrece aunque haya errores para facilitar depuración)
bronze_csv = df_to_csv_bytes(bronze)
st.download_button(
    label="⬇️ Descargar bronze.csv",
    data=bronze_csv,
    file_name="bronze.csv",
    mime="text/csv",
)

# ---------- Silver, KPIs y gráfico ----------
if not errors:
    # Silver
    silver = to_silver(bronze)
    st.subheader("Silver (partner × mes)")
    st.dataframe(silver, use_container_width=True)

    # KPIs simples
    st.subheader("KPIs")
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    total_amount = pd.to_numeric(bronze["amount"], errors="coerce").sum(min_count=1)
    unique_partners = bronze["partner"].nunique(dropna=True)
    date_min = pd.to_datetime(bronze["date"], errors="coerce").min()
    date_max = pd.to_datetime(bronze["date"], errors="coerce").max()

    with kpi_col1:
        st.metric("Importe total (EUR)", f"{total_amount:,.2f}")
    with kpi_col2:
        st.metric("Partners únicos", int(unique_partners) if pd.notna(unique_partners) else 0)
    with kpi_col3:
        rango = "—"
        if pd.notna(date_min) and pd.notna(date_max):
            rango = f"{date_min.date().isoformat()} → {date_max.date().isoformat()}"
        st.metric("Rango de fechas", rango)

    # Gráfico mensual (sobrio, sin estilos custom)
    st.subheader("Tendencia mensual (importe total)")
    if not silver.empty:
        monthly = (
            silver.groupby("month", as_index=False, dropna=True)["amount"]
            .sum(min_count=1)
            .sort_values("month")
        )
        chart_df = monthly.set_index("month")
        st.bar_chart(chart_df["amount"])
    else:
        st.info("No hay datos en silver para graficar.")

    # Descarga silver
    silver_csv = df_to_csv_bytes(silver)
    st.download_button(
        label="⬇️ Descargar silver.csv",
        data=silver_csv,
        file_name="silver.csv",
        mime="text/csv",
    )

# ---------- Notas finales ----------
with st.expander("Notas y supuestos", expanded=False):
    st.markdown(
        """
- La **normalización** usa el mapeo indicado en la barra lateral para convertir columnas origen a `date`, `partner`, `amount`.
- El **importe** se limpia para aceptar formatos europeos (comas/puntos y símbolo €).
- La **fecha** se normaliza a tipo datetime y se usa el **inicio de mes** para la agregación mensual.
- **Bronze** incluye linaje (`source_file`, `ingested_at` UTC).
- **Silver** agrega por `partner` y `month`.
- Los **botones de descarga** generan CSV a partir de las tablas mostradas.
        """
    )
