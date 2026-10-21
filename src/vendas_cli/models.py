"""Estruturas de dados do relatório de vendas."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

ClasseABC = Literal["A", "B", "C"]
ClasseXYZ = Literal["X", "Y", "Z"]


@dataclass(frozen=True)
class Venda:
    """Uma linha válida do CSV."""

    data: date
    produto: str
    quantidade: int
    preco_unitario: Decimal

    @property
    def valor(self) -> Decimal:
        return self.preco_unitario * self.quantidade


@dataclass(frozen=True)
class ResumoProduto:
    """Agregado de um produto no período, com classificação ABC/XYZ."""

    produto: str
    quantidade: int
    valor_total: Decimal
    participacao: Decimal
    participacao_acumulada: Decimal
    classe_abc: ClasseABC
    preco_medio: Decimal
    preco_min: Decimal
    preco_max: Decimal
    cv: Decimal | None
    classe_xyz: ClasseXYZ | None
    mes_pico: str


@dataclass(frozen=True)
class ResumoClasse:
    """Totais de uma classe da curva ABC."""

    classe: ClasseABC
    produtos: int
    valor_total: Decimal
    participacao: Decimal


@dataclass(frozen=True)
class ResumoMes:
    """Totais de um mês (``AAAA-MM``) e variação de valor sobre o mês anterior."""

    mes: str
    quantidade: int
    valor_total: Decimal
    variacao: Decimal | None


@dataclass(frozen=True)
class Relatorio:
    """Resultado completo, pronto para ser formatado."""

    inicio: date | None
    fim: date | None
    validos: int
    ignorados: int
    no_periodo: int
    produtos: tuple[ResumoProduto, ...]
    valor_total: Decimal
    quantidade_total: int
    mais_vendido: ResumoProduto | None
    curva_abc: tuple[ResumoClasse, ...]
    matriz_abc_xyz: Mapping[ClasseABC, Mapping[ClasseXYZ, int]]
    vendas_por_mes: tuple[ResumoMes, ...]
