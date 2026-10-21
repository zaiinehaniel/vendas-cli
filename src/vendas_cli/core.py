"""Regras de negócio: filtro por período, agregações, curva ABC, XYZ e vendas por mês.

Funções puras, sem I/O. Valores ficam em ``Decimal`` exato; arredondamento só na saída.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import mean, pstdev
from typing import NamedTuple

from vendas_cli.models import (
    ClasseABC,
    ClasseXYZ,
    Relatorio,
    ResumoClasse,
    ResumoMes,
    ResumoProduto,
    Venda,
)

logger = logging.getLogger(__name__)

LIMITE_A = Decimal(80)
LIMITE_B = Decimal(95)
LIMITE_X = Decimal("0.5")
LIMITE_Y = Decimal("1.0")
MESES_MINIMOS_XYZ = 3

CLASSES_ABC: tuple[ClasseABC, ...] = ("A", "B", "C")
CLASSES_XYZ: tuple[ClasseXYZ, ...] = ("X", "Y", "Z")

_ZERO = Decimal(0)
_CEM = Decimal(100)


class ClassificacaoABC(NamedTuple):
    participacao: Decimal
    participacao_acumulada: Decimal
    classe: ClasseABC


class ClassificacaoXYZ(NamedTuple):
    cv: Decimal | None
    classe: ClasseXYZ | None


@dataclass
class _Acumulado:
    quantidade: int = 0
    valor: Decimal = _ZERO
    preco_min: Decimal | None = None
    preco_max: Decimal | None = None


def filtrar_por_periodo(
    vendas: Iterable[Venda], inicio: date | None = None, fim: date | None = None
) -> tuple[Venda, ...]:
    """Mantém as vendas entre ``inicio`` e ``fim``, inclusive. ``None`` = sem limite."""
    return tuple(
        venda
        for venda in vendas
        if (inicio is None or venda.data >= inicio) and (fim is None or venda.data <= fim)
    )


def chave_mes(data: date) -> str:
    return f"{data.year:04d}-{data.month:02d}"


def meses_entre(primeiro: date, ultimo: date) -> tuple[str, ...]:
    """Todos os meses ``AAAA-MM`` de ``primeiro`` a ``ultimo``, inclusive."""
    meses: list[str] = []
    ano, mes = primeiro.year, primeiro.month
    while (ano, mes) <= (ultimo.year, ultimo.month):
        meses.append(f"{ano:04d}-{mes:02d}")
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return tuple(meses)


def agregar_por_mes(vendas: Sequence[Venda]) -> tuple[ResumoMes, ...]:
    """Totais por mês, com meses sem venda (entre o primeiro e o último) zerados."""
    if not vendas:
        return ()

    quantidade: dict[str, int] = defaultdict(int)
    valor: dict[str, Decimal] = defaultdict(Decimal)
    for venda in vendas:
        mes = chave_mes(venda.data)
        quantidade[mes] += venda.quantidade
        valor[mes] += venda.valor

    datas = [venda.data for venda in vendas]
    resumos: list[ResumoMes] = []
    anterior: Decimal | None = None
    for mes in meses_entre(min(datas), max(datas)):
        atual = valor[mes]
        variacao = None if not anterior else (atual - anterior) / anterior * _CEM
        resumos.append(ResumoMes(mes, quantidade[mes], atual, variacao))
        anterior = atual
    return tuple(resumos)


def classificar_abc(valores: Mapping[str, Decimal]) -> dict[str, ClassificacaoABC]:
    """Curva ABC por valor. Devolve os produtos em ordem de valor decrescente (empate: nome).

    A classe sai do acumulado *anterior* ao produto, então quem cruza 80% ainda é A.
    """
    ordenados = sorted(valores.items(), key=lambda item: (-item[1], item[0]))
    total = sum(valores.values(), _ZERO)

    resultado: dict[str, ClassificacaoABC] = {}
    acumulado = _ZERO
    for produto, valor in ordenados:
        if total == 0:
            resultado[produto] = ClassificacaoABC(_ZERO, _ZERO, "C")
            continue
        participacao = valor / total * _CEM
        classe: ClasseABC = "A" if acumulado < LIMITE_A else "B" if acumulado < LIMITE_B else "C"
        acumulado += participacao
        resultado[produto] = ClassificacaoABC(participacao, acumulado, classe)
    return resultado


def classificar_xyz(serie: Sequence[int]) -> ClassificacaoXYZ:
    """Classe XYZ pelo coeficiente de variação da quantidade mensal.

    Série com menos de ``MESES_MINIMOS_XYZ`` meses (ou toda zerada) fica sem classe.
    """
    if len(serie) < MESES_MINIMOS_XYZ:
        return ClassificacaoXYZ(None, None)
    valores = [Decimal(quantidade) for quantidade in serie]
    media = mean(valores)
    if media == 0:
        return ClassificacaoXYZ(None, None)
    cv = pstdev(valores) / media
    classe: ClasseXYZ = "X" if cv <= LIMITE_X else "Y" if cv <= LIMITE_Y else "Z"
    return ClassificacaoXYZ(cv, classe)


def mes_de_pico(quantidade_por_mes: Mapping[str, int]) -> str:
    """Mês com maior quantidade; empate fica com o mais antigo."""
    return min(quantidade_por_mes, key=lambda mes: (-quantidade_por_mes[mes], mes))


def resumir_abc(produtos: Iterable[ResumoProduto]) -> tuple[ResumoClasse, ...]:
    """Totais por classe ABC. As três classes sempre aparecem."""
    contagem: dict[ClasseABC, int] = dict.fromkeys(CLASSES_ABC, 0)
    valor: dict[ClasseABC, Decimal] = dict.fromkeys(CLASSES_ABC, _ZERO)
    participacao: dict[ClasseABC, Decimal] = dict.fromkeys(CLASSES_ABC, _ZERO)
    for produto in produtos:
        contagem[produto.classe_abc] += 1
        valor[produto.classe_abc] += produto.valor_total
        participacao[produto.classe_abc] += produto.participacao
    return tuple(
        ResumoClasse(classe, contagem[classe], valor[classe], participacao[classe])
        for classe in CLASSES_ABC
    )


def montar_matriz(
    produtos: Iterable[ResumoProduto],
) -> dict[ClasseABC, dict[ClasseXYZ, int]]:
    """Contagem de produtos por combinação ABC-XYZ; produtos sem XYZ ficam de fora."""
    matriz: dict[ClasseABC, dict[ClasseXYZ, int]] = {
        abc: dict.fromkeys(CLASSES_XYZ, 0) for abc in CLASSES_ABC
    }
    for produto in produtos:
        if produto.classe_xyz is not None:
            matriz[produto.classe_abc][produto.classe_xyz] += 1
    return matriz


def escolher_mais_vendido(produtos: Iterable[ResumoProduto]) -> ResumoProduto | None:
    """Maior quantidade; empate por maior valor e depois ordem alfabética."""
    return min(
        produtos,
        key=lambda produto: (-produto.quantidade, -produto.valor_total, produto.produto),
        default=None,
    )


def gerar_relatorio(
    vendas: Sequence[Venda],
    *,
    inicio: date | None = None,
    fim: date | None = None,
    ignorados: int = 0,
) -> Relatorio:
    """Monta o relatório completo a partir de todas as vendas válidas lidas.

    ``validos`` conta todas as vendas recebidas; ``no_periodo``, as que passaram no filtro.
    """
    no_periodo = filtrar_por_periodo(vendas, inicio, fim)
    meses = agregar_por_mes(no_periodo)
    nomes_meses = [resumo.mes for resumo in meses]
    if meses and len(meses) < MESES_MINIMOS_XYZ:
        logger.info("período curto para XYZ: %d mês(es), mínimo %d", len(meses), MESES_MINIMOS_XYZ)

    acumulados: dict[str, _Acumulado] = defaultdict(_Acumulado)
    quantidade_mes: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(nomes_meses, 0))
    for venda in no_periodo:
        acumulado = acumulados[venda.produto]
        acumulado.quantidade += venda.quantidade
        acumulado.valor += venda.valor
        if acumulado.preco_min is None or venda.preco_unitario < acumulado.preco_min:
            acumulado.preco_min = venda.preco_unitario
        if acumulado.preco_max is None or venda.preco_unitario > acumulado.preco_max:
            acumulado.preco_max = venda.preco_unitario
        quantidade_mes[venda.produto][chave_mes(venda.data)] += venda.quantidade

    abc = classificar_abc({nome: acumulado.valor for nome, acumulado in acumulados.items()})

    produtos: list[ResumoProduto] = []
    for nome, classificacao in abc.items():
        acumulado = acumulados[nome]
        # preco_min/max são preenchidos na primeira venda do produto
        assert acumulado.preco_min is not None and acumulado.preco_max is not None
        xyz = classificar_xyz(list(quantidade_mes[nome].values()))
        produtos.append(
            ResumoProduto(
                produto=nome,
                quantidade=acumulado.quantidade,
                valor_total=acumulado.valor,
                participacao=classificacao.participacao,
                participacao_acumulada=classificacao.participacao_acumulada,
                classe_abc=classificacao.classe,
                preco_medio=acumulado.valor / acumulado.quantidade,
                preco_min=acumulado.preco_min,
                preco_max=acumulado.preco_max,
                cv=xyz.cv,
                classe_xyz=xyz.classe,
                mes_pico=mes_de_pico(quantidade_mes[nome]),
            )
        )

    return Relatorio(
        inicio=inicio,
        fim=fim,
        validos=len(vendas),
        ignorados=ignorados,
        no_periodo=len(no_periodo),
        produtos=tuple(produtos),
        valor_total=sum((produto.valor_total for produto in produtos), _ZERO),
        quantidade_total=sum(produto.quantidade for produto in produtos),
        participacao_total=sum((produto.participacao for produto in produtos), _ZERO),
        mais_vendido=escolher_mais_vendido(produtos),
        curva_abc=resumir_abc(produtos),
        matriz_abc_xyz=montar_matriz(produtos),
        vendas_por_mes=meses,
    )
