"""Dados compartilhados pelos testes: exemplo da seção 2 e saídas da seção 4 do SPEC."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

from vendas_cli.models import Venda

CriarCSV = Callable[..., Path]

CSV_EXEMPLO = """\
data,produto,quantidade,preco_unitario
2025-01-10,Notebook,2,3500.00
2025-01-15,Mouse,10,45.90
2025-02-03,Mouse,12,45.90
2025-02-20,Notebook,1,3400.00
2025-03-05,Mouse,9,49.90
2025-04-01,Teclado,5,120.00
2025-04-12,Notebook,3,3450.00
2025-04-18,Mouse,11,49.90
"""


def venda(data: str, produto: str, quantidade: int, preco: str) -> Venda:
    return Venda(date.fromisoformat(data), produto, quantidade, Decimal(preco))


VENDAS_EXEMPLO = (
    venda("2025-01-10", "Notebook", 2, "3500.00"),
    venda("2025-01-15", "Mouse", 10, "45.90"),
    venda("2025-02-03", "Mouse", 12, "45.90"),
    venda("2025-02-20", "Notebook", 1, "3400.00"),
    venda("2025-03-05", "Mouse", 9, "49.90"),
    venda("2025-04-01", "Teclado", 5, "120.00"),
    venda("2025-04-12", "Notebook", 3, "3450.00"),
    venda("2025-04-18", "Mouse", 11, "49.90"),
)

TEXTO_EXEMPLO = """\
Relatório de vendas
Período: início a fim
Registros: 8 válidos, 0 ignorados, 8 no período

Produtos (curva ABC)
Produto   Quantidade  Valor (R$)  Part. %  Acum. %  ABC
--------  ----------  ----------  -------  -------  ---
Notebook           6   20.750,00    88,84    88,84  A
Mouse             42    2.007,80     8,60    97,43  B
Teclado            5      600,00     2,57   100,00  C
--------  ----------  ----------  -------  -------  ---
TOTAL             53   23.357,80   100,00

Produto mais vendido: Mouse (42 unidades)

Curva ABC: A 1 produto (88,84%) · B 1 produto (8,60%) · C 1 produto (2,57%)

Demanda e preço
Produto   Preço médio  Preço mín  Preço máx    CV  XYZ  Pico
--------  -----------  ---------  ---------  ----  ---  -------
Notebook     3.458,33   3.400,00   3.500,00  0,75  Y    2025-04
Mouse           47,80      45,90      49,90  0,11  X    2025-02
Teclado        120,00     120,00     120,00  1,73  Z    2025-04

Matriz ABC-XYZ (produtos)
ABC  X  Y  Z
---  -  -  -
A    0  1  0
B    1  0  0
C    0  0  1

Vendas por mês
Mês      Quantidade  Valor (R$)  Variação %
-------  ----------  ----------  ----------
2025-01          12    7.459,00           -
2025-02          13    3.950,80      -47,03
2025-03           9      449,10      -88,63
2025-04          19   11.498,90    2.460,43"""

JSON_EXEMPLO = {
    "periodo": {"inicio": None, "fim": None},
    "registros": {"validos": 8, "ignorados": 0, "no_periodo": 8},
    "produtos": [
        {
            "produto": "Notebook",
            "quantidade": 6,
            "valor_total": "20750.00",
            "participacao": "88.84",
            "participacao_acumulada": "88.84",
            "classe_abc": "A",
            "preco_medio": "3458.33",
            "preco_min": "3400.00",
            "preco_max": "3500.00",
            "cv": "0.75",
            "classe_xyz": "Y",
            "mes_pico": "2025-04",
        },
        {
            "produto": "Mouse",
            "quantidade": 42,
            "valor_total": "2007.80",
            "participacao": "8.60",
            "participacao_acumulada": "97.43",
            "classe_abc": "B",
            "preco_medio": "47.80",
            "preco_min": "45.90",
            "preco_max": "49.90",
            "cv": "0.11",
            "classe_xyz": "X",
            "mes_pico": "2025-02",
        },
        {
            "produto": "Teclado",
            "quantidade": 5,
            "valor_total": "600.00",
            "participacao": "2.57",
            "participacao_acumulada": "100.00",
            "classe_abc": "C",
            "preco_medio": "120.00",
            "preco_min": "120.00",
            "preco_max": "120.00",
            "cv": "1.73",
            "classe_xyz": "Z",
            "mes_pico": "2025-04",
        },
    ],
    "valor_total": "23357.80",
    "mais_vendido": {"produto": "Mouse", "quantidade": 42},
    "curva_abc": {
        "A": {"produtos": 1, "valor_total": "20750.00", "participacao": "88.84"},
        "B": {"produtos": 1, "valor_total": "2007.80", "participacao": "8.60"},
        "C": {"produtos": 1, "valor_total": "600.00", "participacao": "2.57"},
    },
    "matriz_abc_xyz": {
        "A": {"X": 0, "Y": 1, "Z": 0},
        "B": {"X": 1, "Y": 0, "Z": 0},
        "C": {"X": 0, "Y": 0, "Z": 1},
    },
    "vendas_por_mes": [
        {"mes": "2025-01", "quantidade": 12, "valor_total": "7459.00", "variacao": None},
        {"mes": "2025-02", "quantidade": 13, "valor_total": "3950.80", "variacao": "-47.03"},
        {"mes": "2025-03", "quantidade": 9, "valor_total": "449.10", "variacao": "-88.63"},
        {"mes": "2025-04", "quantidade": 19, "valor_total": "11498.90", "variacao": "2460.43"},
    ],
}
