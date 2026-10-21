# vendas-cli: spec

CLI em Python que lê um CSV de vendas e gera relatório em texto (tabela), JSON ou HTML,
com curva ABC, classificação XYZ de demanda, preço praticado e vendas por mês.
Desafio técnico (Python Pleno/Sênior, Petrobras). Enunciado original em `docs/desafio.pdf`.
Tempo estimado pelo desafio: até 2 horas.

## 1. Requisitos do enunciado

**Funcionais**
1. Ler CSV com biblioteca padrão (`csv`, `argparse`, `logging`). Caminho do arquivo por argumento.
2. Calcular:
   - total de vendas por produto;
   - valor total de todas as vendas;
   - produto mais vendido.
3. Filtro opcional por intervalo de data (`--start`, `--end`).
4. Saída `--format text|json` (texto = tabela formatada).

**Qualidade**
- Tipagem estática com `typing`.
- Estrutura modular: no mínimo `parser`, `core`, `output`.
- Tratamento de erro e logs claros (`logging`).
- Instalável via `pyproject.toml`, expondo o comando `vendas-cli`.
- Testes com `pytest`, cobertura mínima de 80%.

**Entrega**
- Repositório público no GitHub.
- `README.md` com instalação e uso.
- Configuração de testes (`pytest.ini` ou `[tool.pytest.ini_options]` no `pyproject.toml`).

**Extras (além do enunciado, que pede "relatórios ricos")**
- Curva ABC dos produtos por valor.
- Classificação XYZ (regularidade da demanda) e matriz ABC-XYZ.
- Preço médio, mínimo e máximo praticado por produto.
- Mês de pico por produto.
- Vendas por mês com variação em relação ao mês anterior (sazonalidade).
- Saída `--format html` (relatório num arquivo único, pronto para abrir ou imprimir em PDF pelo navegador).

## 2. Decisões (o enunciado não define)

| Tema | Decisão |
|---|---|
| Colunas do CSV | `data,produto,quantidade,preco_unitario` (cabeçalho obrigatório, ordem livre) |
| Formato de data | ISO `AAAA-MM-DD`, tanto no CSV quanto em `--start`/`--end` |
| Quantidade e preço | Quantidade inteira `> 0`; preço `>= 0`. Fora disso a linha é inválida |
| Formato do preço | `45.90` (ponto decimal) ou pt-BR entre aspas `"45,90"` / `"1.234,56"` (com vírgula, ponto é milhar). Sem vírgula, `1.234` vale 1,234. `45,90` sem aspas vira coluna extra e a linha é rejeitada. Notação científica, `NaN`, `R$` e afins são inválidos |
| Dinheiro e percentuais | `decimal.Decimal`, nunca `float`. Arredondamento a 2 casas (`ROUND_HALF_UP`) só na saída |
| Valor da venda | `quantidade * preco_unitario` |
| "Total de vendas por produto" | Quantidade somada **e** valor somado por produto |
| "Produto mais vendido" | Maior quantidade. Empate: maior valor; persistindo, ordem alfabética |
| Intervalo de data | Inclusivo nas duas pontas. Só `--start` ou só `--end` é válido |
| Contagem de registros | `validos` = linhas válidas do arquivo; `ignorados` = linhas inválidas; `no_periodo` = válidas que passaram no filtro (base de todos os cálculos) |
| Linha inválida | Log `WARNING` com número da linha e motivo, linha ignorada, segue o processamento |
| Erro fatal | Arquivo inexistente, sem permissão, vazio ou sem coluna obrigatória: log `ERROR`, exit code 1 |
| Sem vendas após filtro | Relatório com totais zerados, `mais_vendido: null`, curva ABC, matriz e meses vazios (exit 0) |
| Encoding | UTF-8 (aceitar BOM via `utf-8-sig`) na entrada e na saída |
| Dependências de runtime | Nenhuma. Só stdlib, inclusive no HTML. Python >= 3.10 |

### 2.1 Curva ABC

- Base: valor total por produto (não quantidade).
- Ordenação: valor decrescente; empate por nome.
- `participacao = valor_produto / valor_total * 100`; `participacao_acumulada` soma as participações exatas até o produto, inclusive.
- Classe pelo acumulado **anterior** ao produto: `< 80` → A; `< 95` → B; senão C. Assim o produto que cruza 80% ainda é A (um produto com 90% do valor é A, não B).
- Limites 80/95 são constantes em `core.py`, não opção de CLI.
- `valor_total == 0` (todos os preços zero): participações `0` e todos classe C.
- Resumo por classe: número de produtos, valor e participação de cada classe (A, B, C sempre presentes, mesmo com zero produtos).

### 2.2 Classificação XYZ

- Mede a regularidade da demanda: coeficiente de variação da **quantidade mensal** do produto, `cv = pstdev / média` (`statistics`, com `Decimal`).
- Série mensal do produto: os mesmos meses de "vendas por mês" (2.4), com zero nos meses em que o produto não vendeu.
- Classe: `cv <= 0,5` → X (estável); `cv <= 1,0` → Y (variável); senão Z (errática). Limites são constantes em `core.py`.
- Série com menos de 3 meses: `cv` e classe `null`, com um log `INFO` ("período curto para XYZ"). A matriz fica toda zerada.
- Matriz ABC-XYZ: contagem de produtos em cada combinação (3×3, todas as células presentes). Produtos sem XYZ ficam fora da matriz.

### 2.3 Preço praticado e mês de pico

- `preco_medio = valor_produto / quantidade_produto` (média ponderada pela quantidade).
- `preco_min` / `preco_max`: menor e maior `preco_unitario` entre as vendas do produto no período.
- `mes_pico`: mês (`AAAA-MM`) com maior quantidade do produto. Empate: o mês mais antigo.

### 2.4 Vendas por mês

- Agrupamento por `AAAA-MM` da data da venda, após o filtro de período.
- Meses sem venda entre o primeiro e o último mês com venda aparecem com zero (a lacuna é informação de sazonalidade). Não se estende até os limites do filtro.
- Ordem cronológica.
- `variacao = (valor_mes - valor_mes_anterior) / valor_mes_anterior * 100`. `null` no primeiro mês e quando o mês anterior teve valor zero.

Exemplo de `vendas.csv` (também em `exemplos/vendas.csv`):

```csv
data,produto,quantidade,preco_unitario
2025-01-10,Notebook,2,3500.00
2025-01-15,Mouse,10,45.90
2025-02-03,Mouse,12,45.90
2025-02-20,Notebook,1,3400.00
2025-03-05,Mouse,9,49.90
2025-04-01,Teclado,5,120.00
2025-04-12,Notebook,3,3450.00
2025-04-18,Mouse,11,49.90
```

Escolhido para mostrar as três classes ABC e as três XYZ. Não tem mês sem venda; esse caso fica nos testes.

## 3. Interface

```
vendas-cli ARQUIVO [--format {text,json,html}] [-o SAIDA] [--start AAAA-MM-DD] [--end AAAA-MM-DD] [-v | -q]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `ARQUIVO` | obrigatório | Caminho do CSV |
| `--format` | `text` | Formato da saída |
| `-o/--output` | stdout | Arquivo de saída (qualquer formato), gravado em UTF-8 |
| `--start` | nenhum | Data inicial (inclusiva) |
| `--end` | nenhum | Data final (inclusiva) |
| `-v/--verbose` | | Log em `DEBUG` |
| `-q/--quiet` | | Só `ERROR` |
| `--version` | | Mostra a versão |

- Relatório vai para **stdout** (ou `-o`); logs vão para **stderr** (o JSON fica limpo para `| jq`).
- Tudo em português: ajuda (`uso:`, grupos de opções, exemplos e códigos de saída no `--help`), erros do argparse (traduzidos em `cli`) e níveis de log (`DEPURAÇÃO`, `INFO`, `AVISO`, `ERRO`), no formato `NIVEL: mensagem`.
- Nomes das opções seguem o enunciado (`--format`, `--start`, `--end`); valores de `--format` também (`text`, `json`, `html`).
- Data inválida ou `--start > --end`: erro do argparse (exit 2).
- Falha ao escrever em `-o` (diretório inexistente, sem permissão): log `ERROR`, exit 1.

**Exit codes**: `0` sucesso · `1` erro de entrada/saída (arquivo, cabeçalho, escrita) · `2` argumento inválido.

## 4. Saídas

Exemplos abaixo com o `vendas.csv` da seção 2, sem filtro.

**text**

```
Relatório de vendas
Período: início a fim
Registros: 8 válidos, 0 ignorados, 8 no período

Produtos (curva ABC)
Produto   Quantidade  Valor (R$)  Part. %  Acum. %  ABC
--------  ----------  ----------  -------  -------  ---
Notebook           6   20.750,00    88,84    88,84  A
Mouse             42    2.007,80     8,60    97,43  B
Teclado            5      600,00     2,57   100,00  C
--------  ----------  ----------  -------  -------  ---
TOTAL             53   23.357,80   100,00

Produto mais vendido: Mouse (42 unidades)

Curva ABC: A 1 produto (88,84%) · B 1 produto (8,60%) · C 1 produto (2,57%)

Demanda e preço
Produto   Preço médio  Preço mín  Preço máx    CV  XYZ  Pico
--------  -----------  ---------  ---------  ----  ---  -------
Notebook     3.458,33   3.400,00   3.500,00  0,75  Y    2025-04
Mouse           47,80      45,90      49,90  0,11  X    2025-02
Teclado        120,00     120,00     120,00  1,73  Z    2025-04

Matriz ABC-XYZ (produtos)
ABC  X  Y  Z
---  -  -  -
A    0  1  0
B    1  0  0
C    0  0  1

Vendas por mês
Mês      Quantidade  Valor (R$)  Variação %
-------  ----------  ----------  ----------
2025-01          12    7.459,00           -
2025-02          13    3.950,80      -47,03
2025-03           9      449,10      -88,63
2025-04          19   11.498,90    2.460,43
```

- Tabelas montadas na mão (sem `tabulate`), colunas alinhadas pela maior largura; números à direita, texto à esquerda.
- Produtos ordenados por valor decrescente (mesma ordem da curva ABC) nas duas tabelas de produto.
- `Acum. %` vem do acumulado exato, por isso pode diferir em 0,01 da soma das `Part. %` arredondadas.
- Período mostra `início`/`fim` quando não há filtro.
- `null` (variação, CV, XYZ) aparece como `-`.
- Sem vendas no período: só o cabeçalho (período e registros) e a linha `Nenhuma venda no período.`.

**json**

```json
{
  "periodo": {"inicio": null, "fim": null},
  "registros": {"validos": 8, "ignorados": 0, "no_periodo": 8},
  "produtos": [
    {"produto": "Notebook", "quantidade": 6, "valor_total": "20750.00",
     "participacao": "88.84", "participacao_acumulada": "88.84", "classe_abc": "A",
     "preco_medio": "3458.33", "preco_min": "3400.00", "preco_max": "3500.00",
     "cv": "0.75", "classe_xyz": "Y", "mes_pico": "2025-04"},
    {"produto": "Mouse", "quantidade": 42, "valor_total": "2007.80",
     "participacao": "8.60", "participacao_acumulada": "97.43", "classe_abc": "B",
     "preco_medio": "47.80", "preco_min": "45.90", "preco_max": "49.90",
     "cv": "0.11", "classe_xyz": "X", "mes_pico": "2025-02"},
    {"produto": "Teclado", "quantidade": 5, "valor_total": "600.00",
     "participacao": "2.57", "participacao_acumulada": "100.00", "classe_abc": "C",
     "preco_medio": "120.00", "preco_min": "120.00", "preco_max": "120.00",
     "cv": "1.73", "classe_xyz": "Z", "mes_pico": "2025-04"}
  ],
  "valor_total": "23357.80",
  "mais_vendido": {"produto": "Mouse", "quantidade": 42},
  "curva_abc": {
    "A": {"produtos": 1, "valor_total": "20750.00", "participacao": "88.84"},
    "B": {"produtos": 1, "valor_total": "2007.80", "participacao": "8.60"},
    "C": {"produtos": 1, "valor_total": "600.00", "participacao": "2.57"}
  },
  "matriz_abc_xyz": {
    "A": {"X": 0, "Y": 1, "Z": 0},
    "B": {"X": 1, "Y": 0, "Z": 0},
    "C": {"X": 0, "Y": 0, "Z": 1}
  },
  "vendas_por_mes": [
    {"mes": "2025-01", "quantidade": 12, "valor_total": "7459.00", "variacao": null},
    {"mes": "2025-02", "quantidade": 13, "valor_total": "3950.80", "variacao": "-47.03"},
    {"mes": "2025-03", "quantidade": 9, "valor_total": "449.10", "variacao": "-88.63"},
    {"mes": "2025-04", "quantidade": 19, "valor_total": "11498.90", "variacao": "2460.43"}
  ]
}
```

- Valores monetários, percentuais e CV como string (preserva precisão do `Decimal`).
- `periodo.inicio`/`fim` = `null` quando o filtro não foi passado.

**html**

Arquivo único e autocontido: CSS inline num `<style>`, sem JavaScript e sem recurso externo (fonte, CDN, imagem). Abre offline e imprime em PDF pelo navegador.

Montagem só com stdlib: `string.Template` para o esqueleto da página e funções pequenas que geram cada `<table>`. Todo texto vindo do CSV (nome de produto) passa por `html.escape`.

Conteúdo, na ordem:
1. Cabeçalho: título, período, registros válidos/ignorados/no período, data de geração.
2. Cards: valor total, quantidade total, produto mais vendido.
3. Tabela "Produtos (curva ABC)" com linha de total; badge colorido por classe ABC.
4. Tabela "Demanda e preço"; badge por classe XYZ.
5. Matriz ABC-XYZ como grade 3×3 com a contagem em cada célula e fundo mais forte quanto maior a contagem.
6. Tabela "Vendas por mês"; variação positiva em verde, negativa em vermelho.
7. Rodapé: legenda curta das classes (A/B/C e X/Y/Z) e versão do `vendas-cli`.

- Números no padrão pt-BR, iguais ao text; `null` aparece como `–`.
- Tabelas largas rolam na horizontal dentro da própria seção em telas estreitas; cards empilham.
- Período com menos de 3 meses: nota "XYZ não calculado" abaixo da tabela de demanda.
- `<html lang="pt-BR">`, `<meta charset="utf-8">`, colunas numéricas alinhadas à direita.
- `@media print`: sem sombras/fundos pesados, tabelas sem quebra no meio da linha.
- Sem vendas: cabeçalho, cards zerados e a mensagem "Nenhuma venda no período"; tabelas omitidas.
- Sem gráficos nesta versão (ver seção 9).

## 5. Arquitetura

```
vendas-cli/
├── pyproject.toml          # build (setuptools), script vendas-cli, extra [dev], pytest, coverage, mypy, ruff
├── README.md
├── SPEC.md
├── docs/desafio.pdf
├── exemplos/vendas.csv
├── src/vendas_cli/
│   ├── __init__.py         # __version__
│   ├── __main__.py         # python -m vendas_cli
│   ├── models.py           # dataclasses: Venda, ResumoProduto, ResumoClasse, ResumoMes, Relatorio
│   ├── normalizer.py       # texto -> date | int | Decimal (data, quantidade, preço pt-BR)
│   ├── parser.py           # CSV -> list[Venda] + contagem de ignorados; regras de linha válida
│   ├── core.py             # filtro, agregações, ABC, XYZ, preço, pico, vendas por mês -> Relatorio
│   ├── formatacao.py       # números, período e plural em pt-BR (comum a text e html)
│   ├── output.py           # Relatorio -> str (text | json), despacha html
│   ├── relatorio_html.py   # Relatorio -> str (html); nome evita confusão com o módulo html da stdlib
│   └── cli.py              # argparse, logging, orquestração, escrita da saída, exit codes
└── tests/
    ├── conftest.py         # fixtures de CSV em tmp_path
    ├── test_normalizer.py
    ├── test_parser.py
    ├── test_core.py
    ├── test_formatacao.py
    ├── test_output.py
    ├── test_relatorio_html.py
    └── test_cli.py
```

Fluxo: `cli` → `parser.ler_vendas(path)` → `core.gerar_relatorio(vendas, inicio=, fim=, ignorados=)` (filtra internamente) → `output.formatar(relatorio, formato)` → stdout / `-o`.

Modelos:
- `ClasseABC = Literal["A", "B", "C"]`, `ClasseXYZ = Literal["X", "Y", "Z"]`.
- `ResumoProduto(produto, quantidade, valor_total, participacao, participacao_acumulada, classe_abc, preco_medio, preco_min, preco_max, cv: Decimal | None, classe_xyz: ClasseXYZ | None, mes_pico: str)`.
- `ResumoClasse(classe: ClasseABC, produtos: int, valor_total: Decimal, participacao: Decimal)`.
- `ResumoMes(mes: str, quantidade: int, valor_total: Decimal, variacao: Decimal | None)`.
- `Relatorio` com `produtos`, `quantidade_total`, `participacao_total` (soma exata das participações, usada na linha de total), `curva_abc: tuple[ResumoClasse, ...]`, `matriz_abc_xyz: Mapping[ClasseABC, Mapping[ClasseXYZ, int]]` e `vendas_por_mes: tuple[ResumoMes, ...]`, além dos campos do enunciado.

Regras de desenho:
- `normalizer` converte texto em tipo e levanta `ValueError` com mensagem pronta para log; não conhece CSV nem regra de negócio. `parser` aplica as regras (quantidade `> 0`, preço `>= 0`, coluna extra) e expõe `converter_linha` para testar linha a linha sem arquivo. `cli` reaproveita `normalizar_data` em `--start`/`--end`.
- `core`, `output` e `relatorio_html` são funções puras (sem I/O); a data de geração do HTML entra como parâmetro (testável). Quem escreve é o `cli`.
- `core` expõe as peças separadas para testar isoladamente: `filtrar_por_periodo`, `agregar_por_mes`, `classificar_abc` (valores por produto), `classificar_xyz` (uma série mensal), `mes_de_pico`, `resumir_abc`, `montar_matriz`, `escolher_mais_vendido`. `gerar_relatorio(vendas, inicio=, fim=, ignorados=)` aplica o filtro e junta tudo. Meses são calculados primeiro porque o XYZ depende deles.
- Formatação pt-BR fica em `formatacao`, usada por `output` e `relatorio_html` (evita import circular, já que `output` despacha para o HTML).
- Só `cli` conhece `argparse`, `sys.exit` e configura o `logging`. Os outros módulos usam `logging.getLogger(__name__)`.
- Erros fatais do parser sobem como exceção própria (`ErroLeituraCSV`); `cli` captura e converte em exit 1.
- Dataclasses `frozen=True`, tipos completos, `mypy --strict` passando.

## 6. Testes

- `pytest` + `pytest-cov`, `--cov-fail-under=80` configurado no `pyproject.toml`.
- Casos mínimos:
  - **parser**: CSV válido; cabeçalho faltando coluna; arquivo inexistente; arquivo vazio; linha com data/quantidade/preço inválido (inclui quantidade `<= 0` e preço negativo) é ignorada e logada (`caplog`); linha com coluna extra; BOM; colunas em outra ordem.
  - **parser / `converter_linha`**: linha válida; cada campo vazio; coluna extra; quantidade `0` e negativa; preço negativo; preço `0` é válido.
  - **normalizer**: data válida, fora do formato (`2025-1-5`) e inexistente (`2025-02-30`); quantidade `5`, ` 7 `, inválidas `+5`, `2.0`, `1_000`; preço `45.90`, `45`, `45,90`, `1.234,56`, `1.234` (= 1,234), inválidos `1,234.56`, `1.23,4`, `1e3`, `NaN`, `R$ 10`, `45,`.
  - **core**: totais por produto; valor total; mais vendido; desempate; filtro só start, só end, ambos, inclusivo nas pontas; lista vazia.
  - **core / ABC**: classes do exemplo (A, B, C); produto único com 100% é A; produto que cruza 80% é A; desempate por nome; valor total zero; resumo por classe com classe vazia.
  - **core / XYZ**: classes do exemplo (X, Y, Z); limites exatos 0,5 e 1,0; produto que não vendeu em alguns meses conta zero; menos de 3 meses dá `null` e loga `INFO`; matriz do exemplo e matriz zerada.
  - **core / preço e pico**: preço médio ponderado; min/max; produto com um único preço; pico com empate fica no mês mais antigo.
  - **core / mês**: agrupamento; mês sem venda no meio vira zero; variação positiva e negativa; `null` no primeiro mês e após mês zerado; ordem cronológica.
  - **formatacao**: milhar e decimal pt-BR; `ROUND_HALF_UP` (`-47,025` → `-47,03`); sem `-0,00`; período com e sem limites; plural.
  - **output**: text e JSON do exemplo batem com a seção 4; JSON válido e com o schema acima; `null` vira `-` no text; caso vazio.
  - **relatorio_html**: parseia sem erro com `html.parser.HTMLParser`; contém totais, classes e meses do exemplo; produto `<script>` sai escapado; sem `http://`/`https://`/`<script` no documento; caso vazio mostra a mensagem.
  - **cli**: ajuda e mensagens de erro em português; `--version`; `python -m vendas_cli`; logs não duplicam ao chamar `main` duas vezes; `-q` oculta avisos e `-v` mostra `INFO`/`DEPURAÇÃO`; `main([...])` retorna 0/1; `--start > --end` gera exit 2; `-o` grava o arquivo em UTF-8; `-o` em diretório inexistente gera exit 1; JSON em stdout e logs em stderr (`capsys`).

## 7. Ferramentas de dev (extras `[dev]`)

`pytest`, `pytest-cov`, `mypy`, `ruff`. Opcional: GitHub Actions rodando `ruff`, `mypy` e `pytest` em 3.10–3.12.

## 8. README

- O que faz (em tópicos) e exemplo de saída (text e print do HTML).
- Instalação: `pip install .` (e `pip install -e ".[dev]"` para desenvolver).
- Uso com os 3 exemplos do enunciado e um com `--format html -o relatorio.html`.
- Formato esperado do CSV.
- Como ler a curva ABC, a XYZ, a matriz ABC-XYZ (ex.: AX = alto valor e demanda estável, reposição automática; AZ = alto valor e demanda errática, atenção no estoque) e as vendas por mês.
- Como rodar testes e cobertura.
- Decisões tomadas (resumo da seção 2), incluindo por que não pandas: o enunciado pede stdlib na leitura e o volume não justifica; seria a escolha para bases grandes.

## 9. Fora do escopo

Gráficos (próximo passo natural: SVG inline no HTML, ainda sem dependência), PDF nativo, templates externos (Jinja2), outros formatos de entrada (Excel, Parquet), pandas/numpy, limites ABC/XYZ configuráveis, previsão/tendência, concentração (HHI), recência, comparação com período anterior, dia da semana, banco de dados, múltiplas moedas, delimitador configurável.

## 10. Pronto quando

- [x] `pip install .` e `vendas-cli exemplos/vendas.csv` funcionam num venv limpo.
- [x] Os 3 comandos do enunciado rodam sem erro.
- [x] `vendas-cli exemplos/vendas.csv --format html -o relatorio.html` gera um arquivo que abre offline e imprime legível.
- [x] Saídas text e json do exemplo batem com a seção 4.
- [x] `pytest` passa com cobertura >= 80%.
- [x] `mypy --strict src` e `ruff check` limpos.
- [x] README completo, repo público no GitHub.
