from typing import List
import pandas as pd


def tag_lineage(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Añade linaje:
      - source_file: nombre lógico del origen (archivo)
      - ingested_at: timestamp ISO 8601 en UTC
    """
    out = df.copy()
    out["source_file"] = str(source_name)
    out["ingested_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    return out


def concat_bronze(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatena y ajusta al esquema bronze:
      [date, partner, amount, source_file, ingested_at]
    """
    schema = ["date", "partner", "amount", "source_file", "ingested_at"]

    if not frames:
        return pd.DataFrame(columns=schema)

    df = pd.concat(frames, ignore_index=True, sort=False)

    for col in schema:
        if col not in df.columns:
            df[col] = pd.NA

    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=False)
    df["partner"] = df["partner"].astype("string")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    return df[schema].copy()
