"""Interface de linha de comando: argumentos, logging, orquestração e exit codes."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from vendas_cli import __version__
from vendas_cli.core import gerar_relatorio
from vendas_cli.normalizer import normalizar_data
from vendas_cli.output import FORMATOS, formatar
from vendas_cli.parser import ErroLeituraCSV, ler_vendas

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_ERRO = 1

_NOME_HANDLER = "vendas-cli"


def _data_argumento(texto: str) -> date:
    try:
        return normalizar_data(texto)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vendas-cli",
        description=(
            "Gera relatório de vendas a partir de um CSV "
            "(data,produto,quantidade,preco_unitario): totais por produto, "
            "curva ABC, classificação XYZ e vendas por mês."
        ),
    )
    parser.add_argument("arquivo", type=Path, help="caminho do CSV de vendas")
    parser.add_argument(
        "--format",
        choices=FORMATOS,
        default="text",
        help="formato da saída (padrão: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="SAIDA",
        help="grava o relatório neste arquivo em vez da saída padrão",
    )
    parser.add_argument(
        "--start",
        type=_data_argumento,
        metavar="AAAA-MM-DD",
        help="data inicial, inclusiva",
    )
    parser.add_argument(
        "--end",
        type=_data_argumento,
        metavar="AAAA-MM-DD",
        help="data final, inclusiva",
    )
    verbosidade = parser.add_mutually_exclusive_group()
    verbosidade.add_argument(
        "-v", "--verbose", action="store_true", help="mostra logs de depuração"
    )
    verbosidade.add_argument("-q", "--quiet", action="store_true", help="mostra só erros")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger_pacote.addHandler(handler)
    logger_pacote.setLevel(nivel)


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada. Devolve o exit code; erros de argumento saem com 2 pelo argparse."""
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
        return EXIT_ERRO

    relatorio = gerar_relatorio(
        leitura.vendas, inicio=args.start, fim=args.end, ignorados=leitura.ignorados
    )
    logger.debug("%d venda(s) no período", relatorio.no_periodo)
    saida = formatar(relatorio, args.format) + "\n"

    if args.output is None:
        sys.stdout.write(saida)
        return EXIT_OK

    try:
        args.output.write_text(saida, encoding="utf-8")
    except OSError as exc:
        logger.error("não foi possível gravar %s: %s", args.output, exc.strerror or exc)
        return EXIT_ERRO
    logger.info("relatório gravado em %s", args.output)
    return EXIT_OK
