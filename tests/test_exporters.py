"""Testes unitários dos exportadores de dados e relatórios do dimensionamento de pontes.

Valida memorial descritivo, sanitização contra injeção de fórmulas CSV, painel SVG e integridade de pacote ZIP.
"""

import os
import tempfile
import unittest
import zipfile
from fractions import Fraction

from dimensionamento_pontes_concreto_nbr7187.models import (
    ClasseTremTipo,
    ClasseConcreto,
    AcoArmadura,
    ParametrosVao,
    GeometriaSecao,
    AparelhoApoio,
)
from dimensionamento_pontes_concreto_nbr7187.calculator import calcular_ponte_rodoviaria
from dimensionamento_pontes_concreto_nbr7187.exporters import (
    sanitizar_campo_csv,
    exportar_memorial_texto,
    exportar_csv_sanitizado,
    exportar_svg_painel,
    gerar_pacote_zip,
)


class TesteExportadoresPontes(unittest.TestCase):
    """Bateria de testes dos exportadores técnicos."""

    def setUp(self):
        self.vao = ParametrosVao(
            vao_livre=Fraction(25, 1),
            largura_pista=Fraction(72, 10),
            largura_passeios=Fraction(2, 1),
            num_faixas=2,
            espessura_pavimento=Fraction(7, 100),
            peso_barreiras=Fraction(12, 1),
            num_vigas=2,
        )
        self.secao = GeometriaSecao(
            altura_total=Fraction(18, 10),
            largura_alma=Fraction(45, 100),
            largura_mesa=Fraction(22, 10),
            espessura_mesa=Fraction(2, 10),
            cobrimento=Fraction(4, 100),
            d_util=Fraction(165, 100),
        )
        self.apoio = AparelhoApoio(
            comprimento_a=Fraction(35, 100),
            largura_b=Fraction(45, 100),
            espessura_elastometro=Fraction(6, 100),
            tensao_admissivel=Fraction(10000, 1),
        )
        self.resultado = calcular_ponte_rodoviaria(self.vao, self.secao, self.apoio)

    def test_sanitizacao_formula_csv(self):
        """Campos que começam com =, +, -, @, \\t, \\r devem receber prefixo de aspa simples."""
        self.assertEqual(sanitizar_campo_csv("=1+1"), "'=1+1")
        self.assertEqual(sanitizar_campo_csv("+CMD"), "'+CMD")
        self.assertEqual(sanitizar_campo_csv("-100"), "'-100")
        self.assertEqual(sanitizar_campo_csv("@cmd"), "'@cmd")
        self.assertEqual(sanitizar_campo_csv("\tsoma"), "'\tsoma")
        self.assertEqual(sanitizar_campo_csv("\rretorno"), "'\rretorno")
        self.assertEqual(sanitizar_campo_csv("TB-450"), "TB-450")

    def test_memorial_descritivo_texto(self):
        """O memorial deve conter as seções normativas obrigatórias em português."""
        memorial = exportar_memorial_texto(self.vao, self.secao, self.apoio, self.resultado)
        self.assertIn("LOFRANO TECNOLOGIA", memorial)
        self.assertIn("ABNT NBR 7187:2021", memorial)
        self.assertIn("ABNT NBR 7188:2013", memorial)
        self.assertIn("TREM-TIPO TB-450", memorial)
        self.assertIn("COEFICIENTES DE MAJORAÇÃO DINÂMICA", memorial)
        self.assertIn("MOMENTO FLETOR DE CÁLCULO", memorial)
        self.assertIn("VERIFICAÇÃO DE FADIGA DA ARMADURA", memorial)
        self.assertIn("APROVADO EM TODOS OS CRITÉRIOS", memorial)

    def test_csv_sanitizado_conteudo(self):
        """O CSV deve possuir cabeçalho e registros de todos os parâmetros."""
        csv_str = exportar_csv_sanitizado(self.resultado)
        linhas = csv_str.strip().split("\n")
        self.assertGreater(len(linhas), 10)
        self.assertEqual(linhas[0], "Parametro;Valor_Racional;Valor_Decimal;Unidade;Conforme")
        self.assertTrue(any("CIV" in linha for linha in linhas))
        self.assertTrue(any("Momento_Calculo_Md" in linha for linha in linhas))

    def test_svg_painel_dimensoes_e_elementos(self):
        """O painel SVG deve possuir resolução 1440x900 e elementos visuais de engenharia."""
        svg = exportar_svg_painel(self.vao, self.secao, self.apoio, self.resultado)
        self.assertIn('viewBox="0 0 1440 900"', svg)
        self.assertIn('width="1440"', svg)
        self.assertIn('height="900"', svg)
        self.assertIn("LOFRANO TECNOLOGIA", svg)
        self.assertIn("VEÍCULO TB-450", svg)
        self.assertIn("150 kN", svg)
        self.assertIn("Neoprene", svg)
        self.assertIn("</svg>", svg)

    def test_pacote_zip_determinismo_e_conteudo(self):
        """Gera o arquivo ZIP e valida a presença dos 4 artefatos com timestamp fixo (2026, 1, 1, 0, 0, 0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_zip = os.path.join(tmpdir, "pacote_teste.zip")
            gerar_pacote_zip(caminho_zip, self.vao, self.secao, self.apoio, self.resultado)

            self.assertTrue(os.path.exists(caminho_zip))
            with zipfile.ZipFile(caminho_zip, "r") as zf:
                nomes = zf.namelist()
                self.assertIn("memorial_descritivo_ponte.txt", nomes)
                self.assertIn("resultados_dimensionamento.csv", nomes)
                self.assertIn("resultados_dimensionamento.json", nomes)
                self.assertIn("painel_dimensionamento_ponte.svg", nomes)

                for info in zf.infolist():
                    self.assertEqual(info.date_time, (2026, 1, 1, 0, 0, 0))

    def test_pacote_zip_com_arquivo_existente_falha_com_o_excl(self):
        """A flag os.O_EXCL deve impedir sobrescrita acidental se o arquivo já existir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_zip = os.path.join(tmpdir, "pacote_existente.zip")
            with open(caminho_zip, "wb") as f:
                f.write(b"pre-existente")

            with self.assertRaises(FileExistsError):
                gerar_pacote_zip(caminho_zip, self.vao, self.secao, self.apoio, self.resultado)


if __name__ == "__main__":
    unittest.main()
