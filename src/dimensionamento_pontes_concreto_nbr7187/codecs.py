"""Codecs estritos compatíveis com RFC 8259 para serialização e desserialização.

Garante ausência absoluta de tipos float, rejeição de BOM, verificação de profundidade máxima
e proteção contra chaves duplicadas.
"""

import json
from fractions import Fraction
from typing import Any, Dict, List


class JSONDecodeStrictError(ValueError):
    """Erro lançado quando um payload JSON viola as diretrizes estritas da RFC 8259."""
    pass


def _converter_para_primitivos_estritos(obj: Any, profundidade: int = 0) -> Any:
    """Converte estruturas contendo Fraction e Enums para tipos primitivos seguros (str, int, dict, list)."""
    if profundidade > 32:
        raise JSONDecodeStrictError(f"Profundidade de aninhamento excedeu o limite máximo seguro de 32: {profundidade}")

    if isinstance(obj, float):
        raise TypeError(f"Proibição absoluta de ponto flutuante (float) violada: {obj}")

    if isinstance(obj, Fraction):
        return {
            "numerador": obj.numerator,
            "denominador": obj.denominator,
            "valor_decimal": str(round(float(obj), 4)),  # apenas representação textual amigável
            "racional": f"{obj.numerator}/{obj.denominator}",
        }

    if hasattr(obj, "value"):
        return obj.value

    if hasattr(obj, "__dataclass_fields__"):
        res = {}
        for campo in obj.__dataclass_fields__:
            valor = getattr(obj, campo)
            res[campo] = _converter_para_primitivos_estritos(valor, profundidade + 1)
        return res

    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"Chave de dicionário deve ser string: {k}")
            res[k] = _converter_para_primitivos_estritos(v, profundidade + 1)
        return res

    if isinstance(obj, (list, tuple)):
        return [_converter_para_primitivos_estritos(item, profundidade + 1) for item in obj]

    if isinstance(obj, (int, str, bool)) or obj is None:
        return obj

    raise TypeError(f"Tipo não serializável estritamente: {type(obj)}")


def codificar_json_estrito(obj: Any) -> str:
    """Serializa um objeto ou resultado para JSON segundo a RFC 8259 com chaves ordenadas."""
    dados_limpos = _converter_para_primitivos_estritos(obj)
    return json.dumps(dados_limpos, indent=2, sort_keys=True, ensure_ascii=False)


def _verificar_profundidade_e_chaves(dado: Any, profundidade: int = 0) -> None:
    """Verifica recursivamente a profundidade e a ausência de floats."""
    if profundidade > 32:
        raise JSONDecodeStrictError(f"Profundidade de aninhamento excedeu 32: {profundidade}")
    if isinstance(dado, float):
        raise JSONDecodeStrictError(f"Tipo float proibido detectado no JSON: {dado}")
    if isinstance(dado, dict):
        for k, v in dado.items():
            _verificar_profundidade_e_chaves(v, profundidade + 1)
    elif isinstance(dado, list):
        for item in dado:
            _verificar_profundidade_e_chaves(item, profundidade + 1)


def decodificar_json_estrito(texto_json: str) -> Dict[str, Any]:
    """Desserializa uma string JSON rejeitando BOM, floats e chaves duplicadas."""
    if not isinstance(texto_json, str):
        raise TypeError("Entrada deve ser string")

    # Rejeição de Byte Order Mark (BOM)
    if texto_json.startswith("\ufeff") or texto_json.startswith("\xef\xbb\xbf"):
        raise JSONDecodeStrictError("Byte Order Mark (BOM) proibido no início do payload JSON.")

    def _par_chaves_unicas(pares: List[tuple]) -> Dict[str, Any]:
        d = {}
        for chave, valor in pares:
            if chave in d:
                raise JSONDecodeStrictError(f"Chave duplicada detectada no payload JSON: '{chave}'")
            d[chave] = valor
        return d

    def _parse_float_proibido(s: str) -> Any:
        raise JSONDecodeStrictError(f"Float proibido detectado durante o parse de números: {s}")

    try:
        resultado = json.loads(
            texto_json,
            object_pairs_hook=_par_chaves_unicas,
            parse_float=_parse_float_proibido,
        )
    except json.JSONDecodeError as err:
        raise JSONDecodeStrictError(f"Erro de sintaxe JSON: {err}") from err

    _verificar_profundidade_e_chaves(resultado)
    return resultado
