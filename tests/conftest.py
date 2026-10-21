from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from auxiliares import CSV_EXEMPLO, VENDAS_EXEMPLO, CriarCSV

from vendas_cli.core import gerar_relatorio
from vendas_cli.models import Relatorio


@pytest.fixture(autouse=True)
def _restaurar_logger_do_pacote() -> Iterator[None]:
    """O ``main`` instala handler e nível no logger do pacote; cada teste começa limpo."""
    yield
    logger = logging.getLogger("vendas_cli")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)


@pytest.fixture
def criar_csv(tmp_path: Path) -> CriarCSV:
    def criar(conteudo: str, nome: str = "vendas.csv", encoding: str = "utf-8") -> Path:
        caminho = tmp_path / nome
        caminho.write_text(conteudo, encoding=encoding)
        return caminho

    return criar


@pytest.fixture
def csv_exemplo(criar_csv: CriarCSV) -> Path:
    return criar_csv(CSV_EXEMPLO)


@pytest.fixture
def relatorio_exemplo() -> Relatorio:
    return gerar_relatorio(VENDAS_EXEMPLO)
