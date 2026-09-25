"""Aplicação Flask Principal - Guia do Turista Inteligente (API Gateway em Python)."""

import json
import os
import re
import threading
from copy import deepcopy
import time
import uuid
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
    # TODO (Aluno 4): Implementar inserção de novo roteiro na estrutura de dados
    pass


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


@app.route("/auth/google/callback", methods=["POST"])
def google_callback():
    """Recebe a credencial JWT do Google e valida 100% no Python."""
    token = request.form.get("credential", "").strip()
    if not token:
        return redirect(url_for("index"))

    with httpx.Client() as client:
        usuario_google = verificar_token_google(client, token)

    if usuario_google:
        usuario_anterior = session.get("usuario")
        id_anterior = usuario_anterior.get("id", "") if usuario_anterior else ""
        if id_anterior.startswith("visitante-"):
            viagens_visitante_memoria.pop(id_anterior, None)

        session["usuario"] = {
            "id": usuario_google["sub"],
            "nome": usuario_google["name"],
            "email": usuario_google["email"],
            "foto": usuario_google["picture"],
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


@app.route("/viagens/criar", methods=["GET", "POST"])
def criar_viagem():
    """Processa o formulário de criação com deduplicação (locks) e orquestração de APIs."""
    # TODO (Aluno 3): Implementar lock_requisicoes, orquestração com services/planejamento e Padrão PRG
    pass


@app.route("/viagens/deletar/<string:viagem_id>", methods=["POST"])
def deletar_viagem(viagem_id: str):
    """Exclui um roteiro da lista do usuário."""
    usuario = session.get("usuario")
    if not usuario:
        return redirect(url_for("index"))

    remover_viagem_usuario(usuario["id"], viagem_id)
    return redirect(url_for("index"))


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 4: Endpoint REST e Error Handlers Globais
# ==============================================================================


@app.route("/viagens/json", methods=["GET"])
@app.route("/api/viagens/json", methods=["GET"])
@app.route("/api/viagens", methods=["GET"])
def ver_viagens_json():
    """Retorna a base consolidada de static/data/viagens.json com suporte dinâmico a visitantes."""
    # TODO (Aluno 4): Retornar jsonify() da árvore consolidada de viagens
    pass


@app.errorhandler(405)
def metodo_nao_permitido(error):
    """Fallback para acessos GET em rotas POST (ex: digitar /viagens/criar na barra de endereços)."""
    # TODO (Aluno 4): Interceptar erro 405 e redirecionar suavemente para url_for('index')
    pass


@app.errorhandler(404)
def pagina_nao_encontrada(error):
    """Fallback para rotas inexistentes redirecionando suavemente para a página principal."""
    # TODO (Aluno 4): Interceptar erro 404 e redirecionar suavemente para url_for('index')
    pass


if __name__ == "__main__":
    print(f"🌍 Servidor Flask Guia do Turista rodando em http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
