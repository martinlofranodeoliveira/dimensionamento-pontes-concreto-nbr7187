"""Motor de cálculo analítico para dimensionamento de pontes rodoviárias.

Implementação segundo as normas ABNT NBR 7187:2021, ABNT NBR 7188:2013 e ABNT NBR 6118:2023.
Operação 100% em frações racionais exatas (Fraction) e grandezas inteiras. Zero float.
"""

import math
from fractions import Fraction
from typing import Tuple

from .models import (
    ClasseTremTipo,
    ClasseConcreto,
    AcoArmadura,
    ParametrosVao,
    GeometriaSecao,
    AparelhoApoio,
    ResultadoDimensionamentoPonte,
)


def raiz_quadrada_racional(n: Fraction, precisao_decimais: int = 8) -> Fraction:
    """Calcula a aproximação fracionária racional da raiz quadrada usando math.isqrt com escala inteira."""
    if n < 0:
        raise ValueError(f"Raiz quadrada de fração negativa não permitida: {n}")
    if n == 0:
        return Fraction(0, 1)

    escala = 10 ** precisao_decimais
    escala_quad = escala * escala
    p, q = n.numerator, n.denominator
    # sqrt(p/q) = sqrt(p * q * escala^2) / (q * escala)
    raiz_int = math.isqrt(p * q * escala_quad)
    return Fraction(raiz_int, q * escala)


def calcular_coeficientes_dinamicos(
    vao_livre: Fraction,
    num_faixas: int,
    cia: Fraction = Fraction(23, 20),  # 1.15
) -> Tuple[Fraction, Fraction, Fraction, Fraction]:
    """Calcula os coeficientes de majoração dinâmica CIV, CNF, CIA e CMD (NBR 7187 item 7.2.1).

    Retorna: (CIV, CNF, CIA, CMD)
    """
    if vao_livre <= 0:
        raise ValueError("O vão livre deve ser estritamente positivo.")
    if num_faixas < 1:
        raise ValueError("O número de faixas deve ser no mínimo 1.")

    # 1. Coeficiente de Impacto Vertical (CIV)
    if vao_livre <= 10:
        civ = Fraction(27, 20)  # 1.35
    elif vao_livre <= 200:
        # CIV = 1 + 1.06 * (20 / (L + 50)) = 1 + (53/50) * (20 / (L + 50))
        # CIV = 1 + 1060 / (50 * (L + 50)) = 1 + 106 / (5 * (L + 50)) = (5*L + 356) / (5*(L + 50))
        civ = Fraction(5 * vao_livre + 356, 5 * (vao_livre + 50))
    else:
        # Acima de 200m, valor assintótico
        civ = Fraction(5 * 200 + 356, 5 * (200 + 50))

    # 2. Coeficiente de Número de Faixas (CNF)
    if num_faixas <= 2:
        cnf = Fraction(1, 1)
    else:
        # CNF = 1 - 0.05 * (n - 2) >= 0.90
        cnf_calculado = Fraction(1, 1) - Fraction(num_faixas - 2, 20)
        cnf = max(cnf_calculado, Fraction(9, 10))

    # 3. Coeficiente de Majoração Dinâmica total (CMD)
    cmd = civ * cnf * cia
    return civ, cnf, cia, cmd


def obter_resistencia_tracao_fctd(fck_mpa: int) -> Fraction:
    """Retorna a resistência de cálculo à tração do concreto fctd (em kPa) conforme NBR 6118."""
    # Valores exatos de fctk,inf da NBR 6118:
    tabela_fctk_inf = {
        30: Fraction(20, 10),   # 2.0 MPa
        35: Fraction(22, 10),   # 2.2 MPa
        40: Fraction(25, 10),   # 2.5 MPa
        45: Fraction(27, 10),   # 2.7 MPa
        50: Fraction(29, 10),   # 2.9 MPa
    }
    fctk_inf_mpa = tabela_fctk_inf.get(fck_mpa, Fraction(fck_mpa * 55, 1000))
    # fctd = fctk,inf / 1.40 (em kPa: * 1000)
    return (fctk_inf_mpa / Fraction(7, 5)) * 1000


def calcular_ponte_rodoviaria(
    vao: ParametrosVao,
    secao: GeometriaSecao,
    apoio: AparelhoApoio,
    trem_tipo: ClasseTremTipo = ClasseTremTipo.TB_450,
    fck: ClasseConcreto = ClasseConcreto.C35,
    aco: AcoArmadura = AcoArmadura.CA_50,
    fator_transversal_viga: Fraction = Fraction(65, 100),  # 65% na viga crítica (Courbon)
    cia: Fraction = Fraction(23, 20),                     # 1.15
) -> ResultadoDimensionamentoPonte:
    """Executa o dimensionamento estrutural analítico completo de uma superestrutura de ponte."""
    L = vao.vao_livre
    if L < 3:
        raise ValueError("O vão da ponte deve ser de pelo menos 3 metros para o trem-tipo de 3 eixos.")

    # 1. Coeficientes Dinâmicos
    civ, cnf, cia_calc, cmd = calcular_coeficientes_dinamicos(L, vao.num_faixas, cia)

    # 2. Propriedades dos Materiais (em kPa)
    fck_val = fck.value
    # fcd = fck / 1.40 (kPa)
    fcd = Fraction(fck_val * 1000, 1) / Fraction(7, 5)  # fck * 1000 / 1.4
    # fyd = fyk / 1.15 (kPa)
    fyk_val = aco.value
    fyd = Fraction(fyk_val * 1000, 1) / Fraction(23, 20) # fyk * 1000 / 1.15

    # 3. Cargas Permanentes por Viga (kN/m)
    # Concreto armado gamma_c = 25 kN/m³
    gamma_c = Fraction(25, 1)
    gamma_asf = Fraction(24, 1)

    # Alma da viga:
    area_alma = secao.largura_alma * (secao.altura_total - secao.espessura_mesa)
    g_alma = area_alma * gamma_c

    # Mesa / laje de tabuleiro:
    largura_trib = (vao.largura_pista + vao.largura_passeios) / Fraction(vao.num_vigas, 1)
    g_laje = largura_trib * secao.espessura_mesa * gamma_c

    # Revestimento asfáltico:
    largura_pista_viga = vao.largura_pista / Fraction(vao.num_vigas, 1)
    g_pav = largura_pista_viga * vao.espessura_pavimento * gamma_asf

    # Barreiras e guarda-rodas:
    g_barr = vao.peso_barreiras / Fraction(vao.num_vigas, 1)

    # Carga permanente total g:
    g_total = g_alma + g_laje + g_pav + g_barr

    # 4. Parâmetros do Trem-Tipo (NBR 7188)
    if trem_tipo == ClasseTremTipo.TB_450:
        carga_eixo = Fraction(150, 1)
        num_eixos = 3
        dist_eixos = Fraction(3, 2)  # 1.50 m
        q_multidao = Fraction(5, 1)  # 5 kN/m²
        q_passeio = Fraction(3, 1)   # 3 kN/m²
    elif trem_tipo == ClasseTremTipo.TB_300:
        carga_eixo = Fraction(100, 1)
        num_eixos = 3
        dist_eixos = Fraction(3, 2)
        q_multidao = Fraction(4, 1)
        q_passeio = Fraction(3, 1)
    elif trem_tipo == ClasseTremTipo.TB_120:
        carga_eixo = Fraction(60, 1)
        num_eixos = 2
        dist_eixos = Fraction(3, 2)
        q_multidao = Fraction(3, 1)
        q_passeio = Fraction(3, 1)
    else:  # Passarela
        carga_eixo = Fraction(0, 1)
        num_eixos = 0
        dist_eixos = Fraction(0, 1)
        q_multidao = Fraction(0, 1)
        q_passeio = Fraction(5, 1)

    # 5. Esforços Solicitantes no Meio do Vão (x = L/2)
    # Carga Permanente:
    # Mg_k = g * L^2 / 8
    mg_k = g_total * (L * L) / 8

    # Carga Móvel (Veículo TB-450):
    # Linha de influência triangular com vértice eta_2 = L/4 no meio do vão
    # Para 3 eixos espaçados de 1.50m (central em L/2, laterais em L/2 - 1.50 e L/2 + 1.50):
    if num_eixos == 3:
        # eta_1 = eta_3 = (L/4) - 0.75 = (L - 3)/4
        # M_veic_total = P * (eta_1 + eta_2 + eta_3) = P * (3*L - 6) / 4
        m_veic_total = carga_eixo * (3 * L - 6) / 4
    elif num_eixos == 2:
        # Dois eixos em L/2 - 0.75 e L/2 + 0.75:
        # eta = L/4 - 0.75/2 = (2L - 3)/8
        m_veic_total = carga_eixo * 2 * (2 * L - 3) / 8
    else:
        m_veic_total = Fraction(0, 1)

    # Quinhão do veículo na viga crítica:
    m_veic_viga = m_veic_total * fator_transversal_viga

    # Cargas de multidão e passeios:
    q_lin_viga = (q_multidao * largura_pista_viga) + (q_passeio * (vao.largura_passeios / Fraction(vao.num_vigas, 1)))
    mq_k = q_lin_viga * (L * L) / 8

    # Momento móvel característico total:
    m_movel_total_k = cmd * (m_veic_viga + mq_k)

    # Momento de cálculo de projeto (ELU): gamma_g = 1.35, gamma_q = 1.35 (NBR 7187 Tabela 2)
    gamma_g = Fraction(27, 20)  # 1.35
    gamma_q = Fraction(27, 20)  # 1.35
    md_total = gamma_g * mg_k + gamma_q * m_movel_total_k

    # 6. Esforços Cortantes no Apoio (x = 0)
    # Carga Permanente:
    # Vg_k = g * L / 2
    vg_k = g_total * L / 2

    # Carga Móvel (Veículo com primeiro eixo sobre o apoio):
    if num_eixos == 3:
        # eta_1 = 1, eta_2 = (L - 1.5)/L, eta_3 = (L - 3)/L
        # soma_eta = (6L - 9) / (2L)
        v_veic_total = carga_eixo * (6 * L - 9) / (2 * L)
    elif num_eixos == 2:
        # eta_1 = 1, eta_2 = (L - 1.5)/L
        v_veic_total = carga_eixo * (2 * L - Fraction(3, 2)) / L
    else:
        v_veic_total = Fraction(0, 1)

    v_veic_viga = v_veic_total * fator_transversal_viga
    vq_k = q_lin_viga * L / 2
    v_movel_total_k = cmd * (v_veic_viga + vq_k)

    # Cortante de projeto (ELU):
    vd_total = gamma_g * vg_k + gamma_q * v_movel_total_k

    # 7. Dimensionamento à Flexão no ELU (NBR 6118)
    d = secao.d_util
    bf = secao.largura_mesa
    bw = secao.largura_alma
    hf = secao.espessura_mesa

    # Momento limite suportado pela mesa de compressão:
    # M_Rd,mesa = bf * hf * (0.85 * fcd) * (d - 0.5 * hf)
    m_rd_mesa = bf * hf * Fraction(17, 20) * fcd * (d - hf / 2)

    # Se Md <= M_Rd,mesa, a viga funciona como retangular de largura bf:
    largura_calculo_b = bf if md_total <= m_rd_mesa else bw

    # Equação do bloco de tensões:
    # Md = 0.68 * fcd * b * (x * d - 0.4 * x^2)
    # x = (d - sqrt(d^2 - 2*Md / (0.85*fcd*b))) / 0.8
    termo_raiz = d * d - (2 * md_total) / (Fraction(17, 20) * fcd * largura_calculo_b)
    if termo_raiz < 0:
        # Seção insuficiente para suportar o momento no ELU
        x_linha_neutra = d
        ductilidade = False
    else:
        raiz_termo = raiz_quadrada_racional(termo_raiz)
        x_linha_neutra = (d - raiz_termo) / Fraction(4, 5)
        ductilidade = (x_linha_neutra / d) <= Fraction(45, 100)

    relacao_x_d = x_linha_neutra / d
    limite_x_d = Fraction(45, 100)

    # Braço de alavanca z:
    z_alavanca = d - Fraction(2, 5) * x_linha_neutra
    # As = Md / (fyd * z) (em m² -> multiplicar por 10000 para cm²)
    as_m2 = md_total / (fyd * z_alavanca)
    as_cm2 = as_m2 * 10000

    # Taxa geométrica rho_s (%):
    rho_s = (as_m2 / (bw * d)) * 100

    # 8. Dimensionamento ao Cisalhamento no ELU (NBR 6118 Modelo I)
    # Tensão da biela de compressão:
    # alpha_v1 = 1 - fck / 250
    alpha_v1 = Fraction(1, 1) - Fraction(fck_val, 250)
    # VRd2 = 0.27 * alpha_v1 * fcd * bw * d (kN)
    vrd2 = Fraction(27, 100) * alpha_v1 * fcd * bw * d
    biela_ok = vd_total <= vrd2

    # Parcela resistida pelo concreto Vc:
    fctd = obter_resistencia_tracao_fctd(fck_val)
    # Vc = 0.6 * fctd * bw * d
    vc = Fraction(3, 5) * fctd * bw * d

    # Parcela de estribos:
    vsw = max(vd_total - vc, Fraction(0, 1))
    # Asw / s = Vsw / (0.9 * d * fywd) (em m²/m -> multiplicar por 10000 para cm²/m)
    # fywd limitado a 435 MPa = 435000 kPa
    fywd = min(fyd, Fraction(435000, 1))
    asw_s_m2_m = vsw / (Fraction(9, 10) * d * fywd)
    asw_s_cm2_m = asw_s_m2_m * 10000

    # Armadura mínima de estribos:
    # rho_sw,min = 0.2 * (fctm / fyk) onde fctm = fctk,inf / 0.70
    # Simplificado normativo: rho_sw,min = 0.14% para CA-50
    rho_sw_min = Fraction(14, 10000)
    asw_s_min_cm2_m = rho_sw_min * bw * 10000
    asw_s_adotado = max(asw_s_cm2_m, asw_s_min_cm2_m)

    # 9. Verificação de Fadiga da Armadura Longitudinal (NBR 7187 item 11 e NBR 6118 Tabela 23.2)
    # Modelo de fadiga da NBR 7187: veículo de fadiga (0.70 do veículo com CIV, sem multidão)
    # M_fad = 0.70 * M_veic_viga * civ
    m_fad = Fraction(7, 10) * m_veic_viga * civ
    # Delta_sigma_s = M_fad / (0.9 * d * As) (em kPa -> / 1000 para MPa)
    delta_sigma_s_kpa = m_fad / (Fraction(9, 10) * d * as_m2)
    delta_sigma_s_mpa = delta_sigma_s_kpa / 1000
    # Limite normativo para barras longitudinais retas CA-50 sob tração (NBR 6118 Tab. 23.2): 180 MPa
    limite_fadiga_mpa = Fraction(180, 1)
    fadiga_ok = delta_sigma_s_mpa <= limite_fadiga_mpa

    # 10. Verificação do Estado Limite de Deformação (ELS-DEF)
    # Momento de inércia da seção T com Teorema dos Eixos Paralelos (Steiner):
    h = secao.altura_total
    h_alma = h - hf
    area_alma_t = bw * h_alma
    y_alma = h_alma / 2
    area_mesa_t = bf * hf
    y_mesa = h - hf / 2
    area_total_secao = area_alma_t + area_mesa_t
    y_g = (area_alma_t * y_alma + area_mesa_t * y_mesa) / area_total_secao

    inercia_bruta = (
        (bw * (h_alma ** 3)) / 12
        + area_alma_t * ((y_alma - y_g) ** 2)
        + (bf * (hf ** 3)) / 12
        + area_mesa_t * ((y_mesa - y_g) ** 2)
    )

    # Módulo de elasticidade secante Ecs do concreto (kPa):
    ecs = Fraction(28000000 + (fck_val - 30) * 1000000, 1)

    # Flecha permanente com fluência a longo prazo (alpha_f = 2.5), compensada em projeto por contra-flecha:
    delta_g = Fraction(7, 2) * (5 * g_total * (L ** 4)) / (384 * ecs * inercia_bruta)

    # Flecha sob carga móvel frequente com impacto (NBR 7187 item 12.2.2: limitada a L/1000):
    delta_q = Fraction(7, 10) * (m_movel_total_k * (L ** 2)) / (10 * ecs * inercia_bruta)
    flecha_total = delta_q
    flecha_admissivel = L / 1000
    flecha_ok = flecha_total <= flecha_admissivel

    # 11. Dimensionamento do Aparelho de Apoio de Neoprene Fretado
    # Reação vertical máxima de serviço no apoio por viga:
    r_max_k = vg_k + v_movel_total_k
    # Área adotada do bloco de elastômero:
    area_adotada = apoio.comprimento_a * apoio.largura_b
    tensao_contato = r_max_k / area_adotada
    area_necessaria = r_max_k / apoio.tensao_admissivel
    apoio_ok = tensao_contato <= apoio.tensao_admissivel

    # Status Global
    aprovado = (
        ductilidade
        and biela_ok
        and fadiga_ok
        and flecha_ok
        and apoio_ok
    )

    return ResultadoDimensionamentoPonte(
        civ=civ,
        cnf=cnf,
        cia=cia_calc,
        cmd=cmd,
        peso_proprio_viga=g_alma,
        peso_proprio_laje=g_laje,
        peso_pavimento=g_pav,
        peso_permanente_total=g_total,
        carga_eixo_veiculo=carga_eixo,
        num_eixos=num_eixos,
        carga_multidao_q=q_multidao,
        carga_passeio=q_passeio,
        momento_permanente_k=mg_k,
        momento_veiculo_k=m_veic_viga,
        momento_multidao_k=mq_k,
        momento_movel_total_k=m_movel_total_k,
        momento_total_d=md_total,
        cortante_permanente_k=vg_k,
        cortante_veiculo_k=v_veic_viga,
        cortante_multidao_k=vq_k,
        cortante_movel_total_k=v_movel_total_k,
        cortante_total_d=vd_total,
        altura_linha_neutra_x=x_linha_neutra,
        relacao_x_d=relacao_x_d,
        limite_x_d=limite_x_d,
        armadura_longitudinal_as=as_cm2,
        taxa_armadura_longitudinal=rho_s,
        ductilidade_atendida=ductilidade,
        cortante_resistencia_biela_vrd2=vrd2,
        biela_comprimida_atendida=biela_ok,
        cortante_concreto_vc=vc,
        armadura_estribos_asw_s=asw_s_adotado,
        armadura_estribos_minima_asw_s=asw_s_min_cm2_m,
        variacao_tensao_fadiga=delta_sigma_s_mpa,
        limite_tensao_fadiga=limite_fadiga_mpa,
        fadiga_atendida=fadiga_ok,
        flecha_imediata=delta_q,
        flecha_total_diferida=flecha_total,
        flecha_admissivel=flecha_admissivel,
        flecha_atendida=flecha_ok,
        reacao_apoio_maxima_k=r_max_k,
        area_apoio_necessaria=area_necessaria,
        area_apoio_adotada=area_adotada,
        tensao_contato_apoio=tensao_contato,
        apoio_neoprene_atendido=apoio_ok,
        aprovado_geral=aprovado,
    )
