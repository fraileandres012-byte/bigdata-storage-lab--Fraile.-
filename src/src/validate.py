from typing import List
import pandas as pd


def basic_checks(df: pd.DataFrame) -> List[str]:
    """
    Reglas mínimas:
      - Columnas canónicas presentes: date, partner, amount
      - date convertible a datetime
      - amount numérico y >= 0
    Devuelve lista de mensajes de error (vacía si pasa).
    """
    errors: List[str] = []

    expected = {"date", "partner", "amount"}
    missing = expected.difference(df.columns)
    if missing:
        errors.append(f"Faltan columnas canónicas: {', '.join(sorted(missing))}")
        return errors

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

    return errors
