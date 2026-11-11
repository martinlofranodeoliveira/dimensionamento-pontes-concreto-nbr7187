"""Testes unitários dos codecs estritos RFC 8259 para dimensionamento de pontes.

Verifica rejeição de float, ausência de BOM, verificação de profundidade máxima e unicidade de chaves.
"""

import unittest
from fractions import Fraction

from dimensionamento_pontes_concreto_nbr7187.codecs import (
    JSONDecodeStrictError,
    codificar_json_estrito,
    decodificar_json_estrito,
)


class TesteCodecsPontes(unittest.TestCase):
    """Bateria de testes dos codecs estritos RFC 8259."""

    def test_codificacao_fracao_racional_sem_float(self):
        """Frações devem ser codificadas em representação estruturada exata."""
        dado = {"momento": Fraction(355, 113)}
        json_str = codificar_json_estrito(dado)
        self.assertIn('"numerador": 355', json_str)
        self.assertIn('"denominador": 113', json_str)
        self.assertNotIn("3.141592653589793", json_str)

    def test_rejeicao_float_na_codificacao(self):
        """Valores do tipo float são estritamente proibidos e devem lançar TypeError."""
        dado = {"vao": 25.5}
        with self.assertRaises(TypeError):
            codificar_json_estrito(dado)

    def test_rejeicao_bom_no_parse(self):
        """Presença de BOM UTF-8 deve lançar JSONDecodeStrictError."""
        payload_bom = "\ufeff" + '{"vao": 25}'
        with self.assertRaises(JSONDecodeStrictError):
            decodificar_json_estrito(payload_bom)

        payload_bom_bytes = "\xef\xbb\xbf" + '{"vao": 25}'
        with self.assertRaises(JSONDecodeStrictError):
            decodificar_json_estrito(payload_bom_bytes)

    def test_rejeicao_chaves_duplicadas(self):
        """Chaves repetidas no JSON devem ser rejeitadas."""
        json_duplicado = '{"item": 1, "item": 2}'
        with self.assertRaises(JSONDecodeStrictError):
            decodificar_json_estrito(json_duplicado)

    def test_rejeicao_float_na_decodificacao(self):
        """Presença de literal float no JSON deve ser rejeitada."""
        json_com_float = '{"largura": 7.20}'
        with self.assertRaises(JSONDecodeStrictError):
            decodificar_json_estrito(json_com_float)

    def test_decodificacao_inteiros_e_strings_valida(self):
        """JSON estrito contendo apenas inteiros, strings, booleanos e nulos deve ser aceito."""
        json_valido = '{"vao": 25, "faixas": 2, "aprovado": true, "nome": "TB-450", "nulo": null}'
        resultado = decodificar_json_estrito(json_valido)
        self.assertEqual(resultado["vao"], 25)
        self.assertEqual(resultado["faixas"], 2)
        self.assertTrue(resultado["aprovado"])
        self.assertEqual(resultado["nome"], "TB-450")
        self.assertIsNone(resultado["nulo"])

    def test_limite_profundidade_aninhamento_32(self):
        """Estrutura com profundidade excessiva (> 32) deve lançar JSONDecodeStrictError."""
        dado = {"nivel": 0}
        atual = dado
        for i in range(35):
            novo = {"nivel": i + 1}
            atual["sub"] = novo
            atual = novo

        with self.assertRaises(JSONDecodeStrictError):
            codificar_json_estrito(dado)


if __name__ == "__main__":
    unittest.main()
