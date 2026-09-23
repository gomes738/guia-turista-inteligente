# Módulo de Inteligência Artificial Gemini & Fallback (Guia Turístico e Culinária)

import concurrent.futures
import re
from typing import Any

from google import genai

from config import GEMINI_KEY

# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 2: Inteligência Artificial (Gemini AI) & Fallback
# ==============================================================================


def limpar_formato_texto(texto: str) -> str:
    """Remove marcações residuais de markdown (** ou *), hashtags, crases e saudações, mantendo apenas emojis."""
    if not texto:
        return ""

    texto = texto.replace("\r\n", "\n")
    texto = re.sub(r"```[\s\S]*?```", " ", texto)
    texto = re.sub(r"(?m)^\s*#{1,6}\s*", "", texto)
    texto = re.sub(r"(?m)^\s*[-*+•]\s*", "", texto)
    texto = re.sub(r"\*\*|__|\*|_|`", "", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", texto)
    texto = re.sub(
        r"(?i)\b(?:ol[aá]|oi|olá|hello|hi|sauda[cç][aã]o|segue|aqui\s+vai|segue\s+abaixo)\b.*?\n?",
        "",
        texto,
    )
    texto = re.sub(r"(?m)^\s*\n+", "", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _gerar_guia_contingencia(destino: str) -> str:
    destino_formatado = (destino or "seu destino").strip() or "seu destino"
    return (
        f"🌍 Guia de contingência para {destino_formatado}\n\n"
        "🏛️ Comece pelo centro histórico e pelos pontos mais icônicos da cidade.\n"
        "🍽️ Experimente pratos típicos da região, cafés locais e mercados tradicionais.\n"
        "🚶 Atravessando a cidade a pé ou de transporte local, reserve tempo para mirantes, praças e vistas panorâmicas.\n"
        "🛍️ Inclua momentos para compras de souvenirs, gastronomia e pequenos passeios culturais.\n"
        "💡 Dica: confirme horários, reservas e clima antes de sair para aproveitar melhor a visita."
    )


def _consultar_gemini(prompt: str) -> str:
    client = genai.Client(api_key=GEMINI_KEY)
    resposta = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    if hasattr(resposta, "text") and resposta.text:
        return resposta.text
    return str(resposta)


def obter_guia_destino_com_diagnostico(destino: str) -> tuple[str, dict[str, Any]]:
    """Invoca o modelo 'gemini-3.6-flash' com timeout de 6.0s em ThreadPoolExecutor.

    Em caso de timeout, chave inválida ou ausência de cota, aciona automaticamente
    o gerador de contingência com roteiro estruturado em texto puro com emojis.
    Retorna a tupla (texto_guia, diagnostico_metadados).
    """
    destino_limpo = (destino or "").strip() or "destino"
    prompt = (
        f"Crie um guia turístico e culinário para {destino_limpo} em texto puro, sem Markdown, "
        "com emojis e linguagem clara. Inclua atrações, gastronomia local, dicas de transporte e "
        "recomendação de roteiro em poucas seções. Responda apenas com o guia, sem introdução nem explicações."
    )

    if not GEMINI_KEY:
        texto_fallback = _gerar_guia_contingencia(destino_limpo)
        diagnostico = {
            "destino": destino_limpo,
            "status": "fallback",
            "fallback_utilizado": True,
            "motivo": "chave_vazia",
            "modelo": "gemini-3.6-flash",
        }
        return texto_fallback, diagnostico

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    futuro = executor.submit(_consultar_gemini, prompt)

    try:
        resposta = futuro.result(timeout=6.0)
        texto = limpar_formato_texto(resposta)
        if not texto:
            raise ValueError("resposta vazia")
        diagnostico = {
            "destino": destino_limpo,
            "status": "sucesso",
            "fallback_utilizado": False,
            "modelo": "gemini-3.6-flash",
        }
        executor.shutdown(wait=False, cancel_futures=True)
        return texto, diagnostico
    except (concurrent.futures.TimeoutError, ValueError, TypeError, Exception) as exc:
        futuro.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        texto_fallback = _gerar_guia_contingencia(destino_limpo)
        diagnostico = {
            "destino": destino_limpo,
            "status": "fallback",
            "fallback_utilizado": True,
            "motivo": type(exc).__name__,
            "modelo": "gemini-3.6-flash",
        }
        return texto_fallback, diagnostico


def obter_guia_destino(destino: str) -> str:
    """Wrapper utilitário que retorna apenas o texto do guia."""
    texto, _ = obter_guia_destino_com_diagnostico(destino)
    return texto
