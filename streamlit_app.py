# App: múltiples CSV heterogéneos → Bronze/Silver/Gold
# - Autodetección por archivo (sinónimos)
# - Parseo de fechas robusto (en transform.py)
# - Diagnóstico y limpieza opcional de filas inválidas
# - Imports a prueba de balas (paquete, sys.path y por ruta)

from __future__ import annotations

# --- Rutas base e imports ultrarrobustos ---
import os
import sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")

try:
    from src.transform import normalize_columns, to_silver, to_gold  # type: ignore
    from src.validate import basic_checks  # type: ignore
    from src.ingest import tag_lineage, concat_bronze  # type: ignore
except ModuleNotFoundError:
    for p in (ROOT_DIR, SRC_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        from transform import normalize_columns, to_silver, to_gold  # type: ignore
        from validate import basic_checks  # type: ignore
        from ingest import tag_lineage, concat_bronze  # type: ignore
    except ModuleNotFoundError:
        import importlib.util

        def _load(mod_name: str, path: str):
            if not os.path.exists(path):
                raise ModuleNotFoundError(f"No se encontró {path}. ¿Está src/ en la raíz del repo?")
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                raise ModuleNotFoundError(f"No se pudo cargar {path}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            sys.modules[mod_name] = mod
            return mod

        _t = _load("transform", os.path.join(SRC_DIR, "transform.py"))
        _v = _load("validate", os.path.join(SRC_DIR, "validate.py"))
        _i = _load("ingest", os.path.join(SRC_DIR, "ingest.py"))

        normalize_columns = _t.normalize_columns
        to_silver = _t.to_silver
        to_gold = _t.to_gold
        basic_checks = _v.basic_checks
        tag_lineage = _i.tag_lineage
        concat_bronze = _i.concat_bronze

# --- Dependencias estándar ---
import io
from typing import List, Dict
import pandas as pd
import streamlit as st

# ---------- Utilidades ----------
def read_csv_with_fallback(uploaded_file) -> pd.DataFrame:
    """Lee CSV, primero UTF-8 y si falla latin-1."""
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

# ---------- Sidebar: mapping global (fallback) + limpieza ----------
with st.sidebar:
    st.header("Mapping global (fallback)")
    col_date = st.text_input("Columna de fecha (→ `date`)", value="date")
    col_partner = st.text_input("Columna de partner (→ `partner`)", value="partner")
    col_amount = st.text_input("Columna de importe (→ `amount`)", value="amount")
    st.markdown("---")
    auto_clean = st.checkbox(
        "Eliminar filas inválidas (date NaT o amount no numérico) antes de validar",
        value=True,
    )
    st.caption("Se autodetectan columnas por archivo; si falta alguna, se usa este mapping.")

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
    help="Se intentará autodetectar columnas por archivo (fecha/partner/importe).",
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
    low2orig = {c.lower(): c for c in headers}
    auto_map: Dict[str, str] = {}
    for target, candidates in SYNONYMS.items():
        for cand in candidates:
            if cand.lower() in low2orig:
                auto_map[low2orig[cand.lower()]] = target
                break
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
            missing = {"date", "partner", "amount"} - set(auto_map.values())
            if missing:
                st.warning(
                    f"En `{up.name}` faltan columnas para: {', '.join(sorted(missing))}. "
                    "Revisa el mapping global o renombra columnas en el CSV."
                )
            try:
                df_norm = normalize_columns(df_raw, auto_map)
            except Exception as e:
                st.error(f"Error normalizando `{up.name}`: {e}")
                continue

            # 3) Linaje
            df_tagged = tag_lineage(df_norm, source_name=up.name)
            bronze_frames.append(df_tagged)

            st.write("Normalizado + linaje (primeras filas):")
            st.dataframe(df_tagged.head(10), use_container_width=True)

if not uploaded_files:
    st.info("💡 Sube al menos un CSV para comenzar.")
    st.stop()

# ---------- Bronze unificado ----------
bronze = concat_bronze(bronze_frames)
bronze = bronze.drop_duplicates(subset=["date", "partner", "amount"])

# Diagnóstico previo
date_parsed = pd.to_datetime(bronze["date"], errors="coerce", utc=False)
amount_num = pd.to_numeric(bronze["amount"], errors="coerce")
mask_bad_date = date_parsed.isna()
mask_bad_amount = amount_num.isna()

with st.expander("Diagnóstico de datos (antes de validaciones)", expanded=False):
    st.write(f"Filas con **date** no parseable: {int(mask_bad_date.sum())}")
    if mask_bad_date.any():
        st.dataframe(bronze.loc[mask_bad_date].head(10), use_container_width=True)
    st.write(f"Filas con **amount** no numérico: {int(mask_bad_amount.sum())}")
    if mask_bad_amount.any():
        st.dataframe(bronze.loc[mask_bad_amount].head(10), use_container_width=True)

# Limpieza opcional
if auto_clean and (mask_bad_date.any() or mask_bad_amount.any()):
    bronze = bronze.loc[~(mask_bad_date | mask_bad_amount)].copy()
    st.info("Se eliminaron filas inválidas (date NaT o amount no numérico) antes de validar.")

st.subheader("Bronze unificado")
st.dataframe(bronze, use_container_width=True)

# ---------- Validaciones ----------
st.subheader("Validaciones (basic_checks)")
errors = basic_checks(bronze)

if errors:
    st.error("Se han detectado problemas:")
    for err in errors:
        st.markdown(f"- {err}")
    st.info("Ajusta mapping o corrige el archivo de origen y vuelve a intentarlo.")
else:
    st.success("Validaciones OK.")

# Descargar bronze
st.download_button(
    label="⬇️ Descargar bronze.csv",
    data=df_to_csv_bytes(bronze),
    file_name="bronze.csv",
    mime="text/csv",
)

# ---------- Silver / Gold / KPIs ----------
if not errors and not bronze.empty:
    silver = to_silver(bronze)
    st.subheader("Silver (partner × mes)")
    st.dataframe(silver, use_container_width=True)

    gold = to_gold(silver, bronze)
    st.subheader("Gold (partner × mes, con linaje)")
    st.dataframe(gold, use_container_width=True)

    st.download_button(
        label="⬇️ Descargar silver.csv",
        data=df_to_csv_bytes(silver),
        file_name="silver.csv",
        mime="text/csv",
    )
    st.download_button(
        label="⬇️ Descargar gold.csv",
        data=df_to_csv_bytes(gold),
        file_name="gold.csv",
        mime="text/csv",
    )

    # KPIs
    st.subheader("KPIs")
    c1, c2, c3 = st.columns(3)
    total_amount = pd.to_numeric(bronze["amount"], errors="coerce").sum(min_count=1)
    unique_partners = bronze["partner"].nunique(dropna=True)
    date_min = pd.to_datetime(bronze["date"], errors="coerce").min()
    date_max = pd.to_datetime(bronze["date"], errors="coerce").max()
    with c1:
        st.metric("Importe total (EUR)", f"{total_amount:,.2f}")
    with c2:
        st.metric("Partners únicos", int(unique_partners) if pd.notna(unique_partners) else 0)
    with c3:
        rango = "—" if pd.isna(date_min) or pd.isna(date_max) else f"{date_min.date().isoformat()} → {date_max.date().isoformat()}"
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
