"""Formatação do relatório em texto (tabelas) e JSON; despacha o HTML.

Funções puras: recebem ``Relatorio`` e devolvem ``str``.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from vendas_cli.core import CLASSES_XYZ
from vendas_cli.formatacao import (
    arredondar,
    formatar_decimal,
    formatar_inteiro,
    formatar_periodo,
    plural,
)
from vendas_cli.models import Relatorio, ResumoProduto
from vendas_cli.relatorio_html import gerar_html

Formato = Literal["text", "json", "html"]
FORMATOS: tuple[Formato, ...] = ("text", "json", "html")

VAZIO = "-"


def formatar(relatorio: Relatorio, formato: Formato, gerado_em: datetime | None = None) -> str:
    """Formata o relatório no formato pedido.

    ``gerado_em`` só é usado no HTML; sem ele, vale o horário atual.
    """
    if formato == "json":
        return formatar_json(relatorio)
    if formato == "html":
        return gerar_html(relatorio, gerado_em or datetime.now())
    return formatar_texto(relatorio)


# --- JSON ---------------------------------------------------------------------


def _decimal_json(valor: Decimal | None) -> str | None:
    return None if valor is None else str(arredondar(valor))


def _produto_json(produto: ResumoProduto) -> dict[str, Any]:
    return {
        "produto": produto.produto,
        "quantidade": produto.quantidade,
        "valor_total": _decimal_json(produto.valor_total),
        "participacao": _decimal_json(produto.participacao),
        "participacao_acumulada": _decimal_json(produto.participacao_acumulada),
        "classe_abc": produto.classe_abc,
        "preco_medio": _decimal_json(produto.preco_medio),
        "preco_min": _decimal_json(produto.preco_min),
        "preco_max": _decimal_json(produto.preco_max),
        "cv": _decimal_json(produto.cv),
        "classe_xyz": produto.classe_xyz,
        "mes_pico": produto.mes_pico,
    }


def relatorio_para_dict(relatorio: Relatorio) -> dict[str, Any]:
    """Relatório em tipos JSON; ``Decimal`` vira string com 2 casas."""
    mais_vendido = relatorio.mais_vendido
    return {
        "periodo": {
            "inicio": relatorio.inicio.isoformat() if relatorio.inicio else None,
            "fim": relatorio.fim.isoformat() if relatorio.fim else None,
        },
        "registros": {
            "validos": relatorio.validos,
            "ignorados": relatorio.ignorados,
            "no_periodo": relatorio.no_periodo,
        },
        "produtos": [_produto_json(produto) for produto in relatorio.produtos],
        "valor_total": _decimal_json(relatorio.valor_total),
        "mais_vendido": (
            {"produto": mais_vendido.produto, "quantidade": mais_vendido.quantidade}
            if mais_vendido
            else None
        ),
        "curva_abc": {
            resumo.classe: {
                "produtos": resumo.produtos,
                "valor_total": _decimal_json(resumo.valor_total),
                "participacao": _decimal_json(resumo.participacao),
            }
            for resumo in relatorio.curva_abc
        },
        "matriz_abc_xyz": {abc: dict(linha) for abc, linha in relatorio.matriz_abc_xyz.items()},
        "vendas_por_mes": [
            {
                "mes": mes.mes,
                "quantidade": mes.quantidade,
                "valor_total": _decimal_json(mes.valor_total),
                "variacao": _decimal_json(mes.variacao),
            }
            for mes in relatorio.vendas_por_mes
        ],
    }


def formatar_json(relatorio: Relatorio) -> str:
    return json.dumps(relatorio_para_dict(relatorio), ensure_ascii=False, indent=2)


# --- Texto --------------------------------------------------------------------

Alinhamento = Literal["<", ">"]


def montar_tabela(
    cabecalho: Sequence[str],
    linhas: Sequence[Sequence[str]],
    alinhamento: Sequence[Alinhamento],
    total: Sequence[str] | None = None,
) -> list[str]:
    """Tabela em texto com colunas na largura do maior valor e separador ``---``."""
    todas = [cabecalho, *linhas, *([total] if total else [])]
    larguras = [max(len(linha[i]) for linha in todas) for i in range(len(cabecalho))]

    def formatar_linha(linha: Sequence[str]) -> str:
        celulas = (
            f"{celula:{alinhar}{largura}}"
            for celula, alinhar, largura in zip(linha, alinhamento, larguras, strict=True)
        )
        return "  ".join(celulas).rstrip()

    separador = "  ".join("-" * largura for largura in larguras)
    saida = [formatar_linha(cabecalho), separador, *(formatar_linha(linha) for linha in linhas)]
    if total:
        saida += [separador, formatar_linha(total)]
    return saida


def _opcional(valor: Decimal | None) -> str:
    return VAZIO if valor is None else formatar_decimal(valor)


def _tabela_produtos(relatorio: Relatorio) -> list[str]:
    linhas = [
        [
            produto.produto,
            formatar_inteiro(produto.quantidade),
            formatar_decimal(produto.valor_total),
            formatar_decimal(produto.participacao),
            formatar_decimal(produto.participacao_acumulada),
            produto.classe_abc,
        ]
        for produto in relatorio.produtos
    ]
    total = [
        "TOTAL",
        formatar_inteiro(relatorio.quantidade_total),
        formatar_decimal(relatorio.valor_total),
        formatar_decimal(relatorio.participacao_total),
        "",
        "",
    ]
    return montar_tabela(
        ["Produto", "Quantidade", "Valor (R$)", "Part. %", "Acum. %", "ABC"],
        linhas,
        ["<", ">", ">", ">", ">", "<"],
        total,
    )


def _tabela_demanda(relatorio: Relatorio) -> list[str]:
    linhas = [
        [
            produto.produto,
            formatar_decimal(produto.preco_medio),
            formatar_decimal(produto.preco_min),
            formatar_decimal(produto.preco_max),
            _opcional(produto.cv),
            produto.classe_xyz or VAZIO,
            produto.mes_pico,
        ]
        for produto in relatorio.produtos
    ]
    return montar_tabela(
        ["Produto", "Preço médio", "Preço mín", "Preço máx", "CV", "XYZ", "Pico"],
        linhas,
        ["<", ">", ">", ">", ">", "<", "<"],
    )


def _tabela_matriz(relatorio: Relatorio) -> list[str]:
    linhas = [
        [abc, *(formatar_inteiro(linha[xyz]) for xyz in CLASSES_XYZ)]
        for abc, linha in relatorio.matriz_abc_xyz.items()
    ]
    return montar_tabela(["ABC", *CLASSES_XYZ], linhas, ["<", ">", ">", ">"])


def _tabela_meses(relatorio: Relatorio) -> list[str]:
    linhas = [
        [
            mes.mes,
            formatar_inteiro(mes.quantidade),
            formatar_decimal(mes.valor_total),
            _opcional(mes.variacao),
        ]
        for mes in relatorio.vendas_por_mes
    ]
    return montar_tabela(
        ["Mês", "Quantidade", "Valor (R$)", "Variação %"], linhas, ["<", ">", ">", ">"]
    )


def _resumo_abc(relatorio: Relatorio) -> str:
    partes = (
        f"{resumo.classe} {plural(resumo.produtos, 'produto', 'produtos')}"
        f" ({formatar_decimal(resumo.participacao)}%)"
        for resumo in relatorio.curva_abc
    )
    return "Curva ABC: " + " · ".join(partes)


def formatar_texto(relatorio: Relatorio) -> str:
    linhas = [
        "Relatório de vendas",
        f"Período: {formatar_periodo(relatorio.inicio, relatorio.fim)}",
        f"Registros: {formatar_inteiro(relatorio.validos)} válidos,"
        f" {formatar_inteiro(relatorio.ignorados)} ignorados,"
        f" {formatar_inteiro(relatorio.no_periodo)} no período",
        "",
    ]

    if not relatorio.produtos:
        linhas.append("Nenhuma venda no período.")
        return "\n".join(linhas)

    mais_vendido = relatorio.mais_vendido
    assert mais_vendido is not None  # há produtos, então há mais vendido

    linhas += ["Produtos (curva ABC)", *_tabela_produtos(relatorio), ""]
    linhas += [
        f"Produto mais vendido: {mais_vendido.produto}"
        f" ({plural(mais_vendido.quantidade, 'unidade', 'unidades')})",
        "",
    ]
    linhas += [_resumo_abc(relatorio), ""]
    linhas += ["Demanda e preço", *_tabela_demanda(relatorio), ""]
    linhas += ["Matriz ABC-XYZ (produtos)", *_tabela_matriz(relatorio), ""]
    linhas += ["Vendas por mês", *_tabela_meses(relatorio)]
    return "\n".join(linhas)
