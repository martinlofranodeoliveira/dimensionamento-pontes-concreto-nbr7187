"""Testes unitários da interface de linha de comando (CLI) de dimensionamento de pontes.

ABNT NBR 7187 / NBR 7188.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction

from dimensionamento_pontes_concreto_nbr7187.cli import converter_fracao


class TesteCLIPontes(unittest.TestCase):
    """Bateria de testes da CLI."""

    def test_conversor_fracao(self):
        """Testa conversão de strings para Fraction exata sem float."""
        self.assertEqual(converter_fracao("25"), Fraction(25, 1))
        self.assertEqual(converter_fracao("7.2"), Fraction(72, 10))
        self.assertEqual(converter_fracao("0.45"), Fraction(45, 100))
        self.assertEqual(converter_fracao("481/375"), Fraction(481, 375))

    def test_cli_help(self):
        """CLI deve responder a --help com código 0."""
        cmd = [sys.executable, "-m", "dimensionamento_pontes_concreto_nbr7187.cli", "--help"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/martin/SITES/dimensionamento-pontes-concreto-nbr7187/src")
        self.assertEqual(res.returncode, 0)
        self.assertIn("dimensionamento-pontes", res.stdout)
        self.assertIn("--calcular", res.stdout)

    def test_cli_calcular_padrao(self):
        """CLI deve executar dimensionamento padrão com --calcular e retornar 0."""
        cmd = [sys.executable, "-m", "dimensionamento_pontes_concreto_nbr7187.cli", "--calcular"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/martin/SITES/dimensionamento-pontes-concreto-nbr7187/src")
        self.assertEqual(res.returncode, 0)
        self.assertIn("MEMORIAL DE CÁLCULO ESTRUTURAL DE PONTE RODOVIÁRIA DE CONCRETO", res.stdout)
        self.assertIn("APROVADO EM TODOS OS CRITÉRIOS", res.stdout)

    def test_cli_exportar_todos(self):
        """CLI com --exportar-todos deve gerar todos os 5 artefatos na pasta de saída."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                sys.executable,
                "-m",
                "dimensionamento_pontes_concreto_nbr7187.cli",
                "--calcular",
                "--exportar-todos",
                "--saida-dir",
                tmpdir,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/martin/SITES/dimensionamento-pontes-concreto-nbr7187/src")
            self.assertEqual(res.returncode, 0)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "memorial_calculo.txt")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "resultados.csv")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "resultados.json")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "painel_dimensionamento.svg")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "pacote_ponte.zip")))


if __name__ == "__main__":
    unittest.main()
