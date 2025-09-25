from typing import Dict
import re
import pandas as pd


def _clean_amount_to_float(x: object) -> float:
    """
    Convierte montos con formatos europeos/mixtos a float (EUR).
    Soporta: "1.234,56", "1,234.56", "€1.234,56", "- 2.500", "2500", "2,5"
    """
    if pd.isna(x):
        return float("nan")
    s = str(x).strip()

    # quitar símbolos y espacios
    s = s.replace("€", "").replace("EUR", "").strip()
    s = re.sub(r"\s+", "", s)
    # permitir dígitos/signo/puntos/comas
    s = re.sub(r"[^0-9\-,\.]", "", s)

    if s.count(",") > 0 and s.count(".") > 0:
        # 1.234,56 -> 1234.56
        s = s.replace(".", "").replace(",", ".")
    elif s.count(",") > 0 and s.count(".") == 0:
        # 2,5 -> 2.5
        s = s.replace(",", ".")
    # si solo hay punto, se deja

    try:
        return float(s)
    except ValueError:
        return float("nan")


def normalize_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Normaliza a canónico: date (datetime), partner (str), amount (float EUR).
    - Renombra columnas según mapping {origen: canónico}.
    - Parsea fechas con fallback day-first para DD/MM/YYYY.
    - Limpia partner (espacios múltiples).
    - Normaliza amount.
    """
    out = df.rename(columns=mapping).copy()

    # Asegurar columnas canónicas
    for col in ("date", "partner", "amount"):
        if col not in out.columns:
            out[col] = pd.NA

    # --- Fecha robusta ---
    raw_date = out["date"].astype("string").str.strip()

    # 1º intento: inferencia general
    parsed = pd.to_datetime(raw_date, errors="coerce", utc=False, infer_datetime_format=True)

    # 2º intento: formatos con barras -> dayfirst (DD/MM/YYYY)
    mask_slash = raw_date.str.contains(r"\d{1,2}/\d{1,2}/\d{2,4}", na=False)
    parsed = parsed.fillna(pd.to_datetime(raw_date.where(mask_slash), errors="coerce", dayfirst=True))

    # Normalizar a medianoche (solo fecha)
    out["date"] = parsed.dt.normalize()

    # Partner
    out["partner"] = out["partner"].astype("string").str.strip()
    out["partner"] = out["partner"].str.replace(r"\s+", " ", regex=True)

    # Amount
    out["amount"] = out["amount"].apply(_clean_amount_to_float)

    return out[["date", "partner", "amount"]]


def to_silver(bronze: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega amount por partner y mes (month = inicio de mes).
    """
    df = bronze.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=False)
    df["partner"] = df["partner"].astype("string")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    month_ts = df["date"].dt.to_period("M").dt.to_timestamp(how="start")

    grouped = (
        df.assign(month=month_ts)
        .groupby(["partner", "month"], dropna=True, as_index=False, observed=True)["amount"]
        .sum(min_count=1)
    )
    return grouped[["partner", "month", "amount"]]


def to_gold(silver: pd.DataFrame, bronze: pd.DataFrame) -> pd.DataFrame:
    """
    GOLD (partner × month) para reporting:
      - partner, month, amount_total
      - last_update: max(ingested_at) en bronze para ese partner×month
      - sources: lista única de source_file separados por '|'
    """
    if silver.empty:
        return pd.DataFrame(columns=["partner", "month", "amount_total", "last_update", "sources"])

    g = (
        silver.groupby(["partner", "month"], as_index=False)["amount"]
        .sum(min_count=1)
        .rename(columns={"amount": "amount_total"})
    )

    b = bronze.copy()
    b["month"] = pd.to_datetime(b["date"], errors="coerce").dt.to_period("M").dt.to_timestamp("start")

    lin = (
        b.groupby(["partner", "month"], as_index=False)
        .agg(
            last_update=("ingested_at", "max"),
            sources=("source_file", lambda s: "|".join(sorted(pd.Series(s).dropna().unique()))),
        )
    )

    gold = g.merge(lin, on=["partner", "month"], how="left")
    return gold[["partner", "month", "amount_total", "last_update", "sources"]]
