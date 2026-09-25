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
    if not token:
        return None
    try:
        resp = client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=4.0,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        dados = resp.json()
    except ValueError:
        return None

    # Recusa tokens válidos emitidos para outro aplicativo
    if dados.get("aud") != GOOGLE_CLIENT_ID:
        return None

    return {
        "sub": dados.get("sub"),
        "name": dados.get("name", ""),
        "email": dados.get("email", ""),
        "picture": dados.get("picture", ""),
    }


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
    # Remove descrições entre parênteses (ex: "Fernando de Noronha (Distrito Estadual)")
    nome_cidade = re.sub(r"\s*\([^)]*\)", "", escolhido["name"]).strip()
    nome = f"{nome_cidade} - {sigla}" if sigla else nome_cidade
    return float(escolhido["latitude"]), float(escolhido["longitude"]), nome


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
