"""Relatório em HTML: arquivo único, CSS inline, sem JavaScript nem recurso externo.

Todo texto vindo do CSV passa por ``html.escape``. Função pura: a data de geração
entra como parâmetro.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from string import Template

from vendas_cli import __version__
from vendas_cli.core import CLASSES_XYZ, LIMITE_A, LIMITE_B, LIMITE_X, LIMITE_Y
from vendas_cli.formatacao import (
    formatar_decimal,
    formatar_inteiro,
    formatar_periodo,
    plural,
)
from vendas_cli.models import Relatorio

VAZIO = "&ndash;"

_PAGINA = Template("""\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório de vendas · $periodo</title>
<style>
:root {
  --fundo: #f5f6f8;
  --superficie: #ffffff;
  --texto: #1c2430;
  --suave: #5b6675;
  --borda: #dde1e7;
  --destaque: #0f5e9c;
  --destaque-rgb: 15, 94, 156;
  --positivo: #17803d;
  --negativo: #b42318;
  --a: #0f5e9c; --b: #5a8fc2; --c: #a9b4c2;
  --x: #17803d; --y: #b7791f; --z: #b42318;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--fundo);
  color: var(--texto);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 960px; margin: 0 auto; padding: 32px 16px 48px; }
header { margin-bottom: 24px; }
h1 { margin: 0 0 4px; font-size: 26px; letter-spacing: -0.01em; }
h2 { margin: 0 0 12px; font-size: 17px; }
.meta { margin: 0; color: var(--suave); font-size: 14px; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.card, section {
  background: var(--superficie);
  border: 1px solid var(--borda);
  border-radius: 10px;
}
.card { padding: 16px; }
.card .rotulo { color: var(--suave); font-size: 13px; }
.card .valor { font-size: 22px; font-weight: 650; font-variant-numeric: tabular-nums; }
.card .detalhe { color: var(--suave); font-size: 13px; }
section { padding: 20px; margin-bottom: 16px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { padding: 7px 10px; text-align: left; white-space: nowrap; }
th {
  color: var(--suave);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  border-bottom: 1px solid var(--borda);
}
tbody tr + tr td { border-top: 1px solid var(--borda); }
tfoot td { border-top: 2px solid var(--texto); font-weight: 650; }
.num { text-align: right; }
.nota { margin: 12px 0 0; color: var(--suave); font-size: 13px; }
.badge {
  display: inline-block;
  min-width: 22px;
  padding: 1px 6px;
  border-radius: 5px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}
.classe-A { background: var(--a); } .classe-B { background: var(--b); }
.classe-C { background: var(--c); color: var(--texto); }
.classe-X { background: var(--x); } .classe-Y { background: var(--y); }
.classe-Z { background: var(--z); }
.positivo { color: var(--positivo); } .negativo { color: var(--negativo); }
.matriz { width: auto; }
.matriz th, .matriz td { text-align: center; }
.matriz td { width: 72px; padding: 0; font-size: 17px; font-weight: 650; }
.matriz tbody tr + tr td { border-top: 2px solid var(--superficie); }
.matriz td + td { border-left: 2px solid var(--superficie); }
.vazio { padding: 32px; text-align: center; color: var(--suave); }
footer { color: var(--suave); font-size: 13px; }
footer p { margin: 4px 0; }
@media print {
  @page { size: A4; margin: 14mm; }
  body { background: #fff; font-size: 12px; }
  main { max-width: none; padding: 0; }
  .card, section { border-color: #c8cdd5; break-inside: avoid; }
  tr { break-inside: avoid; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
</head>
<body>
<main>
<header>
<h1>Relatório de vendas</h1>
<p class="meta">Período: $periodo · Registros: $registros · Gerado em $gerado_em</p>
</header>
$conteudo
<footer>
<p>ABC (por valor): A até $limite_a% do acumulado, B até $limite_b%, C o restante.
XYZ (regularidade da demanda mensal, CV = desvio padrão ÷ média):
X até $limite_x, Y até $limite_y, Z acima.</p>
<p>Gerado por vendas-cli $versao.</p>
</footer>
</main>
</body>
</html>
""")


def gerar_html(relatorio: Relatorio, gerado_em: datetime) -> str:
    """Documento HTML completo do relatório."""
    secoes = [_cards(relatorio)]
    if relatorio.produtos:
        secoes += [
            _secao_produtos(relatorio),
            _secao_demanda(relatorio),
            _secao_matriz(relatorio),
            _secao_meses(relatorio),
        ]
    else:
        secoes.append('<section class="vazio">Nenhuma venda no período</section>')

    return _PAGINA.substitute(
        periodo=formatar_periodo(relatorio.inicio, relatorio.fim),
        registros=(
            f"{formatar_inteiro(relatorio.validos)} válidos,"
            f" {formatar_inteiro(relatorio.ignorados)} ignorados,"
            f" {formatar_inteiro(relatorio.no_periodo)} no período"
        ),
        gerado_em=gerado_em.strftime("%Y-%m-%d %H:%M"),
        conteudo="\n".join(secoes),
        limite_a=formatar_inteiro(int(LIMITE_A)),
        limite_b=formatar_inteiro(int(LIMITE_B)),
        limite_x=str(LIMITE_X).replace(".", ","),
        limite_y=str(LIMITE_Y).replace(".", ","),
        versao=html.escape(__version__),
    )


def _opcional(valor: Decimal | None) -> str:
    return VAZIO if valor is None else formatar_decimal(valor)


def _badge(classe: str | None) -> str:
    if classe is None:
        return VAZIO
    return f'<span class="badge classe-{classe}">{classe}</span>'


def _tabela(
    cabecalho: Sequence[str],
    linhas: Sequence[Sequence[str]],
    numericas: frozenset[int],
    rodape: Sequence[str] | None = None,
    classe: str = "",
) -> str:
    """Tabela HTML. Cabeçalho é escapado; células já devem vir seguras."""

    def celula(tag: str, indice: int, conteudo: str) -> str:
        atributo = ' class="num"' if indice in numericas else ""
        return f"<{tag}{atributo}>{conteudo}</{tag}>"

    def linha(tag: str, celulas: Sequence[str]) -> str:
        return "<tr>" + "".join(celula(tag, i, c) for i, c in enumerate(celulas)) + "</tr>"

    partes = [f'<table class="{classe}">' if classe else "<table>"]
    partes.append("<thead>" + linha("th", [html.escape(c) for c in cabecalho]) + "</thead>")
    partes.append("<tbody>" + "".join(linha("td", celulas) for celulas in linhas) + "</tbody>")
    if rodape:
        partes.append("<tfoot>" + linha("td", rodape) + "</tfoot>")
    partes.append("</table>")
    return "".join(partes)


def _secao(titulo: str, corpo: str) -> str:
    return f"<section>\n<h2>{html.escape(titulo)}</h2>\n{corpo}\n</section>"


def _card(rotulo: str, valor: str, detalhe: str = "") -> str:
    linha_detalhe = f'<div class="detalhe">{detalhe}</div>' if detalhe else ""
    return (
        f'<div class="card"><div class="rotulo">{rotulo}</div>'
        f'<div class="valor">{valor}</div>{linha_detalhe}</div>'
    )


def _cards(relatorio: Relatorio) -> str:
    mais_vendido = relatorio.mais_vendido
    cards = [
        _card("Valor total", f"R$ {formatar_decimal(relatorio.valor_total)}"),
        _card("Quantidade vendida", formatar_inteiro(relatorio.quantidade_total), "unidades"),
        _card(
            "Produto mais vendido",
            html.escape(mais_vendido.produto) if mais_vendido else VAZIO,
            plural(mais_vendido.quantidade, "unidade", "unidades") if mais_vendido else "",
        ),
    ]
    return '<div class="cards">' + "".join(cards) + "</div>"


def _secao_produtos(relatorio: Relatorio) -> str:
    linhas = [
        [
            html.escape(produto.produto),
            formatar_inteiro(produto.quantidade),
            formatar_decimal(produto.valor_total),
            formatar_decimal(produto.participacao),
            formatar_decimal(produto.participacao_acumulada),
            _badge(produto.classe_abc),
        ]
        for produto in relatorio.produtos
    ]
    participacao_total = sum((produto.participacao for produto in relatorio.produtos), Decimal(0))
    rodape = [
        "Total",
        formatar_inteiro(relatorio.quantidade_total),
        formatar_decimal(relatorio.valor_total),
        formatar_decimal(participacao_total),
        "",
        "",
    ]
    tabela = _tabela(
        ["Produto", "Quantidade", "Valor (R$)", "Part. %", "Acum. %", "ABC"],
        linhas,
        frozenset({1, 2, 3, 4}),
        rodape,
    )
    resumo = " · ".join(
        f"{_badge(resumo.classe)} {plural(resumo.produtos, 'produto', 'produtos')}"
        f" ({formatar_decimal(resumo.participacao)}% do valor)"
        for resumo in relatorio.curva_abc
    )
    return _secao("Produtos (curva ABC)", f'{tabela}\n<p class="nota">{resumo}</p>')


def _secao_demanda(relatorio: Relatorio) -> str:
    linhas = [
        [
            html.escape(produto.produto),
            formatar_decimal(produto.preco_medio),
            formatar_decimal(produto.preco_min),
            formatar_decimal(produto.preco_max),
            _opcional(produto.cv),
            _badge(produto.classe_xyz),
            produto.mes_pico,
        ]
        for produto in relatorio.produtos
    ]
    tabela = _tabela(
        ["Produto", "Preço médio", "Preço mín", "Preço máx", "CV", "XYZ", "Pico"],
        linhas,
        frozenset({1, 2, 3, 4}),
    )
    sem_xyz = all(produto.classe_xyz is None for produto in relatorio.produtos)
    nota = (
        '\n<p class="nota">Período com menos de 3 meses: XYZ não calculado.</p>' if sem_xyz else ""
    )
    return _secao("Demanda e preço", tabela + nota)


def _secao_matriz(relatorio: Relatorio) -> str:
    maior = max(
        (n for linha in relatorio.matriz_abc_xyz.values() for n in linha.values()), default=0
    )

    def celula(quantidade: int) -> str:
        intensidade = quantidade / maior if maior else 0
        alfa = 0.08 + 0.82 * intensidade if quantidade else 0.04
        cor = "#fff" if alfa > 0.5 else "var(--texto)"
        return (
            f'<span style="display:block;padding:12px 0;'
            f'background:rgba(var(--destaque-rgb),{alfa:.2f});color:{cor}">'
            f"{formatar_inteiro(quantidade)}</span>"
        )

    linhas = [
        [_badge(abc), *(celula(linha[xyz]) for xyz in CLASSES_XYZ)]
        for abc, linha in relatorio.matriz_abc_xyz.items()
    ]
    tabela = _tabela(["ABC \\ XYZ", *CLASSES_XYZ], linhas, frozenset(), classe="matriz")
    nota = (
        '<p class="nota">AX: alto valor e demanda estável, reposição previsível.'
        " AZ: alto valor e demanda errática, atenção ao estoque.</p>"
    )
    return _secao("Matriz ABC-XYZ (produtos)", f"{tabela}\n{nota}")


def _secao_meses(relatorio: Relatorio) -> str:
    def variacao(valor: Decimal | None) -> str:
        if valor is None:
            return VAZIO
        classe = "positivo" if valor > 0 else "negativo" if valor < 0 else ""
        texto = formatar_decimal(valor)
        return f'<span class="{classe}">{texto}</span>' if classe else texto

    linhas = [
        [
            mes.mes,
            formatar_inteiro(mes.quantidade),
            formatar_decimal(mes.valor_total),
            variacao(mes.variacao),
        ]
        for mes in relatorio.vendas_por_mes
    ]
    tabela = _tabela(
        ["Mês", "Quantidade", "Valor (R$)", "Variação %"], linhas, frozenset({1, 2, 3})
    )
    return _secao("Vendas por mês", tabela)
