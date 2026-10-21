"""Conversão de campos de texto do CSV (e da CLI) em tipos Python.

Cada função recebe o texto cru e devolve o valor tipado, ou levanta ``ValueError``
com uma mensagem pronta para log. Regras de negócio (ex.: quantidade > 0) ficam
no ``parser``.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

_DATA = re.compile(r"\d{4}-\d{2}-\d{2}")
_INTEIRO = re.compile(r"-?\d+")
_NUMERO_PONTO = re.compile(r"-?\d+(\.\d+)?")
_NUMERO_PT_BR = re.compile(r"-?(\d{1,3}(\.\d{3})+|\d+),\d+")


def normalizar_data(texto: str) -> date:
    """Converte ``AAAA-MM-DD`` em ``date``."""
    texto = texto.strip()
    if not _DATA.fullmatch(texto):
        raise ValueError(f"data inválida '{texto}' (esperado AAAA-MM-DD)")
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise ValueError(f"data inexistente '{texto}'") from None


def normalizar_quantidade(texto: str) -> int:
    """Converte inteiro em texto (só dígitos, sinal opcional) em ``int``."""
    texto = texto.strip()
    if not _INTEIRO.fullmatch(texto):
        raise ValueError(f"quantidade inválida '{texto}' (esperado número inteiro)")
    return int(texto)


def normalizar_preco(texto: str) -> Decimal:
    """Converte preço em ``Decimal``, aceitando ``45.90`` ou pt-BR ``45,90`` / ``1.234,56``.

    Com vírgula, o texto é lido como pt-BR (ponto = milhar). Sem vírgula, o ponto
    é o separador decimal, então ``1.234`` vale 1,234.
    """
    texto = texto.strip()
    if _NUMERO_PT_BR.fullmatch(texto):
        return Decimal(texto.replace(".", "").replace(",", "."))
    if _NUMERO_PONTO.fullmatch(texto):
        return Decimal(texto)
    raise ValueError(f"preço inválido '{texto}' (use 45.90 ou \"45,90\")")
