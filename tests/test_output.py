from __future__ import annotations

import json
from datetime import date

from auxiliares import JSON_EXEMPLO, TEXTO_EXEMPLO, VENDAS_EXEMPLO, venda

from vendas_cli.core import gerar_relatorio
from vendas_cli.models import Relatorio
from vendas_cli.output import FORMATOS, formatar, montar_tabela, relatorio_para_dict


def test_formatos_disponiveis() -> None:
    assert FORMATOS == ("text", "json", "html")


# --- texto ------------------------------------------------------------------------


def test_texto_do_exemplo_bate_com_o_spec(relatorio_exemplo: Relatorio) -> None:
    assert formatar(relatorio_exemplo, "text") == TEXTO_EXEMPLO


def test_texto_com_filtro_mostra_periodo_e_contagem() -> None:
    relatorio = gerar_relatorio(VENDAS_EXEMPLO, inicio=date(2025, 1, 1), fim=date(2025, 3, 31))

    texto = formatar(relatorio, "text")

    assert "Período: 2025-01-01 a 2025-03-31" in texto
    assert "Registros: 8 válidos, 0 ignorados, 5 no período" in texto
    assert "C 0 produtos (0,00%)" in texto


def test_texto_mostra_traco_quando_nao_ha_xyz_nem_variacao() -> None:
    relatorio = gerar_relatorio(VENDAS_EXEMPLO, inicio=date(2025, 4, 1))

    linhas = formatar(relatorio, "text").splitlines()

    assert "Notebook     3.450,00   3.450,00   3.450,00   -  -    2025-04" in linhas
    assert "2025-04          19   11.498,90           -" in linhas


def test_texto_singular_para_uma_unidade() -> None:
    relatorio = gerar_relatorio([venda("2025-01-01", "Mouse", 1, "45.90")])

    assert "Produto mais vendido: Mouse (1 unidade)" in formatar(relatorio, "text")


def test_texto_sem_vendas() -> None:
    relatorio = gerar_relatorio(VENDAS_EXEMPLO, inicio=date(2026, 1, 1))

    assert formatar(relatorio, "text") == (
        "Relatório de vendas\n"
        "Período: 2026-01-01 a fim\n"
        "Registros: 8 válidos, 0 ignorados, 0 no período\n"
        "\n"
        "Nenhuma venda no período."
    )


def test_montar_tabela_alinha_pela_maior_largura() -> None:
    linhas = montar_tabela(
        ["Nome", "Qtd"], [["a", "1"], ["bbbbbb", "100"]], ["<", ">"], total=["T", "101"]
    )

    assert linhas == [
        "Nome    Qtd",
        "------  ---",
        "a         1",
        "bbbbbb  100",
        "------  ---",
        "T       101",
    ]


# --- JSON ---------------------------------------------------------------------------


def test_json_do_exemplo_bate_com_o_spec(relatorio_exemplo: Relatorio) -> None:
    assert json.loads(formatar(relatorio_exemplo, "json")) == JSON_EXEMPLO


def test_json_mantem_acentos_sem_escape() -> None:
    relatorio = gerar_relatorio([venda("2025-01-01", "Café", 1, "5.00")])

    assert '"Café"' in formatar(relatorio, "json")


def test_json_com_filtro() -> None:
    relatorio = gerar_relatorio(VENDAS_EXEMPLO, inicio=date(2025, 1, 1), fim=date(2025, 3, 31))

    dados = relatorio_para_dict(relatorio)

    assert dados["periodo"] == {"inicio": "2025-01-01", "fim": "2025-03-31"}
    assert dados["registros"] == {"validos": 8, "ignorados": 0, "no_periodo": 5}
    assert dados["valor_total"] == "11858.90"


def test_json_sem_vendas() -> None:
    dados = json.loads(formatar(gerar_relatorio([]), "json"))

    assert dados["produtos"] == []
    assert dados["valor_total"] == "0.00"
    assert dados["mais_vendido"] is None
    assert dados["vendas_por_mes"] == []
    assert dados["curva_abc"]["A"] == {"produtos": 0, "valor_total": "0.00", "participacao": "0.00"}
    assert dados["matriz_abc_xyz"]["C"] == {"X": 0, "Y": 0, "Z": 0}


# --- despacho para HTML -------------------------------------------------------------------


def test_formatar_html(relatorio_exemplo: Relatorio) -> None:
    assert formatar(relatorio_exemplo, "html").startswith("<!doctype html>")
