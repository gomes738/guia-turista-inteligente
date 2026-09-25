"""Aplicação Flask Principal - Guia do Turista Inteligente (API Gateway em Python)."""

import json
import os
import re
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

import httpx
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from config import (
    DATA_DIR,
    ESTADOS_BRASIL,
    GOOGLE_CLIENT_ID,
    PORT,
    VIAGENS_FILE,
)
from planejamento import obter_guia_destino_com_diagnostico
from services import (
    buscar_coordenadas,
    obter_clima,
    obter_percurso,
    verificar_token_google,
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "guia-turista-secret-key-2026-python")

# Controle de concorrência para leitura e escrita segura no arquivo JSON
DATA_DIR.mkdir(parents=True, exist_ok=True)
lock_arquivo_json = threading.RLock()

# Armazenamento volátil de roteiros em memória para sessões de visitantes
viagens_visitante_memoria: dict[str, list[dict[str, Any]]] = {}

# Controle de concorrência e idempotência contra cliques duplicados
requisicoes_ativas: set[str] = set()
requisicoes_recentes: dict[str, float] = {}
lock_requisicoes = threading.Lock()


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 4: Persistência JSON, Sanitização e Manipulação
# ==============================================================================


def sanitizar_entrada(texto: str, max_len: int = 80) -> str:
    """Higieniza entradas de texto removendo tags HTML, caracteres de controle e espaços extras."""
    valor = str(texto or "")
    valor = re.sub(r"<[^>]*>", "", valor)
    valor = re.sub(r"[\x00-\x1f\x7f]", " ", valor)
    valor = re.sub(r"\s+", " ", valor).strip()
    return valor[:max(0, max_len)]


def criar_estrutura_padrao_viagens() -> dict[str, Any]:
    """Retorna a estrutura inicial do payload JSON de viagens com metadados e provedores."""
    return {
        "versao_schema": "1.0",
        "descricao": "Base consolidada de roteiros turísticos e telemetria por usuário",
        "atualizado_em": datetime.now().isoformat(),
        "total_usuarios": 0,
        "total_roteiros": 0,
        "provedores": {
            "geocoding": "Open-Meteo Geocoding API",
            "previsao_tempo": "Open-Meteo Forecast API",
            "roteamento": "OSRM Routing Engine",
            "inteligencia_artificial": "Google Gemini (gemini-3.6-flash)",
        },
        "usuarios": {},
    }


def carregar_dados_viagens_json() -> dict[str, Any]:
    """Lê a base completa de viagens de static/data/viagens.json de forma thread-safe com lock_arquivo_json."""
    with lock_arquivo_json:
        try:
            with open(VIAGENS_FILE, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
            return criar_estrutura_padrao_viagens()

    if not isinstance(dados, dict):
        return criar_estrutura_padrao_viagens()

    padrao = criar_estrutura_padrao_viagens()
    for chave, valor in padrao.items():
        if chave not in dados:
            dados[chave] = deepcopy(valor)
    if not isinstance(dados.get("usuarios"), dict):
        dados["usuarios"] = {}
    return dados


def salvar_dados_viagens_json(dados_completos: dict[str, Any]) -> None:
    """Persiste a base hierárquica em static/data/viagens.json com lock_arquivo_json e indentação de 2 espaços."""
    if not isinstance(dados_completos, dict):
        dados_completos = criar_estrutura_padrao_viagens()

    with lock_arquivo_json:
        usuarios = dados_completos.get("usuarios")
        if not isinstance(usuarios, dict):
            usuarios = {}
            dados_completos["usuarios"] = usuarios

        total_roteiros = 0
        for usuario in usuarios.values():
            if not isinstance(usuario, dict):
                continue
            roteiros = usuario.get("roteiros")
            if not isinstance(roteiros, list):
                roteiros = []
                usuario["roteiros"] = roteiros
            total_roteiros += len(roteiros)
            metadados = usuario.get("metadados")
            if not isinstance(metadados, dict):
                metadados = {}
                usuario["metadados"] = metadados
            metadados["total_roteiros"] = len(roteiros)
            metadados["atualizado_em"] = datetime.now().isoformat()

        dados_completos["total_usuarios"] = len(usuarios)
        dados_completos["total_roteiros"] = total_roteiros
        dados_completos["atualizado_em"] = datetime.now().isoformat()
        with open(VIAGENS_FILE, "w", encoding="utf-8") as arquivo:
            json.dump(dados_completos, arquivo, ensure_ascii=False, indent=2)


def obter_viagens_usuario(user_id: str) -> list[dict[str, Any]]:
    """Recupera a lista de roteiros: da memória para visitantes ou do arquivo JSON para logados."""
    if user_id.startswith("visitante-"):
        return list(viagens_visitante_memoria.get(user_id, []))

    dados = carregar_dados_viagens_json()
    usuario = dados.get("usuarios", {}).get(user_id, {})
    if not isinstance(usuario, dict):
        return []
    roteiros = usuario.get("roteiros", [])
    return list(roteiros) if isinstance(roteiros, list) else []


def adicionar_viagem_usuario(
    user_id: str,
    item: dict[str, Any],
    perfil_usuario: dict[str, Any] | None = None,
) -> None:
    """Adiciona um novo roteiro: na memória para visitante ou grava no JSON para usuário logado."""
    if user_id.startswith("visitante-"):
        viagens_visitante_memoria.setdefault(user_id, []).append(item)
        return

    with lock_arquivo_json:
        dados = carregar_dados_viagens_json()
        usuarios = dados.setdefault("usuarios", {})
        usuario = usuarios.setdefault(user_id, {})
        if not isinstance(usuario, dict):
            usuario = {}
            usuarios[user_id] = usuario
        usuario.setdefault("perfil", perfil_usuario or {})
        if perfil_usuario:
            usuario["perfil"] = perfil_usuario
        usuario.setdefault("metadados", {})
        roteiros = usuario.setdefault("roteiros", [])
        if not isinstance(roteiros, list):
            roteiros = []
            usuario["roteiros"] = roteiros
        roteiros.append(item)
        salvar_dados_viagens_json(dados)


def remover_viagem_usuario(user_id: str, viagem_id: str) -> None:
    """Remove um roteiro específico pelo ID."""
    if user_id.startswith("visitante-"):
        viagens = viagens_visitante_memoria.get(user_id, [])
        viagens_visitante_memoria[user_id] = [
            viagem for viagem in viagens if viagem.get("id") != viagem_id
        ]
        return

    with lock_arquivo_json:
        dados = carregar_dados_viagens_json()
        usuario = dados.get("usuarios", {}).get(user_id)
        if not isinstance(usuario, dict):
            return
        roteiros = usuario.get("roteiros", [])
        if not isinstance(roteiros, list):
            return
        usuario["roteiros"] = [
            viagem for viagem in roteiros
            if not isinstance(viagem, dict) or viagem.get("id") != viagem_id
        ]
        salvar_dados_viagens_json(dados)


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 3: Backend Gateway, Sessões, Rotas & Idempotência
# ==============================================================================


@app.route("/", methods=["GET"])
def index():
    """Renderiza a página principal (SSR com Jinja2)."""
    usuario = session.get("usuario")
    viagens = obter_viagens_usuario(usuario["id"]) if usuario else []

    return render_template(
        "index.html",
        usuario=usuario,
        viagens=viagens,
        ufs=ESTADOS_BRASIL,
        client_id=GOOGLE_CLIENT_ID,
    )


@app.route("/auth/google/callback", methods=["GET", "POST"])
def google_callback():
    """Recebe a credencial JWT do Google e valida 100% no Python."""
    token = request.form.get("credential", "").strip()
    if not token:
        return redirect(url_for("index"))

    with httpx.Client() as client:
        dados_google = verificar_token_google(client, token)

    if not dados_google or not dados_google.get("sub"):
        return redirect(url_for("index"))

    session["usuario"] = {
        "id": dados_google["sub"],
        "nome": dados_google.get("name", ""),
        "email": dados_google.get("email", ""),
        "foto": dados_google.get("picture", ""),
    }
    return redirect(url_for("index"))


@app.route("/auth/demo", methods=["GET"])
def login_demo():
    """Modo Visitante para desenvolvimento e testes locais."""
    usuario_atual = session.get("usuario")
    id_atual = usuario_atual.get("id", "") if usuario_atual else ""
    if id_atual.startswith("visitante-"):
        viagens_visitante_memoria.pop(id_atual, None)

    # Contrato com o Aluno 4: IDs com este prefixo identificam visitantes.
    visitante_id = f"visitante-{uuid.uuid4()}"
    session["usuario"] = {
        "id": visitante_id,
        "nome": "Viajante Convidado",
        "email": "visitante@guia.local",
        "foto": "https://ui-avatars.com/api/?name=Viajante+Convidado",
    }
    viagens_visitante_memoria[visitante_id] = []

    return redirect(url_for("index"))


@app.route("/auth/logout", methods=["GET"])
def logout():
    """Encerra a sessão e descarta a memória de visitante."""
    usuario = session.get("usuario")
    usuario_id = usuario.get("id", "") if usuario else ""
    if usuario_id.startswith("visitante-"):
        viagens_visitante_memoria.pop(usuario_id, None)

    session.clear()
    return redirect(url_for("index"))


@app.route("/viagens/criar", methods=["POST"])
def criar_viagem():
    """Processa o formulário de criação com deduplicação (locks) e orquestração de APIs."""
    usuario = session.get("usuario")
    if not isinstance(usuario, dict) or not usuario.get("id"):
        return redirect(url_for("index"))

    origem_cidade = sanitizar_entrada(request.form.get("origem_cidade", ""))
    origem_uf = sanitizar_entrada(request.form.get("origem_uf", ""), 2).upper()
    destino_cidade = sanitizar_entrada(request.form.get("destino_cidade", ""))
    destino_uf = sanitizar_entrada(request.form.get("destino_uf", ""), 2).upper()
    if not origem_cidade or not destino_cidade or not origem_uf or not destino_uf:
        return redirect(url_for("index"))

    usuario_id = str(usuario["id"])
    chave_requisicao = "|".join(
        (usuario_id, origem_cidade.casefold(), origem_uf, destino_cidade.casefold(), destino_uf)
    )
    agora = time.time()
    with lock_requisicoes:
        ultima_requisicao = requisicoes_recentes.get(chave_requisicao)
        if chave_requisicao in requisicoes_ativas or (
            ultima_requisicao is not None and agora - ultima_requisicao < 10
        ):
            return redirect(url_for("index"))
        requisicoes_ativas.add(chave_requisicao)

    try:
        with httpx.Client() as client:
            lat_origem, lon_origem, nome_origem = buscar_coordenadas(
                client, origem_cidade, origem_uf
            )
            lat_destino, lon_destino, nome_destino = buscar_coordenadas(
                client, destino_cidade, destino_uf
            )
            clima = obter_clima(client, lat_destino, lon_destino)
            percurso = obter_percurso(
                client,
                lat_origem,
                lon_origem,
                lat_destino,
                lon_destino,
            )

        dicas_destino, diagnostico_ia = obter_guia_destino_com_diagnostico(nome_destino)
        item = {
            "id": str(uuid.uuid4()),
            "criado_em": datetime.now().isoformat(),
            "origem": nome_origem,
            "destino": nome_destino,
            "geolocalizacao": {
                "origem": {"latitude": lat_origem, "longitude": lon_origem},
                "destino": {"latitude": lat_destino, "longitude": lon_destino},
            },
            "clima": clima,
            "percurso": percurso,
            "dicas_destino": dicas_destino,
            "diagnostico_ia": diagnostico_ia,
            "metadados": {
                "servicos": {
                    "geocoding": "concluido",
                    "previsao_tempo": "concluido",
                    "roteamento": "concluido",
                    "inteligencia_artificial": diagnostico_ia.get("status", "desconhecido"),
                }
            },
        }
        adicionar_viagem_usuario(usuario_id, item, usuario)
        with lock_requisicoes:
            requisicoes_recentes[chave_requisicao] = time.time()
    finally:
        with lock_requisicoes:
            requisicoes_ativas.discard(chave_requisicao)
            limite = time.time() - 60
            requisicoes_recentes_keys = [
                chave for chave, instante in requisicoes_recentes.items()
                if instante < limite
            ]
            for chave in requisicoes_recentes_keys:
                requisicoes_recentes.pop(chave, None)

    return redirect(url_for("index"))


@app.route("/viagens/deletar/<string:viagem_id>", methods=["POST"])
def deletar_viagem(viagem_id: str):
    """Exclui um roteiro da lista do usuário."""
    usuario = session.get("usuario")
    if isinstance(usuario, dict) and usuario.get("id"):
        remover_viagem_usuario(str(usuario["id"]), sanitizar_entrada(viagem_id, 120))
    return redirect(url_for("index"))


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 4: Endpoint REST e Error Handlers Globais
# ==============================================================================


@app.route("/viagens/json", methods=["GET"])
@app.route("/api/viagens/json", methods=["GET"])
@app.route("/api/viagens", methods=["GET"])
def ver_viagens_json():
    """Retorna a base consolidada de static/data/viagens.json com suporte dinâmico a visitantes."""
    dados = carregar_dados_viagens_json()
    usuario = session.get("usuario") or {}
    user_id = usuario.get("id", "") if isinstance(usuario, dict) else ""
    if user_id.startswith("visitante-"):
        dados["usuarios"][user_id] = {
            "perfil": deepcopy(usuario),
            "metadados": {
                "total_roteiros": len(viagens_visitante_memoria.get(user_id, [])),
                "atualizado_em": datetime.now().isoformat(),
                "persistencia": "memoria_temporaria",
            },
            "roteiros": deepcopy(viagens_visitante_memoria.get(user_id, [])),
        }
        dados["total_usuarios"] = len(dados["usuarios"])
        dados["total_roteiros"] = sum(
            len(usuario.get("roteiros", []))
            for usuario in dados["usuarios"].values()
            if isinstance(usuario, dict) and isinstance(usuario.get("roteiros"), list)
        )
    return jsonify(dados)


@app.errorhandler(405)
def metodo_nao_permitido(error):
    """Fallback para acessos GET em rotas POST (ex: digitar /viagens/criar na barra de endereços)."""
    return redirect(url_for("index"))


@app.errorhandler(404)
def pagina_nao_encontrada(error):
    """Fallback para rotas inexistentes redirecionando suavemente para a página principal."""
    return redirect(url_for("index"))


if __name__ == "__main__":
    print(f"🌍 Servidor Flask Guia do Turista rodando em http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
