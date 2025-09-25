# streamlit_app.py
# App para: subir múltiples CSV, autodetectar columnas por archivo,
# normalizar → validar → consolidar Bronze → derivar Silver/Gold, KPIs y gráfico.
# Cabecera de imports ultrarrobusta (paquete, sys.path y carga por ruta).

from __future__ import annotations

# --- Rutas base ---
import os
import sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")

# --- Intento 1: importar como paquete src. ---
try:
    from src.transform import normalize_columns, to_silver, to_gold  # type: ignore
    from src.validate import basic_checks  # type: ignore
    from src.ingest import tag_lineage, concat_bronze  # type: ignore
except ModuleNotFoundError:
    # --- Intento 2: forzar sys.path y reintentar como módulos planos ---
    for p in (ROOT_DIR, SRC_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        from transform import normalize_columns, to_silver, to_gold  # type: ignore
        from validate import basic_checks  # type: ignore
        from ingest import tag_lineage, concat_bronze  # type: ignore
    except ModuleNotFoundError:
        # --- Intento 3: carga por ruta absoluta con importlib ---
        import importlib.util

        def _load_module(mod_name: str, file_path: str):
            if not os.path.exists(file_path):
                raise ModuleNotFoundError(f"No se encontró {file_path}. ¿Está src/ en la raíz del repo?")
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            if spec is None or spec.loader is None:
                raise ModuleNotFoundError(f"No se pudo crear spec para {file_path}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            sys.modules[mod_name] = mod
            return mod

        _t = _load_module("transform", os.path.join(SRC_DIR, "transform.py"))
        _v = _load_module("validate", os.path.join(SRC_DIR, "validate.py"))
        _i = _load_module("ingest", os.path.join(SRC_DIR, "ingest.py"))

        normalize_columns = _t.normalize_columns
        to_silver = _t.to_silver
        to_gold = getattr(_t, "to_gold", None)  # puede no existir si no hiciste el reto C
        basic_checks = _v.basic_checks
        tag_lineage = _i.tag_lineage
        concat_bronze = _i.concat_bronze

# ---- Dependencias estándar de la app ----
import io
from typing import List, Dict

import pandas as pd
import streamlit as st

# ---------- Utilidades ----------
def read_csv_with_fallback(uploaded_file) -> pd.DataFrame:
    """Lee un CSV intentando primero UTF-8 y luego latin-1 (fallback)."""
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
st.set_page_config(page_title="CSV → Bronze/Silver/Gold", page_icon="📦", layout="wide")
st.title("De CSVs heterogéneos a un almacén analítico confiable")
st.caption("Sube múltiples CSV, autodetecta columnas por archivo, valida y genera Bronze/Silver/Gold con KPIs.")

# ---------- Sidebar: mapping global (fallback) ----------
with st.sidebar:
    st.header("Mapping global (fallback)")
    col_date = st.text_input("Columna de fecha (→ `date`)", value="date")
    col_partner = st.text_input("Columna de partner (→ `partner`)", value="partner")
    col_amount = st.text_input("Columna de importe (→ `amount`)", value="amount")
    st.markdown("---")
    st.write("Se autodetectan columnas por archivo. Si falta alguna, se usa este mapping.")

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
    help="Se intentará autodetectar columnas por archivo.",
)

bronze_frames: List[pd.DataFrame] = []

# Sinónimos para autodetección
SYNONYMS = {
    "date": ["date", "fecha", "date_time", "fechahora", "fch", "Fecha"],
    "partner": ["partner", "cliente", "partner_name", "proveedor", "Partner"],
    "amount": ["amount", "importe", "total_amount", "sales", "Importe"],
}

def build_auto_mapping(df_raw: pd.DataFrame, fallback: Dict[str, str]) -> Dict[str, str]:
    """Crea mapping origen→canónico por archivo: sinónimos + fallback."""
    headers = [str(c).strip() for c in df_raw.columns]
    lower_to_orig = {c.lower(): c for c in headers}
    auto_map: Dict[str, str] = {}
    for target, candidates in SYNONYMS.items():
        for cand in candidates:
            if cand.lower() in lower_to_orig:
                auto_map[lower_to_orig[cand.lower()]] = target
                break
    # Completar con fallback si falta alguno
    present_targets = set(auto_map.values())
    for src_col, tgt in fallback.items():
        if tgt not in present_targets and src_col in df_raw.columns:
            auto_map[src_col] = tgt
    return auto_map


if uploaded_files:
    st.subheader("Normalización y linaje por archivo")
    for up in uploaded_files:
        with st.expander(f"📄 {up.name}", expanded=False):
            # 1) Leer CSV
            try:
                df_raw = read_csv_with_fallback(up)
            except Exception as e:
                st.error(f"No se pudo leer `{up.name}`: {e}")
                continue

            st.write("Vista previa (primeras filas):")
            st.dataframe(df_raw.head(10), use_container_width=True)

            # 2) Autodetectar mapping y normalizar
            auto_map = build_auto_mapping(df_raw, fallback_mapping)
            missing_targets = {"date", "partner", "amount"} - set(auto_map.values())
            if missing_targets:
                st.warning(
                    f"En `{up.name}` faltan columnas para: {', '.join(sorted(missing_targets))}. "
                    f"Revisa el mapping global o renombra columnas en el CSV."
                )
            try:
                df_norm = normalize_columns(df_raw, auto_map)  # type: ignore
            except Exception as e:
                st.error(f"Error normalizando `{up.name}`: {e}")
                continue

            # 3) Linaje
            df_tagged = tag_lineage(df_norm, source_name=up.name)  # type: ignore
            bronze_frames.append(df_tagged)

            st.write("Normalizado + linaje (primeras filas):")
            st.dataframe(df_tagged.head(10), use_container_width=True)

if not uploaded_files:
    st.info("💡 Sube al menos un CSV para comenzar.")
    st.stop()

# ---------- Bronze unificado ----------
bronze = concat_bronze(bronze_frames)  # type: ignore
bronze = bronze.drop_duplicates(subset=["date", "partner", "amount"])  # limpiar duplicados exactos

st.subheader("Bronze unificado")
st.dataframe(bronze, use_container_width=True)

# ---------- Validaciones ----------
st.subheader("Validaciones (basic_checks)")
errors = basic_checks(bronze)  # type: ignore

if errors:
    st.error("Se han detectado problemas:")
    for err in errors:
        st.markdown(f"- {err}")
    st.info("Corrige el mapping (global o renombrando columnas) o revisa los datos de origen y vuelve a intentarlo.")
else:
    st.success("Validaciones OK: el conjunto bronze cumple los requisitos mínimos.")

# Descargar bronze
st.download_button(
    label="⬇️ Descargar bronze.csv",
    data=df_to_csv_bytes(bronze),
    file_name="bronze.csv",
    mime="text/csv",
)

# ---------- Silver / Gold / KPIs ----------
if not errors:
    # Silver
    silver = to_silver(bronze)  # type: ignore
    st.subheader("Silver (partner × mes)")
    st.dataframe(silver, use_container_width=True)

    # Gold (si existe la función; si no, omite)
    if callable(to_gold):  # type: ignore
        gold = to_gold(silver, bronze)  # type: ignore
        st.subheader("Gold (partner × mes, con linaje)")
        st.dataframe(gold, use_container_width=True)
        st.download_button(
            label="⬇️ Descargar gold.csv",
            data=df_to_csv_bytes(gold),
            file_name="gold.csv",
            mime="text/csv",
        )

    # Descargar silver
    st.download_button(
        label="⬇️ Descargar silver.csv",
        data=df_to_csv_bytes(silver),
        file_name="silver.csv",
        mime="text/csv",
    )

    # KPIs
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

    # Tendencia mensual
    st.subheader("Tendencia mensual (importe total)")
    if not silver.empty:
        monthly = (
            silver.groupby("month", as_index=False, dropna=True)["amount"]
            .sum(min_count=1)
            .sort_values("month")
        )
        st.bar_chart(monthly.set_index("month")["amount"])
    else:
        st.info("No hay datos en silver para graficar.")

# ---------- Notas ----------
with st.expander("Notas y supuestos", expanded=False):
    st.markdown(
        """
- Autodetección de columnas por archivo (sinónimos) con fallback de la barra lateral.
- Fechas normalizadas y formatos europeos de importe soportados.
- Bronze con linaje (`source_file`, `ingested_at`) y deduplicación exacta.
- Silver agrega por `partner` y `month`.
- Gold añade `last_update` y `sources` (si implementado).
        """
    )
