from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
from auxiliares import TEXTO_EXEMPLO, CriarCSV

from vendas_cli import __version__
from vendas_cli.cli import main, traduzir_mensagem_argparse

CSV_COM_LINHA_INVALIDA = """\
data,produto,quantidade,preco_unitario
2025-01-15,Mouse,10,45.90
2025-01-16,Mouse,0,45.90
"""


def erro_de_argumento(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    """Roda ``main`` esperando saída 2 do argparse e devolve o stderr."""
    with pytest.raises(SystemExit) as saida:
        main(list(argv))
    assert saida.value.code == 2
    return capsys.readouterr().err


# --- sucesso ------------------------------------------------------------------------


def test_texto_no_stdout(csv_exemplo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(csv_exemplo), "--format", "text"]) == 0

    capturado = capsys.readouterr()
    assert capturado.out == TEXTO_EXEMPLO + "\n"
    assert capturado.err == ""


def test_formato_padrao_e_texto(csv_exemplo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(csv_exemplo)]) == 0
    assert capsys.readouterr().out == TEXTO_EXEMPLO + "\n"


def test_json_com_filtro(csv_exemplo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    codigo = main(
        [str(csv_exemplo), "--format", "json", "--start", "2025-01-01", "--end", "2025-03-31"]
    )

    assert codigo == 0
    dados = json.loads(capsys.readouterr().out)
    assert dados["periodo"] == {"inicio": "2025-01-01", "fim": "2025-03-31"}
    assert dados["registros"]["no_periodo"] == 5


def test_logs_vao_para_stderr_e_json_fica_limpo(
    criar_csv: CriarCSV, capsys: pytest.CaptureFixture[str]
) -> None:
    caminho = criar_csv(CSV_COM_LINHA_INVALIDA)

    assert main([str(caminho), "--format", "json"]) == 0

    capturado = capsys.readouterr()
    assert json.loads(capturado.out)["registros"] == {"validos": 1, "ignorados": 1, "no_periodo": 1}
    assert capturado.err == "AVISO: linha 3 ignorada: quantidade deve ser maior que zero: 0\n"


def test_quiet_oculta_avisos(criar_csv: CriarCSV, capsys: pytest.CaptureFixture[str]) -> None:
    caminho = criar_csv(CSV_COM_LINHA_INVALIDA)

    assert main([str(caminho), "-q"]) == 0
    assert capsys.readouterr().err == ""


def test_verbose_mostra_info_e_depuracao(
    csv_exemplo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(csv_exemplo), "-v"]) == 0

    erro = capsys.readouterr().err
    assert "INFO: 8 venda(s) lida(s), 0 linha(s) ignorada(s)" in erro
    assert "DEPURAÇÃO: 8 venda(s) no período" in erro


def test_rodar_duas_vezes_nao_duplica_logs(
    criar_csv: CriarCSV, capsys: pytest.CaptureFixture[str]
) -> None:
    caminho = criar_csv(CSV_COM_LINHA_INVALIDA)

    main([str(caminho)])
    capsys.readouterr()
    main([str(caminho)])

    assert capsys.readouterr().err.count("AVISO:") == 1


def test_output_grava_arquivo_em_utf8(
    csv_exemplo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "relatorio.txt"

    assert main([str(csv_exemplo), "-o", str(destino)]) == 0

    assert destino.read_text(encoding="utf-8") == TEXTO_EXEMPLO + "\n"
    assert capsys.readouterr().out == ""


def test_output_html(csv_exemplo: Path, tmp_path: Path) -> None:
    destino = tmp_path / "relatorio.html"

    assert main([str(csv_exemplo), "--format", "html", "--output", str(destino)]) == 0

    assert destino.read_text(encoding="utf-8").startswith("<!doctype html>")


# --- erros de leitura e gravação (código 1) ---------------------------------------------


def test_arquivo_inexistente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    caminho = tmp_path / "nao_existe.csv"

    assert main([str(caminho)]) == 1

    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert capturado.err == f"ERRO: arquivo não encontrado: {caminho}\n"


def test_cabecalho_invalido(criar_csv: CriarCSV, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(criar_csv("data,produto\n"))]) == 1
    assert "ERRO: coluna(s) obrigatória(s) ausente(s)" in capsys.readouterr().err


def test_output_em_diretorio_inexistente(
    csv_exemplo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "nao" / "existe" / "r.html"

    assert main([str(csv_exemplo), "-o", str(destino)]) == 1
    assert f"ERRO: não foi possível gravar {destino}" in capsys.readouterr().err


# --- argumentos inválidos (código 2) --------------------------------------------------


def test_start_depois_de_end(csv_exemplo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    erro = erro_de_argumento(
        capsys, str(csv_exemplo), "--start", "2025-03-01", "--end", "2025-01-01"
    )

    assert "vendas-cli: erro: --start (2025-03-01) é posterior a --end (2025-01-01)" in erro
    assert erro.startswith("uso: vendas-cli")


@pytest.mark.parametrize(
    ("argumentos", "mensagem"),
    [
        (["--start", "2025-13-01"], "argumento --start: data inexistente '2025-13-01'"),
        (["--end", "01/03/2025"], "argumento --end: data inválida '01/03/2025'"),
        (["--format", "pdf"], "argumento --format: opção inválida 'pdf'"),
        (["-v", "-q"], "argumento -q/--quiet: não pode ser usado junto com -v/--verbose"),
        (["--end"], "argumento --end: requer um valor"),
        (["sobrando"], "argumentos não reconhecidos: sobrando"),
    ],
)
def test_argumentos_invalidos(
    csv_exemplo: Path,
    capsys: pytest.CaptureFixture[str],
    argumentos: list[str],
    mensagem: str,
) -> None:
    assert mensagem in erro_de_argumento(capsys, str(csv_exemplo), *argumentos)


def test_sem_arquivo(capsys: pytest.CaptureFixture[str]) -> None:
    assert "argumentos obrigatórios ausentes: arquivo" in erro_de_argumento(capsys)


@pytest.mark.parametrize(
    ("mensagem", "traducao"),
    [
        (
            "ambiguous option: --s could match --start, --sx",
            "opção ambígua: --s pode ser --start, --sx",
        ),
        ("mensagem desconhecida", "mensagem desconhecida"),
    ],
)
def test_traduzir_mensagem_argparse(mensagem: str, traducao: str) -> None:
    assert traduzir_mensagem_argparse(mensagem) == traducao


# --- ajuda e versão --------------------------------------------------------------------


def test_ajuda_em_portugues(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as saida:
        main(["--help"])

    assert saida.value.code == 0
    ajuda = capsys.readouterr().out
    for trecho in ["uso: vendas-cli", "argumento obrigatório:", "exemplos:", "códigos de saída:"]:
        assert trecho in ajuda, trecho


def test_versao(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as saida:
        main(["--version"])

    assert saida.value.code == 0
    assert capsys.readouterr().out == f"vendas-cli {__version__}\n"


def test_python_m_vendas_cli(
    csv_exemplo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["vendas_cli", str(csv_exemplo), "--format", "json"])

    with pytest.raises(SystemExit) as saida:
        runpy.run_module("vendas_cli", run_name="__main__")

    assert saida.value.code == 0
    assert json.loads(capsys.readouterr().out)["valor_total"] == "23357.80"


@pytest.mark.skipif(sys.platform == "win32", reason="caminho de comando POSIX")
def test_comando_instalado(csv_exemplo: Path) -> None:
    comando = Path(sys.executable).parent / "vendas-cli"
    if not comando.exists():
        pytest.skip("vendas-cli não instalado neste ambiente")

    resultado = subprocess.run(
        [str(comando), str(csv_exemplo)], capture_output=True, text=True, check=False
    )

    assert resultado.returncode == 0
    assert resultado.stdout == TEXTO_EXEMPLO + "\n"
