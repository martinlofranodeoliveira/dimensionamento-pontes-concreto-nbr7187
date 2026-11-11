"""Modelos de dados para dimensionamento de pontes rodoviárias.

Todos os atributos numéricos utilizam frações racionais exatas (Fraction) e inteiros.
Proibição absoluta de ponto flutuante (float).
"""

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction


class ClasseTremTipo(Enum):
    """Classes normativas de veículos de projeto segundo ABNT NBR 7188:2013."""
    TB_450 = "TB-450"  # Rodoviário pesado padrão: 450 kN (3 eixos de 150 kN), multidão 5 kN/m²
    TB_300 = "TB-300"  # Rodoviário intermediário: 300 kN (3 eixos de 100 kN), multidão 4 kN/m²
    TB_120 = "TB-120"  # Vias vicinais e rurais: 120 kN (2 eixos de 60 kN), multidão 3 kN/m²
    PASSARELA = "PASSARELA"  # Exclusivo pedestres: multidão 5 kN/m², sem veículo pesado


class TipoSecao(Enum):
    """Tipologia estrutural da superestrutura da ponte."""
    VIGA_T_MULTIPLA = "VIGA_T_MULTIPLA"  # Grelha de vigas T com laje de tabuleiro
    VIGA_CAIXAO = "VIGA_CAIXAO"          # Seção caixão unicelular ou multicelular
    LAJE_MACICA = "LAJE_MACICA"          # Tabuleiro em laje maciça de concreto
    VIGA_DUPLA = "VIGA_DUPLA"            # Duas vigas principais com transversinas


class ClasseConcreto(Enum):
    """Classes de resistência à compressão do concreto (ABNT NBR 8953 / NBR 6118)."""
    C30 = 30  # fck = 30 MPa
    C35 = 35  # fck = 35 MPa
    C40 = 40  # fck = 40 MPa
    C45 = 45  # fck = 45 MPa
    C50 = 50  # fck = 50 MPa


class AcoArmadura(Enum):
    """Classes de aços para armaduras de concreto armado (ABNT NBR 7480)."""
    CA_50 = 500  # fyk = 500 MPa
    CA_60 = 600  # fyk = 600 MPa


@dataclass(frozen=True)
class ParametrosVao:
    """Parâmetros geométricos e funcionais do vão da ponte."""
    vao_livre: Fraction          # Comprimento de cálculo do vão L (m)
    largura_pista: Fraction      # Largura útil de rolamento rodoviário (m)
    largura_passeios: Fraction   # Largura total de passeios laterais somados (m)
    num_faixas: int              # Número inteiro de faixas de tráfego rodoviário (mínimo 1)
    espessura_pavimento: Fraction  # Espessura do revestimento asfáltico (m) (ex: 7/100 = 0.07 m)
    peso_barreiras: Fraction     # Carga distribuída de barreiras New Jersey + guarda-rodas (kN/m)
    num_vigas: int = 2           # Número de vigas principais longitudinais


@dataclass(frozen=True)
class GeometriaSecao:
    """Geometria transversal da superestrutura e da viga principal de concreto."""
    altura_total: Fraction       # Altura h da viga/seção (m)
    largura_alma: Fraction       # Largura bw da viga (m)
    largura_mesa: Fraction       # Largura colaborante bf da mesa superior (m)
    espessura_mesa: Fraction     # Espessura hf da laje/mesa de compressão (m)
    cobrimento: Fraction         # Cobrimento nominal c_nom (m) (ex: 4/100 = 0.04 m para classe III/IV)
    d_util: Fraction             # Altura útil d da armadura de tração (m)


@dataclass(frozen=True)
class AparelhoApoio:
    """Parâmetros do aparelho de apoio de elastômero fretado (neoprene)."""
    comprimento_a: Fraction      # Dimensão a longitudinal do elastômero (m)
    largura_b: Fraction          # Dimensão b transversal do elastômero (m)
    espessura_elastometro: Fraction  # Altura total do bloco de neoprene (m)
    tensao_admissivel: Fraction  # Tensão média admissível (kPa) (ex: 10000 kPa = 10 MPa)


@dataclass(frozen=True)
class ResultadoDimensionamentoPonte:
    """Resultados analíticos completos do dimensionamento da superestrutura da ponte."""
    # Coeficientes Dinâmicos
    civ: Fraction                # Coeficiente de Impacto Vertical
    cnf: Fraction                # Coeficiente de Número de Faixas
    cia: Fraction                # Coeficiente de Impacto Adicional
    cmd: Fraction                # Coeficiente de Majoração Dinâmica total (CIV * CNF * CIA)

    # Cargas Permanentes
    peso_proprio_viga: Fraction  # Carga distribuída peso próprio da viga (kN/m)
    peso_proprio_laje: Fraction  # Carga distribuída da laje de tabuleiro (kN/m)
    peso_pavimento: Fraction     # Carga de pavimentação asfáltica (kN/m)
    peso_permanente_total: Fraction  # Carga permanente total g (kN/m)

    # Cargas Móveis (TB-450)
    carga_eixo_veiculo: Fraction # Carga por eixo do veículo (kN)
    num_eixos: int               # Número de eixos do trem-tipo (3 para TB-450)
    carga_multidao_q: Fraction   # Carga distribuída de multidão na pista (kN/m²)
    carga_passeio: Fraction      # Carga distribuída de pedestres nos passeios (kN/m²)

    # Esforços Solicitantes Característicos e de Cálculo
    momento_permanente_k: Fraction   # Mg_k no meio do vão (kNm)
    momento_veiculo_k: Fraction       # M_veic_k no meio do vão (kNm)
    momento_multidao_k: Fraction      # M_q_k no meio do vão (kNm)
    momento_movel_total_k: Fraction   # M_movel_k = CMD * (M_veic + M_q) (kNm)
    momento_total_d: Fraction         # Md_total = 1.35*Mg + 1.35*M_movel (kNm)

    cortante_permanente_k: Fraction  # Vg_k no apoio (kN)
    cortante_veiculo_k: Fraction      # V_veic_k no apoio (kN)
    cortante_multidao_k: Fraction     # V_q_k no apoio (kN)
    cortante_movel_total_k: Fraction  # V_movel_k = CMD * (V_veic + V_q) (kN)
    cortante_total_d: Fraction        # Vd_total = 1.35*Vg + 1.35*V_movel (kN)

    # Dimensionamento à Flexão (ELU)
    altura_linha_neutra_x: Fraction  # Profundidade da linha neutra x (m)
    relacao_x_d: Fraction            # Razão x/d (adimensional)
    limite_x_d: Fraction             # Limite normativo (0.45 para CA-50)
    armadura_longitudinal_as: Fraction # Área de aço necessária As (cm²)
    taxa_armadura_longitudinal: Fraction # Taxa rho_s (%)
    ductilidade_atendida: bool       # True se x/d <= limite_x_d

    # Dimensionamento ao Cisalhamento (ELU)
    cortante_resistencia_biela_vrd2: Fraction # VRd2 esmagamento da biela (kN)
    biela_comprimida_atendida: bool          # True se Vd <= VRd2
    cortante_concreto_vc: Fraction           # Parcela resistida pelo concreto Vc (kN)
    armadura_estribos_asw_s: Fraction        # Armadura transversal por metro Asw/s (cm²/m)
    armadura_estribos_minima_asw_s: Fraction # Armadura mínima de estribos (cm²/m)

    # Verificação de Fadiga da Armadura
    variacao_tensao_fadiga: Fraction # Delta_sigma_s (MPa)
    limite_tensao_fadiga: Fraction   # Limite normativo Delta_fsd,fad (MPa) (ex: 90 MPa)
    fadiga_atendida: bool            # True se Delta_sigma_s <= limite

    # Verificação do Estado Limite de Deformação (ELS-DEF)
    flecha_imediata: Fraction        # Flecha imediata sob carga permanente e móvel (m)
    flecha_total_diferida: Fraction  # Flecha total considerando fluência a longo prazo (m)
    flecha_admissivel: Fraction      # Limite normativo L/1000 (m)
    flecha_atendida: bool            # True se flecha_total <= flecha_admissivel

    # Dimensionamento dos Aparelhos de Apoio de Neoprene
    reacao_apoio_maxima_k: Fraction  # Reação característica máxima no apoio (kN)
    area_apoio_necessaria: Fraction  # Área mínima do elastômero A_nec (m²)
    area_apoio_adotada: Fraction     # Área adotada do elastômero A_adot (m²)
    tensao_contato_apoio: Fraction   # Tensão média de contato sigma_m (kPa)
    apoio_neoprene_atendido: bool    # True se tensao <= tensao_admissivel

    # Status Global
    aprovado_geral: bool             # True se todos os estados limites forem satisfeitos
