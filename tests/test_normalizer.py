from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from vendas_cli.normalizer import normalizar_data, normalizar_preco, normalizar_quantidade


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("2025-01-15", date(2025, 1, 15)),
        (" 2025-12-31 ", date(2025, 12, 31)),
        ("2024-02-29", date(2024, 2, 29)),
    ],
)
def test_normalizar_data_valida(texto: str, esperado: date) -> None:
    assert normalizar_data(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "mensagem"),
    [
        ("2025-1-5", "data inválida"),
        ("15/01/2025", "data inválida"),
        ("20250115", "data inválida"),
        ("", "data inválida"),
        ("2025-02-30", "data inexistente"),
        ("2025-13-01", "data inexistente"),
        ("2025-02-29", "data inexistente"),
    ],
)
def test_normalizar_data_invalida(texto: str, mensagem: str) -> None:
    with pytest.raises(ValueError, match=mensagem):
        normalizar_data(texto)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("5", 5), (" 7 ", 7), ("0", 0), ("-3", -3), ("1000", 1000)],
)
def test_normalizar_quantidade_valida(texto: str, esperado: int) -> None:
    assert normalizar_quantidade(texto) == esperado


@pytest.mark.parametrize("texto", ["+5", "2.0", "1_000", "1.000", "abc", ""])
def test_normalizar_quantidade_invalida(texto: str) -> None:
    with pytest.raises(ValueError, match="quantidade inválida"):
        normalizar_quantidade(texto)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("45.90", "45.90"),
        ("45", "45"),
        ("0", "0"),
        ("45,90", "45.90"),
        (" 7,5 ", "7.5"),
        ("1.234,56", "1234.56"),
        ("12.345.678,9", "12345678.9"),
        ("1.234", "1.234"),
        ("-1,5", "-1.5"),
    ],
)
def test_normalizar_preco_valido(texto: str, esperado: str) -> None:
    assert normalizar_preco(texto) == Decimal(esperado)


def test_normalizar_preco_sem_virgula_usa_ponto_como_decimal() -> None:
    # Caso ambíguo documentado no SPEC: sem vírgula, o ponto é decimal.
    assert normalizar_preco("1.234") == Decimal("1.234")


@pytest.mark.parametrize(
    "texto",
    ["1,234.56", "1.23,4", "1e3", "NaN", "Infinity", "1_000", "R$ 10", "45,", ".5", "", "abc"],
)
def test_normalizar_preco_invalido(texto: str) -> None:
    with pytest.raises(ValueError, match="preço inválido"):
        normalizar_preco(texto)
