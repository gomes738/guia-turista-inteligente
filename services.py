# Serviços de integração com APIs externas (Google OAuth, Open-Meteo e OSRM)

import re
import unicodedata
from typing import Any

import httpx

from config import ESTADOS_BRASIL, GOOGLE_CLIENT_ID

# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 1: APIs REST, Autenticação JWT e Geocodificação
# ==============================================================================


def verificar_token_google(client: httpx.Client, token: str) -> dict[str, Any] | None:
    """Valida o token JWT no endpoint oficial 'https://oauth2.googleapis.com/tokeninfo'.

    Verifica se o token foi emitido para o GOOGLE_CLIENT_ID configurado no projeto
    e retorna o payload do usuário (sub, name, email, picture) ou None se for inválido.
    """
    # TODO (Aluno 1): Implementar a validação do token JWT junto à API do Google OAuth2
    pass


def _normalizar(texto: str) -> str:
    """Remove acentos, espaços extras e caixa alta para comparar nomes de estados."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().strip().lower()


def obter_sigla_uf(admin1: str, uf_informada: str = "") -> str:
    """Converte o estado retornado pela API (admin1) para a sigla oficial de 2 letras (ex: 'PI').

    Caso a API retorne um nome completo (ex: 'Piauí'), normaliza para a sigla 'PI'.
    Caso contrário, utiliza a UF informada como fallback se for válida.
    """
    alvo = _normalizar(admin1 or "")
    for sigla, nome in ESTADOS_BRASIL.items():
        if alvo in (_normalizar(nome), sigla.lower()):
            return sigla
    uf = (uf_informada or "").strip().upper()
    return uf if uf in ESTADOS_BRASIL else ""


def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
    """Consulta o Open-Meteo Geocoding com filtro Brasil (country_codes=BR) e timeout=4.0s.

    Retorna a tupla (latitude, longitude, nome_formatado). Caso a busca falhe,
    aplica fallback seguro retornando (0.0, 0.0, "Cidade - UF").
    """
    uf_informada = (uf or "").strip().upper()
    fallback = (0.0, 0.0, f"{cidade} - {uf_informada}" if uf_informada else cidade)
    try:
        resp = client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": cidade,
                "count": 10,
                "language": "pt",
                "format": "json",
                "countryCode": "BR",
            },
            timeout=4.0,
        )
        resp.raise_for_status()
        resultados = resp.json().get("results") or []
    except (httpx.HTTPError, ValueError):
        return fallback

    resultados = [r for r in resultados if r.get("country_code") == "BR"]
    if not resultados:
        return fallback

    # Prefere o resultado na UF informada; senão, o mais relevante (1º), corrigindo a UF pelo admin1
    escolhido = next(
        (r for r in resultados if obter_sigla_uf(r.get("admin1", "")) == uf_informada),
        resultados[0],
    )
    sigla = obter_sigla_uf(escolhido.get("admin1", ""), uf_informada)
    nome = f"{escolhido['name']} - {sigla}" if sigla else escolhido["name"]
    return float(escolhido["latitude"]), float(escolhido["longitude"]), nome


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 2: Telemetria Climática e Roteamento Rodoviário
# ==============================================================================


def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
    """Consulta o Open-Meteo Forecast e retorna temperatura (°C), umidade (%) e vento (km/h).

    Caso coordenadas sejam inválidas (0.0, 0.0) ou ocorra timeout (4.0s),
    retorna dicionário de contingência com valores 'N/D'.
    """
    # TODO (Aluno 2): Implementar a consulta à API Open-Meteo Forecast com timeout e fallback
    pass


def obter_percurso(
    client: httpx.Client, lat_o: float, lon_o: float, lat_d: float, lon_d: float
) -> dict[str, str]:
    """Consulta o OSRM e calcula distância em km e duração de viagem de carro.

    Em caso de trajetos sem estradas (ex: ilhas) ou timeout (6.0s),
    retorna dicionário com fallback descritivo ('Sem rota direta' / 'Considere voos ou barcos').
    """
    # TODO (Aluno 2): Implementar o cálculo de rota e distância via OSRM com conversão de unidades
    pass
