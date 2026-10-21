"""Formatação de números, períodos e plurais em pt-BR, comum ao texto e ao HTML."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

_CENTAVOS = Decimal("0.01")


def arredondar(valor: Decimal) -> Decimal:
    """Duas casas, ``ROUND_HALF_UP``, sem ``-0.00``."""
    arredondado = valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
    return abs(arredondado) if arredondado.is_zero() else arredondado


def formatar_decimal(valor: Decimal) -> str:
    """``Decimal`` em pt-BR: ``20750.5`` → ``20.750,50``."""
    return f"{arredondar(valor):,.2f}".translate(str.maketrans(",.", ".,"))


def formatar_inteiro(valor: int) -> str:
    """Inteiro em pt-BR: ``1234`` → ``1.234``."""
    return f"{valor:,}".replace(",", ".")


def formatar_periodo(inicio: date | None, fim: date | None) -> str:
    texto_inicio = inicio.isoformat() if inicio else "início"
    texto_fim = fim.isoformat() if fim else "fim"
    return f"{texto_inicio} a {texto_fim}"


def plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{formatar_inteiro(quantidade)} {singular if quantidade == 1 else plural}"
