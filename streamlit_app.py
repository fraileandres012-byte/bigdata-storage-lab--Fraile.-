# streamlit_app.py
# App para: subir múltiples CSV, autodetectar columnas por archivo,
# normalizar → validar → consolidar Bronze → derivar Silver/Gold, KPIs y gráfico.
# Incluye: parche de rutas, autodetección de mapeo por archivo, y descarga de CSVs.

from __future__ import annotations

# --- Patch defensivo para encontrar /src sin depender del cwd ---
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

# Import directo desde /src (porque añadimos SRC_DIR al sys.path)
from transform import normalize_columns, to_silver, to_gold
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
    page_title="CSV → Bronze/Silver/Gold",
    page_icon="📦",
    layout="wide",
)

st.title("De CSVs heterogéneos a un almacén analítico confiable")
st.caption("Sube múltiples CSV, autodetecta columnas por archivo, valida y genera Bronze/Silver/Gold con KPIs.")

# ---------- Sidebar: mapping global (fallback) y ayuda ----------
with st.sidebar:
    st.header("Mapping global (fallback)")
    st.write("Si un archivo no se reconoce automáticamente, se usará este mapping.")
    col_date = st.text_input("Columna de fecha (→ `date`)", value="date", help="Ej.: fecha, date_time, date")
    col_partner = st.text_input("Columna de partner (→ `partner`)", value="partner", help="Ej.: cliente, partner_name")
    col_amount = st.text_input("Columna de importe (→ `amount`)", value="amount", help="Ej.: importe, sales, total_amount")
    st.markdown("---")
    st.write("**Consejo**: puedes subir varios CSV con cabeceras distintas; el sistema intentará mapear cada archivo automáticamente.")
    st.write("Si algún archivo queda con columnas sin reconocer, ajusta el mapping de arriba y vuelve a subir.")

fallback_mapping: Dict[str, str] = {}
if col_date.strip():
    fallback_mapping[col_date.strip()] = "date"
if col_partner.strip():
    fallback_mapping[col_partner.strip()] = "partner"
if col_amount.strip():
    fallback_mapping[col_amount.strip()] = "amount"

# ---------- Carga de archivos ----------
uploaded_files = st.file_uploader(
    "Sube uno o más archivos CSV",
    type=["csv"],
    accept_multiple_files=True,
    help="Puedes arrastrar varios a la vez. Se intentará autodetectar columnas por archivo.",
)

bronze_frames: List[pd.DataFrame] = []

# Sinónimos para autodetección de columnas por archivo
SYNONYMS = {
    "date": ["date", "fecha", "date_time", "fechahora", "fch", "Fecha"],
    "partner": ["partner", "cliente", "partner_name", "proveedor", "Partner"],
    "amount": ["amount", "importe", "total_amount", "sales", "Importe"],
}

def build_auto_mapping(df_raw: pd.DataFrame, fallback: Dict[str, str]) -> Dict[str, str]:
    """
    Crea un mapping origen→canónico por archivo:
      1) Busca por sinónimos (case-insensitive).
      2) Completa con el mapping global (fallback) si alguna canónica falta.
    """
    headers = [str(c).strip() for c in df_raw.columns]
    lower_to_orig = {c.lower(): c for c in headers}

    auto_map: Dict[str, str] = {}
    for target, candidates in SYNONYMS.items():
        found = None
        for cand in candidates:
            if cand.lower() in lower_to_orig:
                found = lower_to_orig[cand.lower()]
                break
        if found is not None:
            auto_map[found] = target

    # Completar con fallback si falta alguno y existe en el df
    present_targets = set(auto_map.values())
    for src_col, tgt in fallback.items():
        if tgt not in present_targets and src_col in df_raw.columns:
            auto_map[src_col] = tgt

    return auto_map


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

            # 2) Autodetectar mapping por archivo y normalizar
            auto_map = build_auto_mapping(df_raw, fallback_mapping)

            missing_targets = {"date", "partner", "amount"} - set(auto_map.values())
            if missing_targets:
                st.warning(
                    f"En `{up.name}` faltan columnas para: {', '.join(sorted(missing_targets))}. "
                    f"Revisa el mapping global o renombra columnas en el CSV."
                )

            try:
                df_norm = normalize_columns(df_raw, auto_map)
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

# (Opcional) eliminar duplicados exactos por clave natural si aparecen
bronze = bronze.drop_duplicates(subset=["date", "partner", "amount"])

st.subheader("Bronze unificado")
st.dataframe(bronze, use_container_width=True)

# ---------- Validaciones ----------
st.subheader("Validaciones (basic_checks)")
errors = basic_checks(bronze)

if errors:
    st.error("Se han detectado problemas:")
    for err in errors:
        st.markdown(f"- {err}")
    st.info("Corrige el mapping (global o renombrando columnas) o revisa los datos de origen y vuelve a intentarlo.")
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

# ---------- Silver, GOLD, KPIs y gráfico ----------
if not errors:
    # Silver
    silver = to_silver(bronze)
    st.subheader("Silver (partner × mes)")
    st.dataframe(silver, use_container_width=True)

    # GOLD (partner×mes con linaje: last_update, sources)
    gold = to_gold(silver, bronze)
    st.subheader("Gold (partner × mes, con linaje)")
    st.dataframe(gold, use_container_width=True)

    # Descarga silver
    silver_csv = df_to_csv_bytes(silver)
    st.download_button(
        label="⬇️ Descargar silver.csv",
        data=silver_csv,
        file_name="silver.csv",
        mime="text/csv",
    )

    # Descarga gold
    gold_csv = df_to_csv_bytes(gold)
    st.download_button(
        label="⬇️ Descargar gold.csv",
        data=gold_csv,
        file_name="gold.csv",
        mime="text/csv",
    )

    # KPIs simples (sobre bronze)
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

# ---------- Notas finales ----------
with st.expander("Notas y supuestos", expanded=False):
    st.markdown(
        """
- Autodetección de columnas por archivo basada en sinónimos comunes (date/fecha/date_time, partner/cliente, amount/importe/sales).
- Si falta alguna columna canónica, se usa el *mapping* global de la barra lateral como **fallback**.
- El importe se limpia para aceptar formatos europeos (comas/puntos y símbolo €).
- La fecha se normaliza a tipo datetime y se usa el **inicio de mes** para la agregación mensual.
- **Bronze** incluye linaje (`source_file`, `ingested_at` UTC) y se deduplican registros exactos por `(date, partner, amount)`.
- **Silver** agrega por `partner` y `month`.
- **Gold** añade `last_update` y `sources` por `partner × month` para facilitar el reporting.
- Botones de descarga para **bronze/silver/gold**.
        """
    )
