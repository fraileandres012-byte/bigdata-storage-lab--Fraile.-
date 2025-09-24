from typing import List
import pandas as pd


def tag_lineage(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Anota linaje de archivo y timestamp de ingesta.
    - source_file: nombre lógico del origen (p. ej. nombre de archivo)
    - ingested_at: timestamp ISO 8601 en UTC (+00:00)

    Args:
        df: DataFrame de entrada (cualquier esquema).
        source_name: nombre del archivo/fuente.

    Returns:
        DataFrame con columnas añadidas: source_file, ingested_at.
    """
    out = df.copy()
    out["source_file"] = str(source_name)
    # ISO 8601 con zona UTC
    out["ingested_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    return out


def concat_bronze(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatena múltiples DataFrames ya enriquecidos con linaje,
    y los ajusta al esquema bronze:
      [date, partner, amount, source_file, ingested_at]

    - Si faltan columnas, se crean vacías.
    - Se fuerza tipo de `date` a datetime y `amount` a float.
    - Se descartan columnas no incluidas en el esquema.

    Args:
        frames: lista de DataFrames compatibles.

    Returns:
        DataFrame consolidado (bronze).
    """
    schema_cols = ["date", "partner", "amount", "source_file", "ingested_at"]

    if not frames:
        # DataFrame vacío con el esquema correcto
        return pd.DataFrame(columns=schema_cols)

    df = pd.concat(frames, ignore_index=True, sort=False)

    # Asegurar todas las columnas del esquema
    for col in schema_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # Coerciones suaves de tipo
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=False)
    df["partner"] = df["partner"].astype("string")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Mantener solo columnas del esquema y ordenarlas
    bronze = df[schema_cols].copy()

    return bronze
