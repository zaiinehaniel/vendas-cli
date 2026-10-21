"""Interface de linha de comando: argumentos, logging, orquestração e códigos de saída."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import NoReturn

from vendas_cli import __version__
from vendas_cli.core import gerar_relatorio
from vendas_cli.normalizer import normalizar_data
from vendas_cli.output import FORMATOS, formatar
from vendas_cli.parser import ErroLeituraCSV, ler_vendas

logger = logging.getLogger(__name__)

CODIGO_SUCESSO = 0
CODIGO_ERRO = 1
CODIGO_ARGUMENTO_INVALIDO = 2

_NOME_HANDLER = "vendas-cli"

_NIVEIS_LOG = {
    "DEBUG": "DEPURAÇÃO",
    "INFO": "INFO",
    "WARNING": "AVISO",
    "ERROR": "ERRO",
    "CRITICAL": "CRÍTICO",
}

# O argparse não traz tradução; as mensagens dele são reescritas aqui.
_TRADUCOES_ARGPARSE: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(padrao), substituto)
    for padrao, substituto in (
        (r"^the following arguments are required: (.+)$", r"argumentos obrigatórios ausentes: \1"),
        (r"^unrecognized arguments: (.+)$", r"argumentos não reconhecidos: \1"),
        (
            r"^argument (\S+): invalid choice: (.+?) \(choose from (.+)\)$",
            r"argumento \1: opção inválida \2 (escolha entre \3)",
        ),
        (
            r"^argument (\S+): not allowed with argument (\S+)$",
            r"argumento \1: não pode ser usado junto com \2",
        ),
        (r"^argument (\S+): expected one argument$", r"argumento \1: requer um valor"),
        (r"^ambiguous option: (\S+) could match (.+)$", r"opção ambígua: \1 pode ser \2"),
        (r"^argument (\S+): (.+)$", r"argumento \1: \2"),
    )
)

_DESCRICAO = """\
Gera um relatório de vendas a partir de um CSV com as colunas
data,produto,quantidade,preco_unitario.

O relatório traz o total por produto, o valor geral, o produto mais vendido,
a curva ABC (participação no valor), a classificação XYZ (regularidade da
demanda mensal), o preço praticado e as vendas mês a mês."""

_EPILOGO = """\
exemplos:
  vendas-cli vendas.csv
  vendas-cli vendas.csv --format json --start 2025-01-01 --end 2025-03-31
  vendas-cli vendas.csv --format html -o relatorio.html

códigos de saída:
  0  relatório gerado
  1  erro ao ler o CSV ou gravar a saída
  2  argumento inválido"""


def traduzir_mensagem_argparse(mensagem: str) -> str:
    for padrao, substituto in _TRADUCOES_ARGPARSE:
        traduzida, trocas = padrao.subn(substituto, mensagem)
        if trocas:
            return traduzida
    return mensagem


class _FormatadorAjuda(argparse.RawDescriptionHelpFormatter):
    def add_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._MutuallyExclusiveGroup],
        prefix: str | None = None,
    ) -> None:
        super().add_usage(usage, actions, groups, prefix="uso: " if prefix is None else prefix)


class _ParserPtBr(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(
            CODIGO_ARGUMENTO_INVALIDO,
            f"{self.prog}: erro: {traduzir_mensagem_argparse(message)}\n",
        )


class _FormatadorLog(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        nivel = _NIVEIS_LOG.get(record.levelname, record.levelname)
        return f"{nivel}: {record.getMessage()}"


def _data_argumento(texto: str) -> date:
    try:
        return normalizar_data(texto)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def criar_parser() -> argparse.ArgumentParser:
    parser = _ParserPtBr(
        prog="vendas-cli",
        description=_DESCRICAO,
        epilog=_EPILOGO,
        formatter_class=_FormatadorAjuda,
        add_help=False,
    )
    entrada = parser.add_argument_group("argumento obrigatório")
    entrada.add_argument(
        "arquivo",
        type=Path,
        help="CSV de vendas em UTF-8, com cabeçalho data,produto,quantidade,preco_unitario",
    )

    saida = parser.add_argument_group("saída")
    saida.add_argument(
        "--format",
        choices=FORMATOS,
        default="text",
        help=(
            "formato do relatório: text (tabelas no terminal), json (para integrar com "
            "outros sistemas) ou html (página para abrir no navegador ou imprimir); "
            "padrão: %(default)s"
        ),
    )
    saida.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="SAIDA",
        help="grava o relatório no arquivo SAIDA (UTF-8) em vez de mostrar no terminal",
    )

    filtro = parser.add_argument_group("filtro por período (datas no formato AAAA-MM-DD)")
    filtro.add_argument(
        "--start",
        type=_data_argumento,
        metavar="AAAA-MM-DD",
        help="considera só as vendas a partir desta data, inclusive",
    )
    filtro.add_argument(
        "--end",
        type=_data_argumento,
        metavar="AAAA-MM-DD",
        help="considera só as vendas até esta data, inclusive",
    )

    geral = parser.add_argument_group("mensagens e ajuda")
    verbosidade = geral.add_mutually_exclusive_group()
    verbosidade.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="mostra também mensagens informativas e de depuração",
    )
    verbosidade.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="mostra só erros, ocultando os avisos de linhas ignoradas",
    )
    geral.add_argument("-h", "--help", action="help", help="mostra esta ajuda e sai")
    geral.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="mostra a versão do vendas-cli e sai",
    )
    return parser


def configurar_logging(nivel: int) -> None:
    """Logs do pacote vão para stderr, deixando stdout só com o relatório.

    Substitui o handler de uma chamada anterior, para ``main`` poder rodar várias
    vezes no mesmo processo (testes) sem duplicar mensagens.
    """
    logger_pacote = logging.getLogger("vendas_cli")
    for handler in list(logger_pacote.handlers):
        if handler.get_name() == _NOME_HANDLER:
            logger_pacote.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.set_name(_NOME_HANDLER)
    handler.setFormatter(_FormatadorLog())
    logger_pacote.addHandler(handler)
    logger_pacote.setLevel(nivel)


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada. Devolve o código de saída; argumento inválido sai com 2 pelo argparse."""
    parser = criar_parser()
    args = parser.parse_args(argv)
    if args.start and args.end and args.start > args.end:
        parser.error(f"--start ({args.start}) é posterior a --end ({args.end})")

    nivel = logging.DEBUG if args.verbose else logging.ERROR if args.quiet else logging.WARNING
    configurar_logging(nivel)

    try:
        leitura = ler_vendas(args.arquivo)
    except ErroLeituraCSV as exc:
        logger.error("%s", exc)
        return CODIGO_ERRO

    relatorio = gerar_relatorio(
        leitura.vendas, inicio=args.start, fim=args.end, ignorados=leitura.ignorados
    )
    logger.debug("%d venda(s) no período", relatorio.no_periodo)
    saida = formatar(relatorio, args.format) + "\n"

    if args.output is None:
        sys.stdout.write(saida)
        return CODIGO_SUCESSO

    try:
        args.output.write_text(saida, encoding="utf-8")
    except OSError as exc:
        logger.error("não foi possível gravar %s: %s", args.output, exc.strerror or exc)
        return CODIGO_ERRO
    logger.info("relatório gravado em %s", args.output)
    return CODIGO_SUCESSO
