"""Dimensionamento de Pontes de Concreto Rodoviárias - ABNT NBR 7187:2021 e NBR 7188:2013.

Biblioteca analítica e ferramenta CLI com zero dependências externas e 100% aritmética racional.
Desenvolvido por Lofrano Tecnologia.
"""

from .models import (
    ClasseTremTipo,
    TipoSecao,
    ClasseConcreto,
    AcoArmadura,
    ParametrosVao,
    GeometriaSecao,
    AparelhoApoio,
    ResultadoDimensionamentoPonte,
)
from .calculator import calcular_ponte_rodoviaria

__version__ = "1.0.0"
__author__ = "Martin Lofrano de Oliveira (Lofrano Tecnologia)"

__all__ = [
    "ClasseTremTipo",
    "TipoSecao",
    "ClasseConcreto",
    "AcoArmadura",
    "ParametrosVao",
    "GeometriaSecao",
    "AparelhoApoio",
    "ResultadoDimensionamentoPonte",
    "calcular_ponte_rodoviaria",
]
