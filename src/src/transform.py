from typing import Dict
import re
import pandas as pd


def _clean_amount_to_float(x: object) -> float:
    """
    Convierte montos con formatos europeos/mixtos a float (EUR).
    Ejemplos válidos: "1.234,56", "1,234.56", "€1.234,56", "- 2.500", "2500", "2,5"
    Regla:
      - Si hay ',' y '.', asumimos ',' como separador decimal y eliminamos los '.'
      - Si solo hay ',', se interpreta como decimal y se reemplaza por '.'
      - Si solo hay '.', se deja como está
    """
    if pd.isna(x):
        return float("nan")
    s = str(x).strip()

    # quitar símbolo de euro y espacios interiores extras
    s = s.replace("€", "").replace("EUR", "").strip()
    s = re.sub(r"\s+", "", s)

    # mantener solo dígitos, signos, puntos y comas
    s = re.sub(r"[^0-9\-,\.]", "", s)

    if s.count(",") > 0 and s.count(".") > 0:
        # formato europeo típico: 1.234,56 -> 1234,56 -> 1234.56
        s = s.replace(".", "")
        s = s.replace(",", ".")
    elif s.count(",") > 0 and s.count(".") == 0:
        # solo coma -> decimal
        s = s.replace(",", ".")
    # si solo hay punto, no hacemos nada

    try:
        return float(s)
    except ValueError:
        return float("nan")


def normalize_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Normaliza un DataFrame a esquema canónico: date (datetime), partner (str), amount (float EUR).
    - Renombra columnas según `mapping` {col_origen: "date"/"partner"/"amount"}.
    - Parsea fechas a datetime (ISO, normalizadas a medianoche).
    - Normaliza amount (quita € y comas europeas) a float.
    - Limpia espacios en `partner`.

    Args:
        df: DataFrame original.
        mapping: Mapeo origen→canónico. Ej: {"fecha": "date", "cliente": "partner", "importe": "amount"}.

    Returns:
        DataFrame con columnas canónicas: ["date", "partner", "amount"].
    """
    # Renombrar según mapping
    out = df.rename(columns=mapping).copy()

    # Asegurar columnas canónicas existan (aunque vacías)
    for col in ("date", "partner", "amount"):
        if col not in out.columns:
            out[col] = pd.NA

    # Parseo de fecha a datetime (naive, normalizada a 00:00:00)
    out["date"] = pd.to_datetime(out["date"], errors="coerce", utc=False)
    # Normalizar a medianoche para consistencia (solo fecha)
    out["date"] = out["date"].dt.normalize()

    # Limpieza de partner
    out["partner"] = out["partner"].astype("string").str.strip()
    # Colapsar espacios múltiples
    out["partner"] = out["partner"].str.replace(r"\s+", " ", regex=True)

    # Normalización de amount a float EUR
    out["amount"] = out["amount"].apply(_clean_amount_to_float)

    # Devolver solo canónicas
    return out[["date", "partner", "amount"]]


def to_silver(bronze: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega amount por partner y mes. La columna `month` se entrega como timestamp
    (inicio de mes), derivado de un Period('M').

    Args:
        bronze: DataFrame canónico/bronze con columnas ["date", "partner", "amount"].

    Returns:
        DataFrame con columnas: ["partner", "month", "amount"].
    """
    df = bronze.copy()
    # Asegurar tipos esperados
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=False)
    df["partner"] = df["partner"].astype("string")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Mes como Period mensual y luego a timestamp (inicio de mes)
    month_period = df["date"].dt.to_period("M")
    month_ts = month_period.dt.to_timestamp(how="start")

    grouped = (
        df.assign(month=month_ts)
        .groupby(["partner", "month"], dropna=True, as_index=False, observed=True)["amount"]
        .sum(min_count=1)  # si todo es NaN, queda NaN
    )

    # Orden estándar de columnas
    return grouped[["partner", "month", "amount"]]
