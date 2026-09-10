"""DTOs del módulo de configuración de grupos etarios.

Los meses completos son la unidad canónica para reglas clínicas: permiten
modelar correctamente rangos de menores de un año y límites como 11 años y
11 meses.  Los DTOs también aceptan y devuelven una representación amigable
en años y meses para las pantallas administrativas.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgeBoundaryInput(BaseModel):
    """Límite de edad legible para personas, sin aproximar meses."""

    anios: int = Field(ge=0, le=5461, description="Años completos.")
    meses: int = Field(
        default=0,
        ge=0,
        le=11,
        description="Meses adicionales después de los años completos (0 a 11).",
    )

    @property
    def total_meses(self) -> int:
        return self.anios * 12 + self.meses


class AgeBoundaryResponse(BaseModel):
    """Límite de edad exacto, listo para ser mostrado por el frontend."""

    anios: int
    meses: int


class AgeGroupRangeInput(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    edad_minima_meses: int | None = Field(
        default=None,
        ge=0,
        le=65535,
        description=(
            "Unidad canónica para la regla clínica. Se conserva por "
            "compatibilidad; alternativamente use edad_minima."
        ),
    )
    edad_maxima_meses: int | None = Field(
        default=None,
        ge=0,
        le=65535,
        description=(
            "Unidad canónica para la regla clínica. Se conserva por "
            "compatibilidad; alternativamente use edad_maxima."
        ),
    )
    edad_minima: AgeBoundaryInput | None = Field(
        default=None,
        description="Forma legible equivalente a edad_minima_meses.",
    )
    edad_maxima: AgeBoundaryInput | None = Field(
        default=None,
        description=(
            "Forma legible equivalente a edad_maxima_meses. Use null u omita "
            "el campo para un rango sin límite superior."
        ),
    )
    activo: bool = True

    @model_validator(mode="after")
    def validate_local_range(self) -> "AgeGroupRangeInput":
        self.edad_minima_meses = self._resolve_months(
            months=self.edad_minima_meses,
            boundary=self.edad_minima,
            field_name="edad_minima",
        )
        self.edad_maxima_meses = self._resolve_months(
            months=self.edad_maxima_meses,
            boundary=self.edad_maxima,
            field_name="edad_maxima",
        )
        if self.activo and self.edad_minima_meses is None:
            raise ValueError("Todo grupo etario activo requiere edad_minima o edad_minima_meses")
        if (
            self.edad_minima_meses is not None
            and self.edad_maxima_meses is not None
            and self.edad_maxima_meses < self.edad_minima_meses
        ):
            raise ValueError("edad_maxima_meses debe ser mayor o igual al mínimo")
        return self

    @staticmethod
    def _resolve_months(
        *,
        months: int | None,
        boundary: AgeBoundaryInput | None,
        field_name: str,
    ) -> int | None:
        """Normalize either public representation to the persisted unit."""

        if boundary is None:
            return months
        calculated_months = boundary.total_meses
        if months is not None and months != calculated_months:
            raise ValueError(
                f"{field_name}_meses no coincide con {field_name} en años y meses"
            )
        return calculated_months


class AgeGroupConfigurationInput(BaseModel):
    grupos: list[AgeGroupRangeInput] = Field(min_length=1)
    exigir_cobertura_continua: bool = False

    @model_validator(mode="after")
    def no_duplicate_codes(self) -> "AgeGroupConfigurationInput":
        codes = [group.codigo for group in self.grupos]
        if len(codes) != len(set(codes)):
            raise ValueError("No se puede configurar dos veces el mismo grupo etario")
        return self


class AgeGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    # Los campos *_meses permanecen para consumidores existentes y para que
    # cualquier integración pueda conservar el valor clínico exacto.
    edad_minima_meses: int | None
    edad_maxima_meses: int | None
    edad_minima: AgeBoundaryResponse | None
    edad_maxima: AgeBoundaryResponse | None
    rango_edad_legible: str
    activo: bool
