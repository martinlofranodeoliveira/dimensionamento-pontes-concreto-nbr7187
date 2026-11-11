"""Exportadores de dados e relatórios técnicos do dimensionamento de pontes.

Inclui:
- Memorial de cálculo descritivo em texto plano;
- CSV sanitizado contra injeção de fórmulas;
- Painel vetorial SVG em alta definição (1440x900);
- Gerador determinístico de pacote ZIP com flag O_EXCL.
"""

import os
import zipfile
from fractions import Fraction
from typing import Dict, Any

from .models import (
    ParametrosVao,
    GeometriaSecao,
    AparelhoApoio,
    ClasseTremTipo,
    ClasseConcreto,
    AcoArmadura,
    ResultadoDimensionamentoPonte,
)
from .codecs import codificar_json_estrito


def sanitizar_campo_csv(valor: Any) -> str:
    """Sanitiza strings para CSV prevenindo injeção de fórmulas (DDE/CSV Injection)."""
    texto = str(valor)
    caracteres_perigosos = ("=", "+", "-", "@", "\t", "\r")
    if any(texto.startswith(c) for c in caracteres_perigosos):
        return "'" + texto
    return texto


def exportar_memorial_texto(
    vao: ParametrosVao,
    secao: GeometriaSecao,
    apoio: AparelhoApoio,
    resultado: ResultadoDimensionamentoPonte,
    trem_tipo: ClasseTremTipo = ClasseTremTipo.TB_450,
    fck: ClasseConcreto = ClasseConcreto.C35,
    aco: AcoArmadura = AcoArmadura.CA_50,
) -> str:
    """Gera o memorial de cálculo analítico completo em formato de texto descritivo."""
    linhas = [
        "=" * 82,
        "          LOFRANO TECNOLOGIA - ENGENHARIA DE ESTRUTURAS E OBRAS DE ARTE",
        "         MEMORIAL DE CÁLCULO ESTRUTURAL DE PONTE RODOVIÁRIA DE CONCRETO",
        "         Normas: ABNT NBR 7187:2021, ABNT NBR 7188:2013 e ABNT NBR 6118:2023",
        "=" * 82,
        "",
        "1. CARACTERÍSTICAS GERAIS E GEOMETRIA DO VÃO",
        f"  - Comprimento do Vão Livre de Cálculo (L): {float(vao.vao_livre):.2f} m",
        f"  - Largura Útil da Pista de Rolamento:     {float(vao.largura_pista):.2f} m",
        f"  - Largura Total dos Passeios:              {float(vao.largura_passeios):.2f} m",
        f"  - Número de Faixas de Tráfego:             {vao.num_faixas}",
        f"  - Número de Vigas Principais:              {vao.num_vigas}",
        f"  - Espessura do Pavimento Asfáltico:        {float(vao.espessura_pavimento)*100:.1f} cm",
        f"  - Carga Total de Barreiras New Jersey:     {float(vao.peso_barreiras):.2f} kN/m",
        "",
        "2. SEÇÃO TRANSVERSAL E PROPRIEDADES DOS MATERIAIS",
        f"  - Altura Total da Viga (h):                {float(secao.altura_total):.2f} m",
        f"  - Largura da Alma da Viga (bw):            {float(secao.largura_alma):.2f} m",
        f"  - Largura Colaborante da Mesa (bf):        {float(secao.largura_mesa):.2f} m",
        f"  - Espessura da Mesa Superior (hf):         {float(secao.espessura_mesa):.2f} m",
        f"  - Altura Útil da Armadura de Tração (d):   {float(secao.d_util):.2f} m",
        f"  - Cobrimento Nominal da Armadura (c_nom):  {float(secao.cobrimento)*100:.1f} cm",
        f"  - Concreto Estrutural:                     {fck.name} (fck = {fck.value} MPa)",
        f"  - Aço para Armaduras:                      {aco.name} (fyk = {aco.value} MPa)",
        "",
        "3. COEFICIENTES DE MAJORAÇÃO DINÂMICA (ABNT NBR 7187)",
        f"  - Coeficiente de Impacto Vertical (CIV):   {float(resultado.civ):.4f}",
        f"  - Coeficiente de Número de Faixas (CNF):   {float(resultado.cnf):.4f}",
        f"  - Coeficiente de Impacto Adicional (CIA):  {float(resultado.cia):.4f}",
        f"  - Majoração Dinâmica Total (CMD):          {float(resultado.cmd):.4f}",
        "",
        "4. AÇÕES PERMANENTES POR VIGA PRINCIPAL (kN/m)",
        f"  - Peso Próprio da Alma:                    {float(resultado.peso_proprio_viga):.2f} kN/m",
        f"  - Peso Próprio da Mesa / Laje:             {float(resultado.peso_proprio_laje):.2f} kN/m",
        f"  - Revestimento Pavimentação Asfáltica:     {float(resultado.peso_pavimento):.2f} kN/m",
        f"  - Barreiras e Equipamentos:                {float(vao.peso_barreiras / vao.num_vigas):.2f} kN/m",
        f"  - Carga Permanente Total por Viga (g):     {float(resultado.peso_permanente_total):.2f} kN/m",
        "",
        "5. CARGA MÓVEL E LINHAS DE INFLUÊNCIA (TREM-TIPO " + trem_tipo.value + ")",
        f"  - Peso Total do Veículo de Projeto:        {float(resultado.carga_eixo_veiculo * resultado.num_eixos):.1f} kN ({resultado.num_eixos} eixos de {float(resultado.carga_eixo_veiculo):.1f} kN)",
        f"  - Carga Distribuída de Multidão (q):       {float(resultado.carga_multidao_q):.2f} kN/m²",
        f"  - Carga em Passeios de Pedestres:          {float(resultado.carga_passeio):.2f} kN/m²",
        "",
        "6. ESFORÇOS SOLICITANTES NO MEIO DO VÃO E APOIOS",
        f"  - Momento Fletor Permanente (Mg,k):        {float(resultado.momento_permanente_k):.2f} kNm",
        f"  - Momento Fletor do Veículo (M_veic,k):    {float(resultado.momento_veiculo_k):.2f} kNm",
        f"  - Momento Fletor da Multidão (Mq,k):       {float(resultado.momento_multidao_k):.2f} kNm",
        f"  - Momento Fletor Móvel Total (M_movel,k):  {float(resultado.momento_movel_total_k):.2f} kNm",
        f"  - MOMENTO FLETOR DE CÁLCULO (Md,total):    {float(resultado.momento_total_d):.2f} kNm",
        "",
        f"  - Esforço Cortante Permanente (Vg,k):      {float(resultado.cortante_permanente_k):.2f} kN",
        f"  - Esforço Cortante do Veículo (V_veic,k):  {float(resultado.cortante_veiculo_k):.2f} kN",
        f"  - Esforço Cortante da Multidão (Vq,k):     {float(resultado.cortante_multidao_k):.2f} kN",
        f"  - Esforço Cortante Móvel Total (V_movel,k):{float(resultado.cortante_movel_total_k):.2f} kN",
        f"  - ESFORÇO CORTANTE DE CÁLCULO (Vd,total):  {float(resultado.cortante_total_d):.2f} kN",
        "",
        "7. DIMENSIONAMENTO NO ESTADO LIMITE ÚLTIMO (ELU)",
        f"  - Posição da Linha Neutra (x):             {float(resultado.altura_linha_neutra_x):.4f} m",
        f"  - Razão x/d:                               {float(resultado.relacao_x_d):.4f} (Limite: {float(resultado.limite_x_d):.2f})",
        f"  - Ductilidade da Seção:                    {'CONFORME (Domínio 2/3)' if resultado.ductilidade_atendida else 'NÃO CONFORME'}",
        f"  - Área de Armadura Longitudinal (As):      {float(resultado.armadura_longitudinal_as):.2f} cm²",
        f"  - Taxa Geométrica de Armadura (rho_s):     {float(resultado.taxa_armadura_longitudinal):.3f} %",
        f"  - Cortante Resistente da Biela (VRd2):     {float(resultado.cortante_resistencia_biela_vrd2):.2f} kN",
        f"  - Verificação de Esmagamento da Biela:     {'CONFORME (Vd <= VRd2)' if resultado.biela_comprimida_atendida else 'FALHA DE BIELA'}",
        f"  - Parcela Resistida pelo Concreto (Vc):    {float(resultado.cortante_concreto_vc):.2f} kN",
        f"  - Armadura Transversal Estribos (Asw/s):   {float(resultado.armadura_estribos_asw_s):.2f} cm²/m",
        f"  - Armadura Transversal Mínima:             {float(resultado.armadura_estribos_minima_asw_s):.2f} cm²/m",
        "",
        "8. VERIFICAÇÃO DE FADIGA DA ARMADURA (NBR 7187 item 11)",
        f"  - Variação de Tensão Cíclica (Delta_sigma):{float(resultado.variacao_tensao_fadiga):.2f} MPa",
        f"  - Limite Resistente à Fadiga:              {float(resultado.limite_tensao_fadiga):.2f} MPa",
        f"  - Avaliação de Fadiga:                     {'CONFORME (Delta_sigma <= Limite)' if resultado.fadiga_atendida else 'FALHA POR FADIGA'}",
        "",
        "9. VERIFICAÇÃO DO ESTADO LIMITE DE DEFORMAÇÃO (ELS-DEF)",
        f"  - Flecha Imediata (Carga Móvel):           {float(resultado.flecha_imediata)*1000:.2f} mm",
        f"  - Flecha Total Diferida no Tempo:          {float(resultado.flecha_total_diferida)*1000:.2f} mm",
        f"  - Flecha Admissível (L/1000):              {float(resultado.flecha_admissivel)*1000:.2f} mm",
        f"  - Avaliação de Flecha:                     {'CONFORME (delta_tot <= L/1000)' if resultado.flecha_atendida else 'FLECHA EXCESSIVA'}",
        "",
        "10. DIMENSIONAMENTO DO APARELHO DE APOIO DE NEOPRENE FRETADO",
        f"  - Dimensões do Neoprene (a x b x e):       {float(apoio.comprimento_a)*100:.0f} cm x {float(apoio.largura_b)*100:.0f} cm x {float(apoio.espessura_elastometro)*100:.0f} cm",
        f"  - Reação Máxima de Serviço (R_max,k):      {float(resultado.reacao_apoio_maxima_k):.2f} kN",
        f"  - Tensão Média de Contato:                 {float(resultado.tensao_contato_apoio)/1000:.2f} MPa",
        f"  - Tensão Média Admissível:                 {float(apoio.tensao_admissivel)/1000:.2f} MPa",
        f"  - Avaliação do Aparelho de Apoio:          {'CONFORME' if resultado.apoio_neoprene_atendido else 'TENSÃO EXCESSIVA'}",
        "",
        "=" * 82,
        f"STATUS GLOBAL DA ESTRUTURA: {'APROVADO EM TODOS OS CRITÉRIOS' if resultado.aprovado_geral else 'REQUER AJUSTE DE SEÇÃO'}",
        "=" * 82,
    ]
    return "\n".join(linhas) + "\n"


def exportar_csv_sanitizado(resultado: ResultadoDimensionamentoPonte) -> str:
    """Gera um arquivo CSV estruturado e sanitizado contra injeção de fórmulas."""
    registros = [
        ("Parametro", "Valor_Racional", "Valor_Decimal", "Unidade", "Conforme"),
        ("CIV", f"{resultado.civ.numerator}/{resultado.civ.denominator}", f"{float(resultado.civ):.4f}", "-", "SIM"),
        ("CNF", f"{resultado.cnf.numerator}/{resultado.cnf.denominator}", f"{float(resultado.cnf):.4f}", "-", "SIM"),
        ("CIA", f"{resultado.cia.numerator}/{resultado.cia.denominator}", f"{float(resultado.cia):.4f}", "-", "SIM"),
        ("CMD", f"{resultado.cmd.numerator}/{resultado.cmd.denominator}", f"{float(resultado.cmd):.4f}", "-", "SIM"),
        ("Peso_Permanente_Total_g", f"{resultado.peso_permanente_total.numerator}/{resultado.peso_permanente_total.denominator}", f"{float(resultado.peso_permanente_total):.2f}", "kN/m", "SIM"),
        ("Momento_Permanente_Mgk", f"{resultado.momento_permanente_k.numerator}/{resultado.momento_permanente_k.denominator}", f"{float(resultado.momento_permanente_k):.2f}", "kNm", "SIM"),
        ("Momento_Movel_Mqk", f"{resultado.momento_movel_total_k.numerator}/{resultado.momento_movel_total_k.denominator}", f"{float(resultado.momento_movel_total_k):.2f}", "kNm", "SIM"),
        ("Momento_Calculo_Md", f"{resultado.momento_total_d.numerator}/{resultado.momento_total_d.denominator}", f"{float(resultado.momento_total_d):.2f}", "kNm", "SIM"),
        ("Cortante_Calculo_Vd", f"{resultado.cortante_total_d.numerator}/{resultado.cortante_total_d.denominator}", f"{float(resultado.cortante_total_d):.2f}", "kN", "SIM"),
        ("Linha_Neutra_x", f"{resultado.altura_linha_neutra_x.numerator}/{resultado.altura_linha_neutra_x.denominator}", f"{float(resultado.altura_linha_neutra_x):.4f}", "m", "SIM"),
        ("Razao_x_d", f"{resultado.relacao_x_d.numerator}/{resultado.relacao_x_d.denominator}", f"{float(resultado.relacao_x_d):.4f}", "-", "SIM" if resultado.ductilidade_atendida else "NAO"),
        ("Armadura_Longitudinal_As", f"{resultado.armadura_longitudinal_as.numerator}/{resultado.armadura_longitudinal_as.denominator}", f"{float(resultado.armadura_longitudinal_as):.2f}", "cm²", "SIM"),
        ("VRd2_Biela", f"{resultado.cortante_resistencia_biela_vrd2.numerator}/{resultado.cortante_resistencia_biela_vrd2.denominator}", f"{float(resultado.cortante_resistencia_biela_vrd2):.2f}", "kN", "SIM" if resultado.biela_comprimida_atendida else "NAO"),
        ("Armadura_Estribos_Asw_s", f"{resultado.armadura_estribos_asw_s.numerator}/{resultado.armadura_estribos_asw_s.denominator}", f"{float(resultado.armadura_estribos_asw_s):.2f}", "cm²/m", "SIM"),
        ("Variacao_Tensao_Fadiga", f"{resultado.variacao_tensao_fadiga.numerator}/{resultado.variacao_tensao_fadiga.denominator}", f"{float(resultado.variacao_tensao_fadiga):.2f}", "MPa", "SIM" if resultado.fadiga_atendida else "NAO"),
        ("Flecha_Total_Diferida", f"{resultado.flecha_total_diferida.numerator}/{resultado.flecha_total_diferida.denominator}", f"{float(resultado.flecha_total_diferida)*1000:.2f}", "mm", "SIM" if resultado.flecha_atendida else "NAO"),
        ("Tensao_Contato_Neoprene", f"{resultado.tensao_contato_apoio.numerator}/{resultado.tensao_contato_apoio.denominator}", f"{float(resultado.tensao_contato_apoio)/1000:.2f}", "MPa", "SIM" if resultado.apoio_neoprene_atendido else "NAO"),
        ("Status_Global", "1/1", "1.0", "-", "SIM" if resultado.aprovado_geral else "NAO"),
    ]
    linhas = []
    for reg in registros:
        linhas.append(";".join(sanitizar_campo_csv(c) for c in reg))
    return "\n".join(linhas) + "\n"


def exportar_svg_painel(
    vao: ParametrosVao,
    secao: GeometriaSecao,
    apoio: AparelhoApoio,
    resultado: ResultadoDimensionamentoPonte,
    trem_tipo: ClasseTremTipo = ClasseTremTipo.TB_450,
    fck: ClasseConcreto = ClasseConcreto.C35,
    aco: AcoArmadura = AcoArmadura.CA_50,
) -> str:
    """Gera um painel técnico vetorial SVG em alta resolução (1440x900)."""
    L = float(vao.vao_livre)
    h_viga = float(secao.altura_total)
    bw = float(secao.largura_alma)
    bf = float(secao.largura_mesa)
    hf = float(secao.espessura_mesa)
    b_pista = float(vao.largura_pista)
    b_pass = float(vao.largura_passeios)

    md = float(resultado.momento_total_d)
    vd = float(resultado.cortante_total_d)
    as_cm2 = float(resultado.armadura_longitudinal_as)
    asw = float(resultado.armadura_estribos_asw_s)
    flecha_mm = float(resultado.flecha_total_diferida) * 1000
    flecha_adm_mm = float(resultado.flecha_admissivel) * 1000
    tensao_neo_mpa = float(resultado.tensao_contato_apoio) / 1000
    fadiga_mpa = float(resultado.variacao_tensao_fadiga)

    status_cor = "#10b981" if resultado.aprovado_geral else "#ef4444"
    status_texto = "APROVADO (NBR 7187)" if resultado.aprovado_geral else "NÃO CONFORME"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 900" width="1440" height="900" style="background:#0b1120; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;">
  <defs>
    <linearGradient id="cabecalho-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="painel-card" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <linearGradient id="viga-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#0284c7" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="tabuleiro-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#64748b"/>
      <stop offset="100%" stop-color="#475569"/>
    </linearGradient>
    <filter id="sombra-suave" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000000" flood-opacity="0.4"/>
    </filter>
  </defs>

  <!-- Cabeçalho Principal -->
  <rect x="24" y="20" width="1392" height="84" rx="12" fill="url(#cabecalho-grad)" stroke="#334155" stroke-width="1.5" filter="url(#sombra-suave)"/>
  <text x="50" y="52" font-size="22" font-weight="700" fill="#f8fafc">LOFRANO TECNOLOGIA · DIMENSIONAMENTO DE PONTES RODOVIÁRIAS</text>
  <text x="50" y="80" font-size="14" fill="#94a3b8">Conformidade estrita: ABNT NBR 7187:2021 · ABNT NBR 7188:2013 (TB-450) · ABNT NBR 6118:2023 · Aritmética 100% Racional</text>

  <!-- Selo de Status Global -->
  <rect x="1190" y="38" width="206" height="48" rx="8" fill="{status_cor}" fill-opacity="0.15" stroke="{status_cor}" stroke-width="2"/>
  <circle cx="1212" cy="62" r="8" fill="{status_cor}"/>
  <text x="1230" y="68" font-size="15" font-weight="700" fill="{status_cor}">{status_texto}</text>

  <!-- CARD 1: ELEVAÇÃO LONGITUDINAL E TREM-TIPO TB-450 (x: 24, y: 120, w: 900, h: 360) -->
  <rect x="24" y="120" width="900" height="360" rx="12" fill="url(#painel-card)" stroke="#334155" stroke-width="1.5" filter="url(#sombra-suave)"/>
  <text x="50" y="152" font-size="16" font-weight="700" fill="#38bdf8">1. MODELO ESTRUTURAL LONGITUDINAL E TREM-TIPO TB-450</text>
  <text x="50" y="174" font-size="12" fill="#94a3b8">Vão Livre L = {L:.2f} m | 3 Eixos de 150 kN espaçados a 1,50 m | Multidão q = 5,0 kN/m² | CIV={float(resultado.civ):.3f} CNF={float(resultado.cnf):.2f}</text>

  <!-- Linha de Terra / Terreno -->
  <line x1="80" y1="410" x2="860" y2="410" stroke="#475569" stroke-width="2" stroke-dasharray="6,4"/>

  <!-- Aparelhos de Apoio de Neoprene (Pilares / Encontros) -->
  <!-- Apoio Esquerdo (x=120) -->
  <polygon points="120,380 90,410 150,410" fill="#475569" stroke="#64748b" stroke-width="1.5"/>
  <rect x="105" y="370" width="30" height="10" rx="2" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>
  <text x="95" y="426" font-size="11" fill="#94a3b8" font-weight="600">Apoio A (x=0)</text>

  <!-- Apoio Direito (x=820) -->
  <polygon points="820,380 790,410 850,410" fill="#475569" stroke="#64748b" stroke-width="1.5"/>
  <circle cx="805" cy="412" r="3" fill="#94a3b8"/>
  <circle cx="835" cy="412" r="3" fill="#94a3b8"/>
  <rect x="805" y="370" width="30" height="10" rx="2" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>
  <text x="795" y="426" font-size="11" fill="#94a3b8" font-weight="600">Apoio B (x={L:.1f}m)</text>

  <!-- Viga de Concreto Longa (x: 100 a 840, y: 310 a 370) -->
  <rect x="100" y="310" width="740" height="60" rx="4" fill="url(#viga-grad)" stroke="#0284c7" stroke-width="2"/>
  <rect x="90" y="295" width="760" height="15" rx="3" fill="url(#tabuleiro-grad)" stroke="#334155" stroke-width="1.5"/>

  <!-- Veículo TB-450 posicionado no meio do vão (x_centro = 470) -->
  <!-- Eixo 1 (x=410), Eixo 2 (x=470), Eixo 3 (x=530) -->
  <rect x="380" y="240" width="180" height="50" rx="6" fill="#3b82f6" fill-opacity="0.3" stroke="#60a5fa" stroke-width="1.5"/>
  <text x="470" y="260" font-size="11" font-weight="700" fill="#93c5fd" text-anchor="middle">VEÍCULO TB-450 (450 kN)</text>
  <text x="470" y="278" font-size="10" fill="#bfdbfe" text-anchor="middle">3 x 150 kN (Eixos a 1,50 m)</text>

  <!-- Setas dos 3 eixos de 150 kN -->
  <!-- Eixo 1 -->
  <line x1="410" y1="210" x2="410" y2="290" stroke="#ef4444" stroke-width="2.5"/>
  <polygon points="410,295 405,285 415,285" fill="#ef4444"/>
  <text x="410" y="204" font-size="11" font-weight="700" fill="#f87171" text-anchor="middle">150 kN</text>

  <!-- Eixo 2 (Central) -->
  <line x1="470" y1="210" x2="470" y2="290" stroke="#ef4444" stroke-width="2.5"/>
  <polygon points="470,295 465,285 475,285" fill="#ef4444"/>
  <text x="470" y="204" font-size="11" font-weight="700" fill="#f87171" text-anchor="middle">150 kN</text>

  <!-- Eixo 3 -->
  <line x1="530" y1="210" x2="530" y2="290" stroke="#ef4444" stroke-width="2.5"/>
  <polygon points="530,295 525,285 535,285" fill="#ef4444"/>
  <text x="530" y="204" font-size="11" font-weight="700" fill="#f87171" text-anchor="middle">150 kN</text>

  <!-- Carga de Multidão Distribuída (q = 5 kN/m²) -->
  <path d="M 120,290 L 370,290 M 570,290 L 820,290" stroke="#fbbf24" stroke-width="2" stroke-dasharray="4,4"/>
  <text x="245" y="280" font-size="11" fill="#fde047" text-anchor="middle">Multidão q = 5 kN/m²</text>
  <text x="695" y="280" font-size="11" fill="#fde047" text-anchor="middle">Multidão q = 5 kN/m²</text>

  <!-- Cota do Vão Livre -->
  <line x1="120" y1="445" x2="820" y2="445" stroke="#94a3b8" stroke-width="1.5"/>
  <line x1="120" y1="440" x2="120" y2="450" stroke="#94a3b8" stroke-width="1.5"/>
  <line x1="820" y1="440" x2="820" y2="450" stroke="#94a3b8" stroke-width="1.5"/>
  <text x="470" y="462" font-size="13" font-weight="700" fill="#e2e8f0" text-anchor="middle">Vão Livre Teórico L = {L:.2f} metros</text>

  <!-- CARD 2: SEÇÃO TRANSVERSAL DO TABULEIRO (x: 948, y: 120, w: 468, h: 360) -->
  <rect x="948" y="120" width="468" height="360" rx="12" fill="url(#painel-card)" stroke="#334155" stroke-width="1.5" filter="url(#sombra-suave)"/>
  <text x="974" y="152" font-size="16" font-weight="700" fill="#38bdf8">2. SEÇÃO TRANSVERSAL DO TABULEIRO</text>
  <text x="974" y="174" font-size="12" fill="#94a3b8">Largura Pista: {b_pista:.2f}m | h = {h_viga:.2f}m | bw = {bw:.2f}m | bf = {bf:.2f}m</text>

  <!-- Desenho esquemático da seção T com tabuleiro e barreiras -->
  <!-- Laje de Mesa (x: 980 a 1380, y: 220 a 245) -->
  <rect x="980" y="220" width="404" height="25" rx="2" fill="url(#tabuleiro-grad)" stroke="#475569" stroke-width="1.5"/>
  <!-- Revestimento Asfáltico (x: 1020 a 1344, y: 212 a 220) -->
  <rect x="1020" y="212" width="324" height="8" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <!-- Barreiras New Jersey Laterais -->
  <polygon points="985,220 995,190 1010,190 1015,220" fill="#94a3b8" stroke="#cbd5e1" stroke-width="1.5"/>
  <polygon points="1350,220 1355,190 1370,190 1380,220" fill="#94a3b8" stroke="#cbd5e1" stroke-width="1.5"/>

  <!-- Almas das duas Vigas Principais -->
  <!-- Viga Esquerda -->
  <rect x="1050" y="245" width="45" height="140" fill="url(#viga-grad)" stroke="#0284c7" stroke-width="1.5"/>
  <!-- Viga Direita -->
  <rect x="1270" y="245" width="45" height="140" fill="url(#viga-grad)" stroke="#0284c7" stroke-width="1.5"/>

  <!-- Aparelhos de Apoio Neoprene sob as vigas -->
  <rect x="1045" y="385" width="55" height="12" rx="2" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>
  <rect x="1265" y="385" width="55" height="12" rx="2" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>

  <!-- Armadura Longitudinal Ilustrativa nos fundos das vigas -->
  <circle cx="1062" cy="370" r="4" fill="#ef4444"/>
  <circle cx="1073" cy="370" r="4" fill="#ef4444"/>
  <circle cx="1083" cy="370" r="4" fill="#ef4444"/>
  <circle cx="1282" cy="370" r="4" fill="#ef4444"/>
  <circle cx="1293" cy="370" r="4" fill="#ef4444"/>
  <circle cx="1303" cy="370" r="4" fill="#ef4444"/>

  <!-- Cotas e anotações da seção transversal -->
  <text x="1182" y="206" font-size="11" fill="#cbd5e1" text-anchor="middle">Pista de Rolamento ({b_pista:.1f}m)</text>
  <text x="1000" y="184" font-size="10" fill="#94a3b8" text-anchor="middle">New Jersey</text>
  <text x="1365" y="184" font-size="10" fill="#94a3b8" text-anchor="middle">New Jersey</text>
  <text x="1072" y="415" font-size="10" fill="#f59e0b" text-anchor="middle">Neoprene</text>
  <text x="1292" y="415" font-size="10" fill="#f59e0b" text-anchor="middle">Neoprene</text>

  <rect x="974" y="435" width="416" height="32" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"/>
  <text x="1182" y="456" font-size="12" fill="#38bdf8" text-anchor="middle" font-weight="600">Armadura Long. As = {as_cm2:.1f} cm² | Estribos Asw/s = {asw:.1f} cm²/m</text>

  <!-- CARD 3: DIAGRAMAS DE ESFORÇOS SOLICITANTES M(x) e V(x) (x: 24, y: 504, w: 680, h: 366) -->
  <rect x="24" y="504" width="680" height="366" rx="12" fill="url(#painel-card)" stroke="#334155" stroke-width="1.5" filter="url(#sombra-suave)"/>
  <text x="50" y="534" font-size="16" font-weight="700" fill="#38bdf8">3. ENVOLTÓRIAS DE ESFORÇOS SOLICITANTES (ELU)</text>
  <text x="50" y="554" font-size="12" fill="#94a3b8">Momento Fletor Máximo Md = {md:.1f} kNm | Cortante Máximo Vd = {vd:.1f} kN</text>

  <!-- Diagrama de Momentos Fletores (Parábola com valor central máximo) -->
  <text x="50" y="585" font-size="13" font-weight="700" fill="#f43f5e">Momento Fletor Md(x) [kNm]</text>
  <line x1="70" y1="605" x2="650" y2="605" stroke="#64748b" stroke-width="1.5"/>
  <!-- Curva parabólica invertida (tracionando embaixo) -->
  <path d="M 70,605 Q 360,695 650,605" fill="#f43f5e" fill-opacity="0.15" stroke="#f43f5e" stroke-width="2.5"/>
  <line x1="360" y1="605" x2="360" y2="695" stroke="#f43f5e" stroke-width="1.5" stroke-dasharray="4,2"/>
  <circle cx="360" cy="695" r="4" fill="#f43f5e"/>
  <text x="360" y="718" font-size="13" font-weight="700" fill="#fda4af" text-anchor="middle">Md,max = {md:.1f} kNm (Meio do Vão)</text>

  <!-- Diagrama de Esforços Cortantes Vd(x) -->
  <text x="50" y="748" font-size="13" font-weight="700" fill="#10b981">Esforço Cortante Vd(x) [kN]</text>
  <line x1="70" y1="800" x2="650" y2="800" stroke="#64748b" stroke-width="1.5"/>
  <polygon points="70,760 360,800 650,840 650,800 70,800" fill="#10b981" fill-opacity="0.15"/>
  <line x1="70" y1="760" x2="650" y2="840" stroke="#10b981" stroke-width="2.5"/>
  <text x="95" y="752" font-size="12" font-weight="700" fill="#6ee7b7">+Vd = {vd:.1f} kN</text>
  <text x="625" y="855" font-size="12" font-weight="700" fill="#6ee7b7">-Vd = -{vd:.1f} kN</text>

  <!-- CARD 4: TABELA DE VERIFICAÇÃO NORMATIVA (x: 728, y: 504, w: 688, h: 366) -->
  <rect x="728" y="504" width="688" height="366" rx="12" fill="url(#painel-card)" stroke="#334155" stroke-width="1.5" filter="url(#sombra-suave)"/>
  <text x="754" y="534" font-size="16" font-weight="700" fill="#38bdf8">4. AUDITORIA DE CRITÉRIOS NORMATIVOS (NBR 7187 / NBR 6118)</text>

  <!-- Tabela de Verificações com Badges -->
  <!-- Linha 1: Flexão e Ductilidade -->
  <g transform="translate(754, 555)">
    <rect x="0" y="0" width="636" height="42" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="16" y="26" font-size="13" font-weight="600" fill="#f8fafc">Ductilidade e Posição Linha Neutra (x/d)</text>
    <text x="320" y="26" font-size="12" fill="#94a3b8">x/d = {float(resultado.relacao_x_d):.3f} (Limite: {float(resultado.limite_x_d):.2f})</text>
    <rect x="540" y="10" width="80" height="22" rx="4" fill="{'#10b981' if resultado.ductilidade_atendida else '#ef4444'}" fill-opacity="0.2"/>
    <text x="580" y="25" font-size="11" font-weight="700" fill="{'#34d399' if resultado.ductilidade_atendida else '#f87171'}" text-anchor="middle">{'CONFORME' if resultado.ductilidade_atendida else 'FALHA'}</text>
  </g>

  <!-- Linha 2: Biela de Compressão (VRd2) -->
  <g transform="translate(754, 605)">
    <rect x="0" y="0" width="636" height="42" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="16" y="26" font-size="13" font-weight="600" fill="#f8fafc">Esmagamento da Biela de Concreto (VRd2)</text>
    <text x="320" y="26" font-size="12" fill="#94a3b8">Vd = {vd:.1f} kN &lt; VRd2 = {float(resultado.cortante_resistencia_biela_vrd2):.1f} kN</text>
    <rect x="540" y="10" width="80" height="22" rx="4" fill="{'#10b981' if resultado.biela_comprimida_atendida else '#ef4444'}" fill-opacity="0.2"/>
    <text x="580" y="25" font-size="11" font-weight="700" fill="{'#34d399' if resultado.biela_comprimida_atendida else '#f87171'}" text-anchor="middle">{'CONFORME' if resultado.biela_comprimida_atendida else 'FALHA'}</text>
  </g>

  <!-- Linha 3: Fadiga da Armadura Longitudinal -->
  <g transform="translate(754, 655)">
    <rect x="0" y="0" width="636" height="42" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="16" y="26" font-size="13" font-weight="600" fill="#f8fafc">Fadiga da Armadura sob Carga Móvel Cíclica</text>
    <text x="320" y="26" font-size="12" fill="#94a3b8">Δσs = {fadiga_mpa:.1f} MPa &lt; {float(resultado.limite_tensao_fadiga):.0f} MPa</text>
    <rect x="540" y="10" width="80" height="22" rx="4" fill="{'#10b981' if resultado.fadiga_atendida else '#ef4444'}" fill-opacity="0.2"/>
    <text x="580" y="25" font-size="11" font-weight="700" fill="{'#34d399' if resultado.fadiga_atendida else '#f87171'}" text-anchor="middle">{'CONFORME' if resultado.fadiga_atendida else 'FALHA'}</text>
  </g>

  <!-- Linha 4: Deformação e Flecha (ELS-DEF) -->
  <g transform="translate(754, 705)">
    <rect x="0" y="0" width="636" height="42" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="16" y="26" font-size="13" font-weight="600" fill="#f8fafc">Flecha Total com Fluência (ELS-DEF)</text>
    <text x="320" y="26" font-size="12" fill="#94a3b8">δ_tot = {flecha_mm:.1f} mm &lt; L/1000 = {flecha_adm_mm:.1f} mm</text>
    <rect x="540" y="10" width="80" height="22" rx="4" fill="{'#10b981' if resultado.flecha_atendida else '#ef4444'}" fill-opacity="0.2"/>
    <text x="580" y="25" font-size="11" font-weight="700" fill="{'#34d399' if resultado.flecha_atendida else '#f87171'}" text-anchor="middle">{'CONFORME' if resultado.flecha_atendida else 'FALHA'}</text>
  </g>

  <!-- Linha 5: Aparelho de Apoio de Neoprene Fretado -->
  <g transform="translate(754, 755)">
    <rect x="0" y="0" width="636" height="42" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="16" y="26" font-size="13" font-weight="600" fill="#f8fafc">Tensão no Apoio de Neoprene Fretado</text>
    <text x="320" y="26" font-size="12" fill="#94a3b8">σm = {tensao_neo_mpa:.2f} MPa &lt; σadm = {float(apoio.tensao_admissivel)/1000:.0f} MPa</text>
    <rect x="540" y="10" width="80" height="22" rx="4" fill="{'#10b981' if resultado.apoio_neoprene_atendido else '#ef4444'}" fill-opacity="0.2"/>
    <text x="580" y="25" font-size="11" font-weight="700" fill="{'#34d399' if resultado.apoio_neoprene_atendido else '#f87171'}" text-anchor="middle">{'CONFORME' if resultado.apoio_neoprene_atendido else 'FALHA'}</text>
  </g>

  <!-- Rodapé Técnico -->
  <text x="754" y="845" font-size="11" fill="#64748b">LOFRANO TECNOLOGIA · Data de Emissão: 10/11/2026 · Software de Engenharia Open Source</text>
</svg>
"""
    return svg


def gerar_pacote_zip(
    caminho_zip: str,
    vao: ParametrosVao,
    secao: GeometriaSecao,
    apoio: AparelhoApoio,
    resultado: ResultadoDimensionamentoPonte,
    trem_tipo: ClasseTremTipo = ClasseTremTipo.TB_450,
    fck: ClasseConcreto = ClasseConcreto.C35,
    aco: AcoArmadura = AcoArmadura.CA_50,
) -> None:
    """Gera um pacote ZIP determinístico com proteção contra sobrescrita (O_EXCL)."""
    # Timestamp determinístico fixo
    data_hora_fixa = (2026, 1, 1, 0, 0, 0)

    # Conteúdos dos artefatos
    memorial = exportar_memorial_texto(vao, secao, apoio, resultado, trem_tipo, fck, aco)
    csv_conteudo = exportar_csv_sanitizado(resultado)
    json_conteudo = codificar_json_estrito(resultado)
    svg_conteudo = exportar_svg_painel(vao, secao, apoio, resultado, trem_tipo, fck, aco)

    arquivos = [
        ("memorial_descritivo_ponte.txt", memorial.encode("utf-8")),
        ("resultados_dimensionamento.csv", csv_conteudo.encode("utf-8")),
        ("resultados_dimensionamento.json", json_conteudo.encode("utf-8")),
        ("painel_dimensionamento_ponte.svg", svg_conteudo.encode("utf-8")),
    ]

    # Criação segura com O_CREAT | O_EXCL | O_WRONLY
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(caminho_zip, flags, 0o644)
    with os.fdopen(fd, "wb") as f_out:
        with zipfile.ZipFile(f_out, "w", zipfile.ZIP_DEFLATED) as zf:
            for nome_arquivo, dados in arquivos:
                zinfo = zipfile.ZipInfo(filename=nome_arquivo, date_time=data_hora_fixa)
                zinfo.external_attr = 0o644 << 16
                zf.writestr(zinfo, dados)
