from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from vendas_cli.formatacao import (
    arredondar,
    formatar_decimal,
    formatar_inteiro,
    formatar_periodo,
    plural,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("0", "0,00"),
        ("5", "5,00"),
        ("45.9", "45,90"),
        ("1234.5", "1.234,50"),
        ("1234567.891", "1.234.567,89"),
        ("-47.025", "-47,03"),
        ("2460.425", "2.460,43"),
        ("-0.001", "0,00"),
    ],
)
def test_formatar_decimal(valor: str, esperado: str) -> None:
    assert formatar_decimal(Decimal(valor)) == esperado


def test_arredondar_usa_round_half_up() -> None:
    # ROUND_HALF_EVEN (padrão do Decimal) daria 0.12
    assert arredondar(Decimal("0.125")) == Decimal("0.13")


def test_arredondar_nao_produz_zero_negativo() -> None:
    assert str(arredondar(Decimal("-0.004"))) == "0.00"


@pytest.mark.parametrize(("valor", "esperado"), [(0, "0"), (999, "999"), (1234567, "1.234.567")])
def test_formatar_inteiro(valor: int, esperado: str) -> None:
    assert formatar_inteiro(valor) == esperado


@pytest.mark.parametrize(
    ("inicio", "fim", "esperado"),
    [
        (None, None, "início a fim"),
        (date(2025, 1, 1), None, "2025-01-01 a fim"),
        (None, date(2025, 3, 31), "início a 2025-03-31"),
        (date(2025, 1, 1), date(2025, 3, 31), "2025-01-01 a 2025-03-31"),
    ],
)
def test_formatar_periodo(inicio: date | None, fim: date | None, esperado: str) -> None:
    assert formatar_periodo(inicio, fim) == esperado


@pytest.mark.parametrize(
    ("quantidade", "esperado"),
    [(0, "0 produtos"), (1, "1 produto"), (2, "2 produtos"), (1500, "1.500 produtos")],
)
def test_plural(quantidade: int, esperado: str) -> None:
    assert plural(quantidade, "produto", "produtos") == esperado
