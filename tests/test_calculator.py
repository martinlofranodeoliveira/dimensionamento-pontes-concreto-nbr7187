"""Testes unitários abrangentes do motor de cálculo de pontes rodoviárias.

ABNT NBR 7187:2021, ABNT NBR 7188:2013 e ABNT NBR 6118:2023.
"""

import unittest
from fractions import Fraction

from dimensionamento_pontes_concreto_nbr7187.models import (
    ClasseTremTipo,
    ClasseConcreto,
    AcoArmadura,
    ParametrosVao,
    GeometriaSecao,
    AparelhoApoio,
    ResultadoDimensionamentoPonte,
)
from dimensionamento_pontes_concreto_nbr7187.calculator import (
    raiz_quadrada_racional,
    calcular_coeficientes_dinamicos,
    obter_resistencia_tracao_fctd,
    calcular_ponte_rodoviaria,
)


class TesteCalculadoraPontes(unittest.TestCase):
    """Bateria de testes das rotinas analíticas e normativas de pontes de concreto."""

    def setUp(self):
        self.vao_padrao = ParametrosVao(
            vao_livre=Fraction(25, 1),
            largura_pista=Fraction(72, 10),
            largura_passeios=Fraction(2, 1),
            num_faixas=2,
            espessura_pavimento=Fraction(7, 100),
            peso_barreiras=Fraction(12, 1),
            num_vigas=2,
        )
        self.secao_padrao = GeometriaSecao(
            altura_total=Fraction(18, 10),
            largura_alma=Fraction(45, 100),
            largura_mesa=Fraction(22, 10),
            espessura_mesa=Fraction(2, 10),
            cobrimento=Fraction(4, 100),
            d_util=Fraction(165, 100),
        )
        self.apoio_padrao = AparelhoApoio(
            comprimento_a=Fraction(35, 100),
            largura_b=Fraction(45, 100),
            espessura_elastometro=Fraction(6, 100),
            tensao_admissivel=Fraction(10000, 1),
        )

    def test_raiz_quadrada_racional_casos_notaveis(self):
        """Verifica a raiz quadrada racional em quadrados perfeitos e aproximações."""
        self.assertEqual(raiz_quadrada_racional(Fraction(0, 1)), Fraction(0, 1))
        self.assertEqual(raiz_quadrada_racional(Fraction(4, 1)), Fraction(2, 1))
        self.assertEqual(raiz_quadrada_racional(Fraction(9, 16)), Fraction(3, 4))
        self.assertEqual(raiz_quadrada_racional(Fraction(25, 144)), Fraction(5, 12))

    def test_raiz_quadrada_racional_negativo_lanca_excecao(self):
        """Verifica que raiz de fração negativa lança ValueError."""
        with self.assertRaises(ValueError):
            raiz_quadrada_racional(Fraction(-4, 1))

    def test_civ_vao_curto_menor_ou_igual_10m(self):
        """Para vãos até 10m, CIV deve ser exatamente 1.35 (27/20)."""
        civ, cnf, cia, cmd = calcular_coeficientes_dinamicos(Fraction(10, 1), 2)
        self.assertEqual(civ, Fraction(27, 20))
        civ_5m, _, _, _ = calcular_coeficientes_dinamicos(Fraction(5, 1), 2)
        self.assertEqual(civ_5m, Fraction(27, 20))

    def test_civ_vao_intermediario_25m(self):
        """Para L=25m, CIV = (5*25 + 356) / (5*75) = 481 / 375."""
        civ, _, _, _ = calcular_coeficientes_dinamicos(Fraction(25, 1), 2)
        self.assertEqual(civ, Fraction(481, 375))

    def test_civ_vao_longo_maior_ou_igual_200m(self):
        """Para L>=200m, CIV atinge o valor assintótico."""
        civ_200, _, _, _ = calcular_coeficientes_dinamicos(Fraction(200, 1), 2)
        civ_300, _, _, _ = calcular_coeficientes_dinamicos(Fraction(300, 1), 2)
        self.assertEqual(civ_200, civ_300)

    def test_cnf_uma_e_duas_faixas(self):
        """Para n <= 2 faixas, CNF deve ser exatamente 1.0."""
        _, cnf_1, _, _ = calcular_coeficientes_dinamicos(Fraction(20, 1), 1)
        _, cnf_2, _, _ = calcular_coeficientes_dinamicos(Fraction(20, 1), 2)
        self.assertEqual(cnf_1, Fraction(1, 1))
        self.assertEqual(cnf_2, Fraction(1, 1))

    def test_cnf_tres_e_quatro_faixas(self):
        """Para n=3: CNF = 1 - 0.05*(1) = 0.95. Para n=4: CNF = 1 - 0.05*(2) = 0.90."""
        _, cnf_3, _, _ = calcular_coeficientes_dinamicos(Fraction(20, 1), 3)
        _, cnf_4, _, _ = calcular_coeficientes_dinamicos(Fraction(20, 1), 4)
        self.assertEqual(cnf_3, Fraction(19, 20))
        self.assertEqual(cnf_4, Fraction(9, 10))

    def test_cnf_muitas_faixas_limite_minimo_0_90(self):
        """Para n >= 4 faixas, CNF não pode ser inferior a 0.90."""
        _, cnf_6, _, _ = calcular_coeficientes_dinamicos(Fraction(20, 1), 6)
        self.assertEqual(cnf_6, Fraction(9, 10))

    def test_validacao_vao_e_faixas_invalidos(self):
        """Testa rejeição de vão não positivo e zero faixas."""
        with self.assertRaises(ValueError):
            calcular_coeficientes_dinamicos(Fraction(0, 1), 2)
        with self.assertRaises(ValueError):
            calcular_coeficientes_dinamicos(Fraction(20, 1), 0)

    def test_resistencia_fctd_tabela(self):
        """Confere fctd para diferentes fck de concreto."""
        fctd_30 = obter_resistencia_tracao_fctd(30)
        self.assertEqual(fctd_30, Fraction(20, 14) * 1000)
        fctd_50 = obter_resistencia_tracao_fctd(50)
        self.assertEqual(fctd_50, Fraction(29, 14) * 1000)

    def test_dimensionamento_padrao_tb450_aprovado(self):
        """Dimensionamento completo com vão de 25m e TB-450 deve ser aprovado."""
        res = calcular_ponte_rodoviaria(
            vao=self.vao_padrao,
            secao=self.secao_padrao,
            apoio=self.apoio_padrao,
            trem_tipo=ClasseTremTipo.TB_450,
            fck=ClasseConcreto.C35,
        )
        self.assertIsInstance(res, ResultadoDimensionamentoPonte)
        self.assertTrue(res.aprovado_geral)
        self.assertTrue(res.ductilidade_atendida)
        self.assertTrue(res.biela_comprimida_atendida)
        self.assertTrue(res.fadiga_atendida)
        self.assertTrue(res.flecha_atendida)
        self.assertTrue(res.apoio_neoprene_atendido)

    def test_carga_permanente_decomposicao(self):
        """Testa se as parcelas de peso próprio somam a carga permanente total."""
        res = calcular_ponte_rodoviaria(
            vao=self.vao_padrao,
            secao=self.secao_padrao,
            apoio=self.apoio_padrao,
        )
        soma = res.peso_proprio_viga + res.peso_proprio_laje + res.peso_pavimento + (self.vao_padrao.peso_barreiras / 2)
        self.assertEqual(res.peso_permanente_total, soma)

    def test_esforcos_solicitantes_positivos(self):
        """Verifica se momentos e cortantes característicos e de cálculo são estritamente positivos."""
        res = calcular_ponte_rodoviaria(
            vao=self.vao_padrao,
            secao=self.secao_padrao,
            apoio=self.apoio_padrao,
        )
        self.assertGreater(res.momento_permanente_k, 0)
        self.assertGreater(res.momento_veiculo_k, 0)
        self.assertGreater(res.momento_multidao_k, 0)
        self.assertGreater(res.momento_total_d, res.momento_permanente_k)
        self.assertGreater(res.cortante_permanente_k, 0)
        self.assertGreater(res.cortante_total_d, res.cortante_permanente_k)

    def test_trem_tipo_tb300_momento_menor_que_tb450(self):
        """Trem-tipo TB-300 deve gerar momento menor que o TB-450 sob mesma geometria."""
        res_450 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, trem_tipo=ClasseTremTipo.TB_450)
        res_300 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, trem_tipo=ClasseTremTipo.TB_300)
        self.assertLess(res_300.momento_veiculo_k, res_450.momento_veiculo_k)
        self.assertLess(res_300.momento_total_d, res_450.momento_total_d)

    def test_trem_tipo_tb120(self):
        """Trem-tipo TB-120 com 2 eixos de 60 kN deve gerar momento menor que TB-300."""
        res_300 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, trem_tipo=ClasseTremTipo.TB_300)
        res_120 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, trem_tipo=ClasseTremTipo.TB_120)
        self.assertLess(res_120.momento_veiculo_k, res_300.momento_veiculo_k)
        self.assertEqual(res_120.num_eixos, 2)

    def test_passarela_exclusiva_pedestres(self):
        """Passarela não possui veículo de eixos concentrados (apenas pedestres)."""
        res_pass = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, trem_tipo=ClasseTremTipo.PASSARELA)
        self.assertEqual(res_pass.momento_veiculo_k, 0)
        self.assertEqual(res_pass.num_eixos, 0)

    def test_armadura_longitudinal_calculada_positiva(self):
        """Área de armadura longitudinal As deve ser positiva e condizente."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao)
        self.assertGreater(res.armadura_longitudinal_as, 50)  # > 50 cm² para vão de 25m
        self.assertLess(res.armadura_longitudinal_as, 300)

    def test_estribos_transversais_maior_ou_igual_ao_minimo(self):
        """Armadura transversal Asw/s deve ser >= Asw/s mínima."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao)
        self.assertGreaterEqual(res.armadura_estribos_asw_s, res.armadura_estribos_minima_asw_s)

    def test_secao_muito_baixa_rejeita_biela_ou_ductilidade(self):
        """Uma viga absurdamente baixa (ex: h = 0.50m para vão de 25m) deve falhar."""
        secao_inadequada = GeometriaSecao(
            altura_total=Fraction(5, 10),
            largura_alma=Fraction(3, 10),
            largura_mesa=Fraction(1, 1),
            espessura_mesa=Fraction(15, 100),
            cobrimento=Fraction(4, 100),
            d_util=Fraction(40, 100),
        )
        res = calcular_ponte_rodoviaria(self.vao_padrao, secao_inadequada, self.apoio_padrao)
        self.assertFalse(res.aprovado_geral)

    def test_aparelho_apoio_pequeno_rejeita_tensao(self):
        """Um apoio de neoprene muito reduzido (10x10 cm) deve falhar na tensão de contato."""
        apoio_insuficiente = AparelhoApoio(
            comprimento_a=Fraction(1, 10),
            largura_b=Fraction(1, 10),
            espessura_elastometro=Fraction(2, 100),
            tensao_admissivel=Fraction(10000, 1),
        )
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, apoio_insuficiente)
        self.assertFalse(res.apoio_neoprene_atendido)
        self.assertFalse(res.aprovado_geral)

    def test_concreto_alta_resistencia_c50(self):
        """Verifica dimensionamento em concreto C50."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, fck=ClasseConcreto.C50)
        self.assertTrue(res.aprovado_geral)
        self.assertGreater(res.cortante_resistencia_biela_vrd2, 0)

    def test_concreto_c40_e_c45(self):
        """Verifica dimensionamento com fck 40 e 45 MPa."""
        res_40 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, fck=ClasseConcreto.C40)
        res_45 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, fck=ClasseConcreto.C45)
        self.assertTrue(res_40.aprovado_geral)
        self.assertTrue(res_45.aprovado_geral)
        self.assertGreater(res_45.cortante_resistencia_biela_vrd2, res_40.cortante_resistencia_biela_vrd2)

    def test_pista_tres_faixas_10m50(self):
        """Ponte com 3 faixas (largura 10.50m) deve ter CNF = 0.95."""
        vao_3f = ParametrosVao(
            vao_livre=Fraction(30, 1),
            largura_pista=Fraction(105, 10),
            largura_passeios=Fraction(3, 1),
            num_faixas=3,
            espessura_pavimento=Fraction(7, 100),
            peso_barreiras=Fraction(14, 1),
            num_vigas=2,
        )
        secao_maior = GeometriaSecao(
            altura_total=Fraction(22, 10),
            largura_alma=Fraction(50, 100),
            largura_mesa=Fraction(3, 1),
            espessura_mesa=Fraction(25, 100),
            cobrimento=Fraction(4, 100),
            d_util=Fraction(205, 100),
        )
        apoio_maior = AparelhoApoio(
            comprimento_a=Fraction(45, 100),
            largura_b=Fraction(55, 100),
            espessura_elastometro=Fraction(8, 100),
            tensao_admissivel=Fraction(10000, 1),
        )
        res = calcular_ponte_rodoviaria(vao_3f, secao_maior, apoio_maior)
        self.assertEqual(res.cnf, Fraction(19, 20))
        self.assertTrue(res.aprovado_geral)

    def test_cia_extremidade_junta_1_25(self):
        """Verifica cálculo com CIA de extremidade (1.25 = 5/4)."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, cia=Fraction(5, 4))
        self.assertEqual(res.cia, Fraction(5, 4))
        self.assertGreater(res.cmd, res.civ)

    def test_espessura_pavimento_variada(self):
        """Espessura maior de pavimento asfáltico aumenta o peso próprio permanente."""
        vao_pav_fino = ParametrosVao(
            vao_livre=Fraction(25, 1),
            largura_pista=Fraction(72, 10),
            largura_passeios=Fraction(2, 1),
            num_faixas=2,
            espessura_pavimento=Fraction(5, 100),  # 5 cm
            peso_barreiras=Fraction(12, 1),
            num_vigas=2,
        )
        vao_pav_grosso = ParametrosVao(
            vao_livre=Fraction(25, 1),
            largura_pista=Fraction(72, 10),
            largura_passeios=Fraction(2, 1),
            num_faixas=2,
            espessura_pavimento=Fraction(12, 100), # 12 cm
            peso_barreiras=Fraction(12, 1),
            num_vigas=2,
        )
        res_fino = calcular_ponte_rodoviaria(vao_pav_fino, self.secao_padrao, self.apoio_padrao)
        res_grosso = calcular_ponte_rodoviaria(vao_pav_grosso, self.secao_padrao, self.apoio_padrao)
        self.assertLess(res_fino.peso_permanente_total, res_grosso.peso_permanente_total)
        self.assertLess(res_fino.momento_permanente_k, res_grosso.momento_permanente_k)

    def test_rejeicao_vao_menor_que_tres_metros(self):
        """Vão menor que 3m não comporta o trem-tipo de 3 eixos e deve lançar ValueError."""
        vao_curto = ParametrosVao(
            vao_livre=Fraction(2, 1),
            largura_pista=Fraction(72, 10),
            largura_passeios=Fraction(2, 1),
            num_faixas=2,
            espessura_pavimento=Fraction(7, 100),
            peso_barreiras=Fraction(12, 1),
        )
        with self.assertRaises(ValueError):
            calcular_ponte_rodoviaria(vao_curto, self.secao_padrao, self.apoio_padrao)

    def test_fator_distribuicao_transversal_customizado(self):
        """Fator de distribuição transversal maior (ex: 80% na viga) aumenta esforço."""
        res_65 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, fator_transversal_viga=Fraction(65, 100))
        res_80 = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, fator_transversal_viga=Fraction(80, 100))
        self.assertLess(res_65.momento_veiculo_k, res_80.momento_veiculo_k)
        self.assertLess(res_65.cortante_veiculo_k, res_80.cortante_veiculo_k)

    def test_tamanho_neoprene_superdimensionado(self):
        """Neoprene grande (60x60 cm) reduz tensão de contato e passa com folga."""
        apoio_amplo = AparelhoApoio(
            comprimento_a=Fraction(6, 10),
            largura_b=Fraction(6, 10),
            espessura_elastometro=Fraction(8, 100),
            tensao_admissivel=Fraction(10000, 1),
        )
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, apoio_amplo)
        self.assertTrue(res.apoio_neoprene_atendido)
        self.assertLess(res.tensao_contato_apoio, 5000)  # < 5 MPa

    def test_pista_simples_uma_faixa_3m60(self):
        """Ponte de pista simples (3.60m) com 1 faixa: CNF = 1.0."""
        vao_1f = ParametrosVao(
            vao_livre=Fraction(18, 1),
            largura_pista=Fraction(36, 10),
            largura_passeios=Fraction(16, 10),
            num_faixas=1,
            espessura_pavimento=Fraction(5, 100),
            peso_barreiras=Fraction(10, 1),
            num_vigas=2,
        )
        secao_1f = GeometriaSecao(
            altura_total=Fraction(15, 10),
            largura_alma=Fraction(40, 100),
            largura_mesa=Fraction(18, 10),
            espessura_mesa=Fraction(18, 100),
            cobrimento=Fraction(4, 100),
            d_util=Fraction(135, 100),
        )
        apoio_1f = AparelhoApoio(
            comprimento_a=Fraction(30, 100),
            largura_b=Fraction(40, 100),
            espessura_elastometro=Fraction(5, 100),
            tensao_admissivel=Fraction(10000, 1),
        )
        res = calcular_ponte_rodoviaria(vao_1f, secao_1f, apoio_1f)
        self.assertEqual(res.cnf, Fraction(1, 1))
        self.assertTrue(res.aprovado_geral)

    def test_relacao_x_d_dentro_do_dominio_de_ductilidade(self):
        """A relação x/d deve ser inferior ao limite normativo de 0.45."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao)
        self.assertLessEqual(res.relacao_x_d, res.limite_x_d)
        self.assertGreater(res.altura_linha_neutra_x, 0)

    def test_aco_ca60_resistencia(self):
        """Verifica o dimensionamento com aço CA-60."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao, aco=AcoArmadura.CA_60)
        self.assertTrue(res.aprovado_geral)

    def test_area_apoio_necessaria_menor_que_adotada(self):
        """Para apoio aprovado, a área necessária deve ser menor ou igual à área adotada."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao)
        self.assertLessEqual(res.area_apoio_necessaria, res.area_apoio_adotada)

    def test_flecha_imediata_menor_que_flecha_admissivel(self):
        """A flecha imediata sob carga móvel deve ser inferior a L/1000."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao)
        self.assertLess(res.flecha_imediata, res.flecha_admissivel)

    def test_decomposicao_cortante_resistencia_concreto_e_estribos(self):
        """A soma Vc + Vsw deve cobrir Vd no ELU."""
        res = calcular_ponte_rodoviaria(self.vao_padrao, self.secao_padrao, self.apoio_padrao)
        self.assertGreater(res.cortante_resistencia_biela_vrd2, res.cortante_total_d)
        self.assertGreater(res.cortante_concreto_vc, 0)


if __name__ == "__main__":
    unittest.main()
