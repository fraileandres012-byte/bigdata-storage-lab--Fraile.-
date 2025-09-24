# src/validate.py
from typing import List, Optional
import pandas as pd


def basic_checks(
    df: pd.DataFrame,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    check_duplicates: bool = True,
) -> List[str]:
    """
    Valida requisitos mínimos y reglas extra:
      - Columnas canónicas presentes
      - date convertible a datetime
      - amount numérico y >= 0
      - (opcional) date dentro de [min_date, max_date]
      - (opcional) duplicados por clave natural (date, partner, amount)
    """
    errors: List[str] = []

    expected = {"date", "partner", "amount"}
    missing = expected.difference(df.columns)
    if missing:
        errors.append(f"Faltan columnas canónicas: {', '.join(sorted(missing))}")
        return errors

    # Tipos básicos
    date_parsed = pd.to_datetime(df["date"], errors="coerce", utc=False)
    nat_count = date_parsed.isna().sum()
    if nat_count > 0:
        errors.append(f"`date` no parseable en {nat_count} filas")

    amount_num = pd.to_numeric(df["amount"], errors="coerce")
    non_numeric = amount_num.isna().sum()
    if non_numeric > 0:
        errors.append(f"`amount` no numérico en {non_numeric} filas")

    negative_count = (amount_num.dropna() < 0).sum()
    if negative_count > 0:
        errors.append(f"`amount` negativo en {negative_count} filas")

    # Rango de fechas
    if min_date:
        min_d = pd.to_datetime(min_date)
        below = (date_parsed < min_d).sum()
        if below > 0:
            errors.append(f"Fechas < {min_d.date().isoformat()}: {below}")
    if max_date:
        max_d = pd.to_datetime(max_date)
        above = (date_parsed > max_d).sum()
        if above > 0:
            errors.append(f"Fechas > {max_d.date().isoformat()}: {above}")

    # Duplicados por clave natural
    if check_duplicates:
        dup_count = df.duplicated(subset=["date", "partner", "amount"]).sum()
        if dup_count > 0:
            errors.append(f"Duplicados por (date, partner, amount): {dup_count}")

    return errors
