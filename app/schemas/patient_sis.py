"""Patient master data, using SIS trama 2025 contract lengths (not paper TDI codes)."""

from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


class PatientSisFields(BaseModel):
    # Strings are intentional: leading zeroes are significant for ETL and printing.
    sis_diresa: Annotated[str, Field(pattern=r"^[A-Z0-9]{3}$")] | None = None
    sis_tipo: Annotated[str, Field(pattern=r"^[A-Z0-9]{1,2}$")] | None = None
    sis_numero: Annotated[str, Field(pattern=r"^[0-9]{8,9}$")] | None = None
    sis_secuencia: Annotated[str, Field(pattern=r"^[0-9]{1,2}$")] | None = None
    etnia_codigo: Annotated[str, Field(pattern=r"^[0-9]{1,2}$")] | None = None

    @field_validator("sis_diresa", "sis_tipo", "sis_numero", "sis_secuencia", "etnia_codigo", mode="before")
    @classmethod
    def normalize_sis(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return value.strip().upper() or None

    @field_validator("etnia_codigo")
    @classmethod
    def canonical_ethnicity_code(cls, value: str | None) -> str | None:
        return str(int(value)) if value is not None else None


def affiliation_problem(values: dict[str, Any]) -> str | None:
    # DISA is conditional in the electronic contract. Paper warns if it is missing.
    if any(values.get(key) for key in ("sis_diresa", "sis_tipo", "sis_numero", "sis_secuencia")):
        if not values.get("sis_tipo") or not values.get("sis_numero"):
            return "Complete tipo/formato y número de afiliación SIS juntos, o deje toda la afiliación vacía."
    return None
