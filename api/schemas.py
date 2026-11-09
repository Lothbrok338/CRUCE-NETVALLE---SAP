from typing import List, Optional

from pydantic import BaseModel


class ArchivoClasificado(BaseModel):
    nombre: str
    tipo: str                     # NETVALLE (archivo CRUCE) | SAP | OTROS
    cuentas: List[str] = []       # para SAP: "IVA" y/o "IT" detectados
    detalle: Optional[str] = None


class Clasificacion(BaseModel):
    valido: bool
    archivos: List[ArchivoClasificado]
    problemas: List[str]


class JobCreado(BaseModel):
    id: str
    estado: str
    clasificacion: Clasificacion


class Tarjeta(BaseModel):
    control: str
    resultado: str
    cantidad: Optional[float] = None
    total_facturas_bs: Optional[float] = None
    dato_clave: Optional[str] = None
    que_significa: Optional[str] = None
    que_hacer: Optional[str] = None


class Resumen(BaseModel):
    tarjetas: List[Tarjeta]
    observaciones_total: int


class EstadoControl(BaseModel):
    id: str
    estado: str                   # en cola | procesando | listo | error
    progreso: int                 # 0-100 (aproximado por estado)
    creado: float
    expira: float
    resumen: Optional[Resumen] = None
    error: Optional[str] = None


class PaginaObservaciones(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    paginas: int
    columnas: List[str]
    filas: List[dict]
    filtros: dict
