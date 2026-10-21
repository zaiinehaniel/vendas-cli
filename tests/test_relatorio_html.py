from __future__ import annotations

from datetime import date, datetime
from html.parser import HTMLParser

from auxiliares import VENDAS_EXEMPLO, venda

from vendas_cli.core import gerar_relatorio
from vendas_cli.models import Relatorio
from vendas_cli.relatorio_html import gerar_html

GERADO_EM = datetime(2026, 10, 21, 14, 30)

_SEM_FECHAMENTO = {"meta", "br", "hr", "img", "input", "link"}


class VerificadorDeTags(HTMLParser):
    """Confere se toda tag aberta é fechada na ordem certa."""

    def __init__(self) -> None:
        super().__init__()
        self.abertas: list[str] = []
        self.erros: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _SEM_FECHAMENTO:
            self.abertas.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.abertas or self.abertas[-1] != tag:
            self.erros.append(f"</{tag}> fecha {self.abertas[-1:] or 'nada'}")
        else:
            self.abertas.pop()


def verificar_estrutura(documento: str) -> None:
    verificador = VerificadorDeTags()
    verificador.feed(documento)
    verificador.close()
    assert verificador.erros == []
    assert verificador.abertas == []


def test_documento_bem_formado(relatorio_exemplo: Relatorio) -> None:
    documento = gerar_html(relatorio_exemplo, GERADO_EM)

    assert documento.startswith("<!doctype html>")
    assert '<html lang="pt-BR">' in documento
    assert '<meta charset="utf-8">' in documento
    verificar_estrutura(documento)


def test_conteudo_do_exemplo(relatorio_exemplo: Relatorio) -> None:
    documento = gerar_html(relatorio_exemplo, GERADO_EM)

    for trecho in [
        "Período: início a fim",
        "8 válidos, 0 ignorados, 8 no período",
        "Gerado em 2026-10-21 14:30",
        "R$ 23.357,80",
        "42 unidades",
        "88,84",
        "3.458,33",
        "2025-04",
        '<span class="badge classe-A">A</span>',
        '<span class="badge classe-Z">Z</span>',
        '<span class="negativo">-47,03</span>',
        '<span class="positivo">2.460,43</span>',
    ]:
        assert trecho in documento, trecho


def test_autocontido_sem_script_nem_recurso_externo(relatorio_exemplo: Relatorio) -> None:
    documento = gerar_html(relatorio_exemplo, GERADO_EM).lower()

    assert "<script" not in documento
    assert "http://" not in documento
    assert "https://" not in documento
    assert "<link" not in documento


def test_nome_de_produto_e_escapado() -> None:
    relatorio = gerar_relatorio([venda("2025-01-01", '<script>alert(1)</script> & "Cia"', 1, "1")])

    documento = gerar_html(relatorio, GERADO_EM)

    assert "<script" not in documento
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;Cia&quot;" in documento
    verificar_estrutura(documento)


def test_sem_vendas_mostra_mensagem_e_omite_tabelas() -> None:
    relatorio = gerar_relatorio(VENDAS_EXEMPLO, inicio=date(2026, 1, 1))

    documento = gerar_html(relatorio, GERADO_EM)

    assert "Nenhuma venda no período" in documento
    assert "<table" not in documento
    assert "R$ 0,00" in documento
    verificar_estrutura(documento)


def test_periodo_curto_avisa_que_xyz_nao_foi_calculado() -> None:
    relatorio = gerar_relatorio(VENDAS_EXEMPLO, inicio=date(2025, 4, 1))

    documento = gerar_html(relatorio, GERADO_EM)

    assert "XYZ não calculado" in documento
    assert 'class="badge classe-X"' not in documento


def test_periodo_completo_nao_mostra_aviso_de_xyz(relatorio_exemplo: Relatorio) -> None:
    assert "XYZ não calculado" not in gerar_html(relatorio_exemplo, GERADO_EM)
