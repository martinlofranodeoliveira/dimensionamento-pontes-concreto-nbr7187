"""Interface de linha de comando (CLI) para dimensionamento de pontes rodoviárias.

ABNT NBR 7187:2021 / ABNT NBR 7188:2013 / ABNT NBR 6118:2023.
"""

import argparse
import os
import sys
from fractions import Fraction

from .models import (
    ClasseTremTipo,
    ClasseConcreto,
    AcoArmadura,
    ParametrosVao,
    GeometriaSecao,
    AparelhoApoio,
)
from .calculator import calcular_ponte_rodoviaria
from .codecs import codificar_json_estrito
from .exporters import (
    exportar_memorial_texto,
    exportar_csv_sanitizado,
    exportar_svg_painel,
    gerar_pacote_zip,
)


def converter_fracao(valor_str: str) -> Fraction:
    """Converte uma string contendo decimal ou fração para Fraction exata sem float intermediário."""
    if "/" in valor_str:
        partes = valor_str.split("/")
        return Fraction(int(partes[0].strip()), int(partes[1].strip()))
    if "." in valor_str:
        inteiro, dec = valor_str.split(".")
        den = 10 ** len(dec)
        num = int(inteiro) * den + int(dec) if int(inteiro) >= 0 else int(inteiro) * den - int(dec)
        return Fraction(num, den)
    return Fraction(int(valor_str), 1)


def criar_argumentos() -> argparse.ArgumentParser:
    """Cria e configura o analisador de argumentos da CLI."""
    parser = argparse.ArgumentParser(
        prog="dimensionamento-pontes",
        description="Dimensionamento de Pontes Rodoviárias de Concreto conforme NBR 7187, NBR 7188 e NBR 6118.",
    )
    parser.add_argument(
        "--calcular",
        action="store_true",
        help="Executa o dimensionamento estrutural e emite o resumo de resultados.",
    )
    parser.add_argument(
        "--vao",
        type=str,
        default="25",
        help="Comprimento do vão livre L da ponte em metros (padrão: 25).",
    )
    parser.add_argument(
        "--largura-pista",
        type=str,
        default="7.2",
        help="Largura útil da pista de rolamento em metros (padrão: 7.20).",
    )
    parser.add_argument(
        "--largura-passeios",
        type=str,
        default="2.0",
        help="Largura total dos passeios laterais em metros (padrão: 2.00).",
    )
    parser.add_argument(
        "--faixas",
        type=int,
        default=2,
        help="Número de faixas de tráfego rodoviário (padrão: 2).",
    )
    parser.add_argument(
        "--altura-viga",
        type=str,
        default="1.8",
        help="Altura total h da viga principal em metros (padrão: 1.80).",
    )
    parser.add_argument(
        "--largura-alma",
        type=str,
        default="0.45",
        help="Largura bw da alma da viga em metros (padrão: 0.45).",
    )
    parser.add_argument(
        "--largura-mesa",
        type=str,
        default="2.2",
        help="Largura colaborante bf da mesa superior em metros (padrão: 2.20).",
    )
    parser.add_argument(
        "--espessura-mesa",
        type=str,
        default="0.20",
        help="Espessura hf da mesa/laje superior em metros (padrão: 0.20).",
    )
    parser.add_argument(
        "--d-util",
        type=str,
        default="1.65",
        help="Altura útil d da armadura de tração em metros (padrão: 1.65).",
    )
    parser.add_argument(
        "--fck",
        type=int,
        choices=[30, 35, 40, 45, 50],
        default=35,
        help="Resistência característica do concreto fck em MPa (padrão: 35).",
    )
    parser.add_argument(
        "--trem-tipo",
        choices=["TB-450", "TB-300", "TB-120", "PASSARELA"],
        default="TB-450",
        help="Classe normativa do trem-tipo rodoviário (padrão: TB-450).",
    )
    parser.add_argument(
        "--exportar-todos",
        action="store_true",
        help="Exporta todos os relatórios (Memorial, CSV, JSON, SVG e ZIP).",
    )
    parser.add_argument(
        "--saida-dir",
        type=str,
        default="relatorios",
        help="Diretório onde salvar os arquivos exportados (padrão: ./relatorios).",
    )
    return parser


def main() -> int:
    """Ponto de entrada principal da CLI."""
    parser = criar_argumentos()
    args = parser.parse_args()

    if not args.calcular and not args.exportar_todos:
        parser.print_help()
        return 0

    try:
        vao_f = converter_fracao(args.vao)
        lp_f = converter_fracao(args.largura_pista)
        lpass_f = converter_fracao(args.largura_passeios)
        h_f = converter_fracao(args.altura_viga)
        bw_f = converter_fracao(args.largura_alma)
        bf_f = converter_fracao(args.largura_mesa)
        hf_f = converter_fracao(args.espessura_mesa)
        d_f = converter_fracao(args.d_util)

        vao = ParametrosVao(
            vao_livre=vao_f,
            largura_pista=lp_f,
            largura_passeios=lpass_f,
            num_faixas=args.faixas,
            espessura_pavimento=Fraction(7, 100),  # 7 cm
            peso_barreiras=Fraction(12, 1),       # 12 kN/m
            num_vigas=2,
        )

        secao = GeometriaSecao(
            altura_total=h_f,
            largura_alma=bw_f,
            largura_mesa=bf_f,
            espessura_mesa=hf_f,
            cobrimento=Fraction(4, 100),          # 4 cm
            d_util=d_f,
        )

        apoio = AparelhoApoio(
            comprimento_a=Fraction(35, 100),      # 35 cm
            largura_b=Fraction(45, 100),          # 45 cm
            espessura_elastometro=Fraction(6, 100), # 6 cm
            tensao_admissivel=Fraction(10000, 1), # 10.000 kPa = 10 MPa
        )

        mapa_tt = {
            "TB-450": ClasseTremTipo.TB_450,
            "TB-300": ClasseTremTipo.TB_300,
            "TB-120": ClasseTremTipo.TB_120,
            "PASSARELA": ClasseTremTipo.PASSARELA,
        }
        trem_tipo_enum = mapa_tt[args.trem_tipo]

        mapa_fck = {
            30: ClasseConcreto.C30,
            35: ClasseConcreto.C35,
            40: ClasseConcreto.C40,
            45: ClasseConcreto.C45,
            50: ClasseConcreto.C50,
        }
        fck_enum = mapa_fck[args.fck]

        res = calcular_ponte_rodoviaria(
            vao=vao,
            secao=secao,
            apoio=apoio,
            trem_tipo=trem_tipo_enum,
            fck=fck_enum,
            aco=AcoArmadura.CA_50,
        )

        # Imprime o memorial em stdout
        memorial = exportar_memorial_texto(
            vao=vao,
            secao=secao,
            apoio=apoio,
            resultado=res,
            trem_tipo=trem_tipo_enum,
            fck=fck_enum,
            aco=AcoArmadura.CA_50,
        )
        print(memorial)

        if args.exportar_todos:
            os.makedirs(args.saida_dir, exist_ok=True)
            caminho_mem = os.path.join(args.saida_dir, "memorial_calculo.txt")
            caminho_csv = os.path.join(args.saida_dir, "resultados.csv")
            caminho_json = os.path.join(args.saida_dir, "resultados.json")
            caminho_svg = os.path.join(args.saida_dir, "painel_dimensionamento.svg")
            caminho_zip = os.path.join(args.saida_dir, "pacote_ponte.zip")

            with open(caminho_mem, "w", encoding="utf-8") as f:
                f.write(memorial)

            with open(caminho_csv, "w", encoding="utf-8") as f:
                f.write(exportar_csv_sanitizado(res))

            with open(caminho_json, "w", encoding="utf-8") as f:
                f.write(codificar_json_estrito(res))

            with open(caminho_svg, "w", encoding="utf-8") as f:
                f.write(exportar_svg_painel(vao, secao, apoio, res, trem_tipo_enum, fck_enum, AcoArmadura.CA_50))

            if os.path.exists(caminho_zip):
                os.remove(caminho_zip)
            gerar_pacote_zip(caminho_zip, vao, secao, apoio, res, trem_tipo_enum, fck_enum, AcoArmadura.CA_50)

            print(f"Artefatos exportados com sucesso em '{args.saida_dir}'.")

        return 0 if res.aprovado_geral else 1

    except Exception as e:
        sys.stderr.write(f"Erro operacional: {e}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
