from __future__ import annotations

import logging
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from auxiliares import VENDAS_EXEMPLO, CriarCSV

from vendas_cli.models import Venda
from vendas_cli.parser import ErroLeituraCSV, converter_linha, ler_vendas

CABECALHO = "data,produto,quantidade,preco_unitario\n"


def linha(**campos: str | None) -> dict[str | None, str | None]:
    base: dict[str | None, str | None] = {
        "data": "2025-01-15",
        "produto": "Mouse",
        "quantidade": "10",
        "preco_unitario": "45.90",
    }
    base.update(campos)
    return base


# --- ler_vendas: arquivo válido ----------------------------------------------


def test_le_csv_valido(csv_exemplo: Path) -> None:
    resultado = ler_vendas(csv_exemplo)

    assert resultado.vendas == VENDAS_EXEMPLO
    assert resultado.ignorados == 0


def test_aceita_caminho_como_texto(csv_exemplo: Path) -> None:
    assert len(ler_vendas(str(csv_exemplo)).vendas) == 8


def test_colunas_em_outra_ordem(criar_csv: CriarCSV) -> None:
    caminho = criar_csv("preco_unitario,produto,data,quantidade\n45.90,Mouse,2025-01-15,10\n")

    assert ler_vendas(caminho).vendas == (Venda(date(2025, 1, 15), "Mouse", 10, Decimal("45.90")),)


def test_cabecalho_com_espacos_e_maiusculas(criar_csv: CriarCSV) -> None:
    caminho = criar_csv(" Data , PRODUTO ,Quantidade,Preco_Unitario\n2025-01-15,Mouse,10,45.90\n")

    assert len(ler_vendas(caminho).vendas) == 1


def test_aceita_bom_utf8(criar_csv: CriarCSV) -> None:
    caminho = criar_csv(CABECALHO + "2025-01-15,Café,1,10.00\n", encoding="utf-8-sig")

    assert ler_vendas(caminho).vendas[0].produto == "Café"


def test_coluna_extra_no_cabecalho_e_ignorada(criar_csv: CriarCSV) -> None:
    caminho = criar_csv("data,produto,quantidade,preco_unitario,obs\n2025-01-15,Mouse,1,10,x\n")

    assert len(ler_vendas(caminho).vendas) == 1


def test_preco_pt_br_entre_aspas(criar_csv: CriarCSV) -> None:
    caminho = criar_csv(CABECALHO + '2025-01-15,Notebook,1,"3.500,00"\n')

    assert ler_vendas(caminho).vendas[0].preco_unitario == Decimal("3500.00")


def test_so_cabecalho_gera_lista_vazia(criar_csv: CriarCSV) -> None:
    resultado = ler_vendas(criar_csv(CABECALHO))

    assert resultado.vendas == ()
    assert resultado.ignorados == 0


def test_linhas_em_branco_sao_puladas(criar_csv: CriarCSV) -> None:
    caminho = criar_csv(CABECALHO + "\n2025-01-15,Mouse,1,10\n\n")

    resultado = ler_vendas(caminho)
    assert len(resultado.vendas) == 1
    assert resultado.ignorados == 0


# --- ler_vendas: linhas inválidas ----------------------------------------------


def test_linhas_invalidas_sao_ignoradas_e_logadas(
    criar_csv: CriarCSV, caplog: pytest.LogCaptureFixture
) -> None:
    caminho = criar_csv(
        CABECALHO
        + "2025-01-15,Mouse,10,45.90\n"  # linha 2: válida
        + "2025-1-5,Mouse,1,1\n"  # linha 3: data fora do formato
        + "2025-01-15,Mouse,0,1\n"  # linha 4: quantidade zero
        + "2025-01-15,Mouse,1,45,90\n"  # linha 5: preço com vírgula sem aspas
        + "2025-01-15,Mouse,1,-1\n"  # linha 6: preço negativo
        + ",Mouse,1,1\n"  # linha 7: data vazia
    )
    caplog.set_level(logging.WARNING, logger="vendas_cli")

    resultado = ler_vendas(caminho)

    assert len(resultado.vendas) == 1
    assert resultado.ignorados == 5
    avisos = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert avisos == [
        "linha 3 ignorada: data inválida '2025-1-5' (esperado AAAA-MM-DD)",
        "linha 4 ignorada: quantidade deve ser maior que zero: 0",
        "linha 5 ignorada: mais colunas que o cabeçalho"
        ' (preço com vírgula precisa de aspas: "45,90")',
        "linha 6 ignorada: preço não pode ser negativo: -1",
        "linha 7 ignorada: campo 'data' vazio",
    ]


def test_loga_resumo_da_leitura(csv_exemplo: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="vendas_cli")

    ler_vendas(csv_exemplo)

    assert "8 venda(s) lida(s), 0 linha(s) ignorada(s)" in caplog.messages


# --- ler_vendas: erros fatais ---------------------------------------------------


def test_arquivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(ErroLeituraCSV, match="arquivo não encontrado"):
        ler_vendas(tmp_path / "nao_existe.csv")


def test_arquivo_vazio(criar_csv: CriarCSV) -> None:
    with pytest.raises(ErroLeituraCSV, match="arquivo vazio"):
        ler_vendas(criar_csv(""))


def test_cabecalho_sem_coluna_obrigatoria(criar_csv: CriarCSV) -> None:
    caminho = criar_csv("data,produto\n2025-01-15,Mouse\n")

    with pytest.raises(ErroLeituraCSV, match=r"ausente.*preco_unitario, quantidade"):
        ler_vendas(caminho)


def test_diretorio_no_lugar_do_arquivo(tmp_path: Path) -> None:
    with pytest.raises(ErroLeituraCSV, match="não é um arquivo"):
        ler_vendas(tmp_path)


def test_arquivo_fora_de_utf8(tmp_path: Path) -> None:
    caminho = tmp_path / "latin1.csv"
    caminho.write_bytes((CABECALHO + "2025-01-15,Café,1,10\n").encode("latin-1"))

    with pytest.raises(ErroLeituraCSV, match="não está em UTF-8"):
        ler_vendas(caminho)


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="permissão de arquivo POSIX, sem root"
)
def test_arquivo_sem_permissao(csv_exemplo: Path) -> None:
    csv_exemplo.chmod(0o000)
    try:
        with pytest.raises(ErroLeituraCSV, match="sem permissão"):
            ler_vendas(csv_exemplo)
    finally:
        csv_exemplo.chmod(0o644)


# --- converter_linha ------------------------------------------------------------


def test_converte_linha_valida() -> None:
    assert converter_linha(linha(produto="  Mouse  ")) == Venda(
        date(2025, 1, 15), "Mouse", 10, Decimal("45.90")
    )


@pytest.mark.parametrize("campo", ["data", "produto", "quantidade", "preco_unitario"])
@pytest.mark.parametrize("valor", [None, "", "   "])
def test_campo_vazio(campo: str, valor: str | None) -> None:
    with pytest.raises(ValueError, match=f"campo '{campo}' vazio"):
        converter_linha(linha(**{campo: valor}))


def test_coluna_excedente() -> None:
    dados = linha(preco_unitario="45")
    dados[None] = "90"  # o DictReader guarda o excedente na chave None

    with pytest.raises(ValueError, match="mais colunas que o cabeçalho"):
        converter_linha(dados)


@pytest.mark.parametrize("quantidade", ["0", "-2"])
def test_quantidade_deve_ser_positiva(quantidade: str) -> None:
    with pytest.raises(ValueError, match="quantidade deve ser maior que zero"):
        converter_linha(linha(quantidade=quantidade))


def test_preco_negativo() -> None:
    with pytest.raises(ValueError, match="preço não pode ser negativo"):
        converter_linha(linha(preco_unitario="-0,01"))


def test_preco_zero_e_valido() -> None:
    assert converter_linha(linha(preco_unitario="0")).preco_unitario == 0
