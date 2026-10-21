"""Leitura e validação do CSV de vendas."""

from __future__ import annotations

import csv
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from vendas_cli.models import Venda
from vendas_cli.normalizer import normalizar_data, normalizar_preco, normalizar_quantidade

logger = logging.getLogger(__name__)

COLUNAS_OBRIGATORIAS = frozenset({"data", "produto", "quantidade", "preco_unitario"})


class ErroLeituraCSV(Exception):
    """Erro fatal: o arquivo não pode ser processado."""


@dataclass(frozen=True)
class ResultadoLeitura:
    vendas: tuple[Venda, ...]
    ignorados: int


def ler_vendas(caminho: Path | str) -> ResultadoLeitura:
    """Lê o CSV, ignorando (com log) linhas inválidas.

    Levanta ``ErroLeituraCSV`` quando o arquivo não pode ser lido, está vazio
    ou não tem as colunas obrigatórias.
    """
    caminho = Path(caminho)
    try:
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
            resultado = _ler(arquivo, caminho)
    except FileNotFoundError:
        raise ErroLeituraCSV(f"arquivo não encontrado: {caminho}") from None
    except IsADirectoryError:
        raise ErroLeituraCSV(f"não é um arquivo: {caminho}") from None
    except PermissionError:
        raise ErroLeituraCSV(f"sem permissão para ler: {caminho}") from None
    except UnicodeDecodeError:
        raise ErroLeituraCSV(f"arquivo não está em UTF-8: {caminho}") from None
    except csv.Error as exc:
        raise ErroLeituraCSV(f"CSV malformado em {caminho}: {exc}") from None
    except OSError as exc:
        raise ErroLeituraCSV(f"não foi possível ler {caminho}: {exc.strerror}") from None

    logger.info(
        "%d venda(s) lida(s), %d linha(s) ignorada(s)",
        len(resultado.vendas),
        resultado.ignorados,
    )
    return resultado


def _ler(arquivo: TextIO, caminho: Path) -> ResultadoLeitura:
    leitor = csv.DictReader(arquivo)
    if leitor.fieldnames is None:
        raise ErroLeituraCSV(f"arquivo vazio: {caminho}")

    leitor.fieldnames = [nome.strip().lower() for nome in leitor.fieldnames]
    faltando = COLUNAS_OBRIGATORIAS - set(leitor.fieldnames)
    if faltando:
        raise ErroLeituraCSV(
            f"coluna(s) obrigatória(s) ausente(s) em {caminho}: {', '.join(sorted(faltando))}"
        )

    vendas: list[Venda] = []
    ignorados = 0
    for linha in leitor:
        try:
            vendas.append(converter_linha(linha))
        except ValueError as exc:
            ignorados += 1
            logger.warning("linha %d ignorada: %s", leitor.line_num, exc)

    return ResultadoLeitura(vendas=tuple(vendas), ignorados=ignorados)


def converter_linha(linha: Mapping[str | None, str | None]) -> Venda:
    """Converte uma linha do ``DictReader`` em ``Venda``. Levanta ``ValueError`` se inválida."""
    # DictReader guarda colunas excedentes na chave None; ex.: preço 45,90 sem aspas
    if None in linha:
        raise ValueError(
            'mais colunas que o cabeçalho (preço com vírgula precisa de aspas: "45,90")'
        )

    data = normalizar_data(_campo(linha, "data"))
    produto = _campo(linha, "produto")

    quantidade = normalizar_quantidade(_campo(linha, "quantidade"))
    if quantidade <= 0:
        raise ValueError(f"quantidade deve ser maior que zero: {quantidade}")

    preco = normalizar_preco(_campo(linha, "preco_unitario"))
    if preco < 0:
        raise ValueError(f"preço não pode ser negativo: {preco}")

    return Venda(data=data, produto=produto, quantidade=quantidade, preco_unitario=preco)


def _campo(linha: Mapping[str | None, str | None], nome: str) -> str:
    valor = linha.get(nome)
    if valor is None or not valor.strip():
        raise ValueError(f"campo '{nome}' vazio")
    return valor.strip()
