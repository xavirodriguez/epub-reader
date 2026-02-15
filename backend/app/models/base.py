"""
Clases base para modelos de datos.
"""
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Esquema base con configuración común"""
    model_config = ConfigDict(from_attributes=True)
