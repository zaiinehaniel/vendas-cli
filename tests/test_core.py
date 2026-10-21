from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import pytest
from auxiliares import VENDAS_EXEMPLO, venda

from vendas_cli.core import (
    agregar_por_mes,
    classificar_abc,
    classificar_xyz,
    escolher_mais_vendido,
    filtrar_por_periodo,
    gerar_relatorio,
    mes_de_pico,
    meses_entre,
)
from vendas_cli.formatacao import arredondar
from vendas_cli.models import Relatorio, ResumoProduto


def d(valor: str) -> Decimal:
    return Decimal(valor)


def produto(relatorio: Relatorio, nome: str) -> ResumoProduto:
    return next(p for p in relatorio.produtos if p.produto == nome)


# --- filtro por período ---------------------------------------------------------


def test_sem_filtro_mantem_todas() -> None:
    assert filtrar_por_periodo(VENDAS_EXEMPLO) == VENDAS_EXEMPLO


def test_filtro_so_inicio_inclusivo() -> None:
    vendas = filtrar_por_periodo(VENDAS_EXEMPLO, inicio=date(2025, 4, 1))

    assert [v.data for v in vendas] == [date(2025, 4, 1), date(2025, 4, 12), date(2025, 4, 18)]


def test_filtro_so_fim_inclusivo() -> None:
    vendas = filtrar_por_periodo(VENDAS_EXEMPLO, fim=date(2025, 1, 15))

    assert [v.data for v in vendas] == [date(2025, 1, 10), date(2025, 1, 15)]


def test_filtro_inicio_e_fim_inclusivos_nas_pontas() -> None:
    vendas = filtrar_por_periodo(VENDAS_EXEMPLO, date(2025, 2, 3), date(2025, 2, 20))

    assert [v.data for v in vendas] == [date(2025, 2, 3), date(2025, 2, 20)]


def test_filtro_sem_vendas_no_intervalo() -> None:
    assert filtrar_por_periodo(VENDAS_EXEMPLO, inicio=date(2026, 1, 1)) == ()


# --- relatório completo -------------------------------------------------------------


def test_totais_do_exemplo(relatorio_exemplo: Relatorio) -> None:
    assert relatorio_exemplo.valor_total == d("23357.80")
    assert relatorio_exemplo.quantidade_total == 53
    assert [p.produto for p in relatorio_exemplo.produtos] == ["Notebook", "Mouse", "Teclado"]


def test_total_por_produto(relatorio_exemplo: Relatorio) -> None:
    totais = {p.produto: (p.quantidade, p.valor_total) for p in relatorio_exemplo.produtos}

    assert totais == {
        "Notebook": (6, d("20750.00")),
        "Mouse": (42, d("2007.80")),
        "Teclado": (5, d("600.00")),
    }


def test_mais_vendido_e_maior_quantidade(relatorio_exemplo: Relatorio) -> None:
    assert relatorio_exemplo.mais_vendido is not None
    assert relatorio_exemplo.mais_vendido.produto == "Mouse"


def test_mais_vendido_empate_por_valor_e_depois_nome() -> None:
    relatorio = gerar_relatorio(
        [
            venda("2025-01-01", "Caro", 5, "10"),
            venda("2025-01-01", "Barato", 5, "1"),
            venda("2025-01-01", "Bravo", 5, "10"),
        ]
    )

    assert relatorio.mais_vendido is not None
    assert relatorio.mais_vendido.produto == "Bravo"
    assert escolher_mais_vendido([]) is None


def test_contagem_de_registros_com_filtro() -> None:
    relatorio = gerar_relatorio(
        VENDAS_EXEMPLO, inicio=date(2025, 1, 1), fim=date(2025, 3, 31), ignorados=2
    )

    assert (relatorio.validos, relatorio.ignorados, relatorio.no_periodo) == (8, 2, 5)
    assert (relatorio.inicio, relatorio.fim) == (date(2025, 1, 1), date(2025, 3, 31))
    assert relatorio.valor_total == d("11858.90")


def test_lista_vazia() -> None:
    relatorio = gerar_relatorio([])

    assert relatorio.produtos == ()
    assert relatorio.valor_total == 0
    assert relatorio.quantidade_total == 0
    assert relatorio.mais_vendido is None
    assert relatorio.vendas_por_mes == ()
    assert [(c.classe, c.produtos, c.valor_total) for c in relatorio.curva_abc] == [
        ("A", 0, 0),
        ("B", 0, 0),
        ("C", 0, 0),
    ]
    assert all(n == 0 for linha in relatorio.matriz_abc_xyz.values() for n in linha.values())


# --- curva ABC ----------------------------------------------------------------------


def test_classes_abc_do_exemplo(relatorio_exemplo: Relatorio) -> None:
    resumo = [
        (
            p.produto,
            arredondar(p.participacao),
            arredondar(p.participacao_acumulada),
            p.classe_abc,
        )
        for p in relatorio_exemplo.produtos
    ]

    assert resumo == [
        ("Notebook", d("88.84"), d("88.84"), "A"),
        ("Mouse", d("8.60"), d("97.43"), "B"),
        ("Teclado", d("2.57"), d("100.00"), "C"),
    ]


def test_produto_unico_e_classe_a() -> None:
    abc = classificar_abc({"Único": d("10")})

    assert abc["Único"] == (d("100"), d("100"), "A")


def test_produto_que_cruza_80_por_cento_ainda_e_a() -> None:
    abc = classificar_abc({"a": d("50"), "b": d("40"), "c": d("10")})

    # b começa em 50% (< 80) e termina em 90%: continua A. c começa em 90%: B.
    assert {nome: c.classe for nome, c in abc.items()} == {"a": "A", "b": "A", "c": "B"}


def test_limites_exatos_da_abc() -> None:
    abc = classificar_abc({"a": d("80"), "b": d("15"), "c": d("5")})

    # b começa exatamente em 80% (não é < 80): B. c começa exatamente em 95%: C.
    assert [c.classe for c in abc.values()] == ["A", "B", "C"]


def test_abc_logo_abaixo_dos_limites() -> None:
    abc = classificar_abc({"a": d("75"), "b": d("17"), "c": d("6"), "d": d("2")})

    # b começa em 75% (< 80): A. c começa em 92% (< 95): B. d começa em 98%: C.
    # Pega limites deslocados para baixo (ex.: 70 ou 90), que os exatos não pegam.
    assert {nome: c.classe for nome, c in abc.items()} == {"a": "A", "b": "A", "c": "B", "d": "C"}


def test_abc_ordena_por_valor_e_desempata_por_nome() -> None:
    abc = classificar_abc({"b": d("10"), "c": d("30"), "a": d("10")})

    assert list(abc) == ["c", "a", "b"]


def test_abc_com_valor_total_zero() -> None:
    abc = classificar_abc({"brinde": d("0"), "amostra": d("0")})

    assert all(c == (0, 0, "C") for c in abc.values())


def test_resumo_abc_mantem_classe_vazia() -> None:
    relatorio = gerar_relatorio(VENDAS_EXEMPLO, fim=date(2025, 3, 31))

    resumo = {c.classe: (c.produtos, arredondar(c.participacao)) for c in relatorio.curva_abc}
    assert resumo == {"A": (1, d("87.70")), "B": (1, d("12.30")), "C": (0, d("0.00"))}


# --- XYZ ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("serie", "cv", "classe"),
    [
        ([10, 12, 9, 11], "0.11", "X"),
        ([2, 1, 0, 3], "0.75", "Y"),
        ([0, 0, 0, 5], "1.73", "Z"),
        ([5, 5, 5], "0.00", "X"),
    ],
)
def test_classificar_xyz(serie: list[int], cv: str, classe: str) -> None:
    resultado = classificar_xyz(serie)

    assert resultado.cv is not None
    assert arredondar(resultado.cv) == d(cv)
    assert resultado.classe == classe


def test_xyz_limites_exatos() -> None:
    assert classificar_xyz([1, 3, 1, 3]) == (d("0.5"), "X")  # cv = 1 / 2
    assert classificar_xyz([0, 2, 0, 2]) == (d("1"), "Y")  # cv = 1 / 1
    assert classificar_xyz([0, 0, 3]).classe == "Z"  # cv ≈ 1,41


def test_xyz_logo_acima_dos_limites() -> None:
    # Pega limites deslocados para cima (ex.: 0,55 ou 1,05), que os exatos não pegam.
    assert classificar_xyz([1, 3, 5, 6]).classe == "Y"  # cv ≈ 0,51
    assert classificar_xyz([0, 0, 5, 6]).classe == "Z"  # cv ≈ 1,01


@pytest.mark.parametrize("serie", [[], [5], [5, 3], [0, 0, 0]])
def test_xyz_sem_dados_suficientes(serie: list[int]) -> None:
    assert classificar_xyz(serie) == (None, None)


def test_xyz_conta_zero_nos_meses_sem_venda_do_produto(relatorio_exemplo: Relatorio) -> None:
    # Teclado só vendeu em abril: série [0, 0, 0, 5]
    teclado = produto(relatorio_exemplo, "Teclado")

    assert teclado.classe_xyz == "Z"
    assert teclado.cv is not None and arredondar(teclado.cv) == d("1.73")


def test_periodo_curto_nao_calcula_xyz_e_loga(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="vendas_cli")

    relatorio = gerar_relatorio(VENDAS_EXEMPLO, inicio=date(2025, 3, 1))

    assert all(p.cv is None and p.classe_xyz is None for p in relatorio.produtos)
    assert all(n == 0 for linha in relatorio.matriz_abc_xyz.values() for n in linha.values())
    assert "período curto para XYZ: 2 mês(es), mínimo 3" in caplog.messages


def test_matriz_abc_xyz_do_exemplo(relatorio_exemplo: Relatorio) -> None:
    assert relatorio_exemplo.matriz_abc_xyz == {
        "A": {"X": 0, "Y": 1, "Z": 0},
        "B": {"X": 1, "Y": 0, "Z": 0},
        "C": {"X": 0, "Y": 0, "Z": 1},
    }


# --- preço praticado e pico -------------------------------------------------------------


def test_preco_medio_ponderado_min_e_max(relatorio_exemplo: Relatorio) -> None:
    notebook = produto(relatorio_exemplo, "Notebook")

    # (2 * 3500 + 1 * 3400 + 3 * 3450) / 6
    assert arredondar(notebook.preco_medio) == d("3458.33")
    assert (notebook.preco_min, notebook.preco_max) == (d("3400.00"), d("3500.00"))


def test_produto_com_preco_unico(relatorio_exemplo: Relatorio) -> None:
    teclado = produto(relatorio_exemplo, "Teclado")

    assert teclado.preco_medio == teclado.preco_min == teclado.preco_max == d("120.00")


def test_mes_de_pico(relatorio_exemplo: Relatorio) -> None:
    picos = {p.produto: p.mes_pico for p in relatorio_exemplo.produtos}

    assert picos == {"Notebook": "2025-04", "Mouse": "2025-02", "Teclado": "2025-04"}


def test_mes_de_pico_empate_fica_com_o_mais_antigo() -> None:
    assert mes_de_pico({"2025-03": 5, "2025-01": 5, "2025-02": 1}) == "2025-01"


# --- vendas por mês ---------------------------------------------------------------------


def test_vendas_por_mes_do_exemplo(relatorio_exemplo: Relatorio) -> None:
    meses = [
        (m.mes, m.quantidade, m.valor_total, m.variacao and arredondar(m.variacao))
        for m in relatorio_exemplo.vendas_por_mes
    ]

    assert meses == [
        ("2025-01", 12, d("7459.00"), None),
        ("2025-02", 13, d("3950.80"), d("-47.03")),
        ("2025-03", 9, d("449.10"), d("-88.63")),
        ("2025-04", 19, d("11498.90"), d("2460.43")),
    ]


def test_mes_sem_venda_no_meio_vira_zero_e_variacao_depois_e_nula() -> None:
    meses = agregar_por_mes([venda("2024-11-05", "A", 1, "10"), venda("2025-02-01", "A", 3, "10")])

    assert [(m.mes, m.quantidade, m.valor_total, m.variacao) for m in meses] == [
        ("2024-11", 1, d("10"), None),
        ("2024-12", 0, d("0"), d("-100")),
        ("2025-01", 0, d("0"), None),
        ("2025-02", 3, d("30"), None),
    ]


def test_vendas_por_mes_em_ordem_cronologica() -> None:
    meses = agregar_por_mes([venda("2025-03-01", "A", 1, "1"), venda("2025-01-01", "A", 1, "1")])

    assert [m.mes for m in meses] == ["2025-01", "2025-02", "2025-03"]


def test_vendas_por_mes_vazio() -> None:
    assert agregar_por_mes([]) == ()


def test_meses_entre_atravessa_o_ano() -> None:
    assert meses_entre(date(2024, 11, 30), date(2025, 2, 1)) == (
        "2024-11",
        "2024-12",
        "2025-01",
        "2025-02",
    )
