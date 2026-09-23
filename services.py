# Serviços de integração com APIs externas (Google OAuth, Open-Meteo e OSRM)

import re
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


def obter_sigla_uf(admin1: str, uf_informada: str = "") -> str:
    """Converte o estado retornado pela API (admin1) para a sigla oficial de 2 letras (ex: 'PI').

    Caso a API retorne um nome completo (ex: 'Piauí'), normaliza para a sigla 'PI'.
    Caso contrário, utiliza a UF informada como fallback se for válida.
    """
    # TODO (Aluno 1): Implementar a conversão e normalização da UF
    pass


def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
    """Consulta o Open-Meteo Geocoding com filtro Brasil (country_codes=BR) e timeout=4.0s.

    Retorna a tupla (latitude, longitude, nome_formatado). Caso a busca falhe,
    aplica fallback seguro retornando (0.0, 0.0, "Cidade - UF").
    """
    # TODO (Aluno 1): Implementar a consulta à API de Geocodificação Open-Meteo com filtro Brasil
    pass


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 2: Telemetria Climática e Roteamento Rodoviário
# ==============================================================================


def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
    """Consulta o Open-Meteo Forecast e retorna temperatura (°C), umidade (%) e vento (km/h).

    Caso coordenadas sejam inválidas (0.0, 0.0) ou ocorra timeout (4.0s),
    retorna dicionário de contingência com valores 'N/D'.
    """
    if lat == 0.0 and lon == 0.0:
        return {"temperatura": "N/D", "umidade": "N/D", "vento": "N/D"}

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        "&timezone=auto"
    )

    try:
        resposta = client.get(url, timeout=4.0)
        resposta.raise_for_status()
        dados = resposta.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return {"temperatura": "N/D", "umidade": "N/D", "vento": "N/D"}

    atual = dados.get("current") or {}
    temperatura = atual.get("temperature_2m")
    umidade = atual.get("relative_humidity_2m")
    vento = atual.get("wind_speed_10m")

    if temperatura is None or umidade is None or vento is None:
        return {"temperatura": "N/D", "umidade": "N/D", "vento": "N/D"}

    return {
        "temperatura": f"{float(temperatura):.1f} °C",
        "umidade": f"{int(umidade)}%",
        "vento": f"{float(vento):.1f} km/h",
    }


def obter_percurso(
    client: httpx.Client, lat_o: float, lon_o: float, lat_d: float, lon_d: float
) -> dict[str, str]:
    """Consulta o OSRM e calcula distância em km e duração de viagem de carro.

    Em caso de trajetos sem estradas (ex: ilhas) ou timeout (6.0s),
    retorna dicionário com fallback descritivo ('Sem rota direta' / 'Considere voos ou barcos').
    """
    if lat_o == 0.0 and lon_o == 0.0 and lat_d == 0.0 and lon_d == 0.0:
        return {"distancia": "Sem rota direta", "tempo": "Considere voos ou barcos"}

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon_o},{lat_o};{lon_d},{lat_d}?overview=false"
    )

    try:
        resposta = client.get(url, timeout=6.0)
        resposta.raise_for_status()
        payload = resposta.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return {"distancia": "Sem rota direta", "tempo": "Considere voos ou barcos"}

    rotas = payload.get("routes") or []
    if not rotas:
        return {"distancia": "Sem rota direta", "tempo": "Considere voos ou barcos"}

    rota = rotas[0]
    distancia_m = rota.get("distance")
    duracao_s = rota.get("duration")
    if distancia_m is None or duracao_s is None:
        return {"distancia": "Sem rota direta", "tempo": "Considere voos ou barcos"}

    distancia_km = round(float(distancia_m) / 1000, 1)
    horas = int(float(duracao_s) // 3600)
    minutos = int((float(duracao_s) % 3600) // 60)

    if horas and minutos:
        tempo = f"{horas} h {minutos} min"
    elif horas:
        tempo = f"{horas} h"
    elif minutos:
        tempo = f"{minutos} min"
    else:
        tempo = "< 1 min"

    return {"distancia": f"{distancia_km:.1f} km", "tempo": tempo}
