from typing import List
import pandas as pd


def basic_checks(df: pd.DataFrame) -> List[str]:
    """
    Valida requisitos mínimos del esquema canónico.
    Reglas:
      - Columnas canónicas presentes: date, partner, amount
      - amount numérico y >= 0 (no NaN para filas válidas)
      - date de tipo datetime convertible (sin NaT para filas válidas)

    Devuelve:
      Lista de mensajes de error (vacía si todo OK).
    """
    errors: List[str] = []

    expected = {"date", "partner", "amount"}
    missing = expected.difference(df.columns)
    if missing:
        errors.append(f"Faltan columnas canónicas: {', '.join(sorted(missing))}")

    # Si faltan columnas, no se puede continuar con chequeos siguientes de forma fiable
    if missing:
        return errors

    # Chequeo de tipo/parseo de fecha
    date_parsed = pd.to_datetime(df["date"], errors="coerce", utc=False)
    nat_count = date_parsed.isna().sum()
    if nat_count > 0:
        errors.append(f"`date` contiene valores no parseables a datetime: {nat_count}")

    # Chequeo amount numérico
    amount_num = pd.to_numeric(df["amount"], errors="coerce")
    non_numeric = amount_num.isna().sum()
    if non_numeric > 0:
        errors.append(f"`amount` contiene valores no numéricos: {non_numeric}")

    # Chequeo amount >= 0 (solo en filas numéricas)
    negative_count = (amount_num.dropna() < 0).sum()
    if negative_count > 0:
        errors.append(f"`amount` contiene valores negativos: {negative_count}")

    return errors
