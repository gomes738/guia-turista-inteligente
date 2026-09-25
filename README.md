# 🇧🇷 Guia do Turista Inteligente (Flask + HTTPX + Google Auth + Gemini AI)

Aplicação web desenvolvida com **Flask** e Python para integrar APIs externas, autenticação com Google, informações meteorológicas, rotas rodoviárias e geração de guias turísticos com inteligência artificial.

---

## 👥 Equipe e divisão da atividade

A divisão segue os quatro papéis definidos pelo professor. O quarto integrante será identificado quando entrar na equipe. As funções ainda estão **a implementar**.

| Papel | Integrante | Matrícula | Responsabilidades |
| --- | --- | --- | --- |
| Aluno 1 — APIs REST e autenticação | Maria Clara Almeida Martins | 2025116TADS0012 | Em `services.py`: validação do token Google OAuth e geocodificação Open-Meteo com identificação da UF. |
| Aluno 2 — Telemetria e IA | Roger Pierre Reis Silva | 2025116TADS0010 | Em `services.py`: clima Open-Meteo e rotas OSRM. Em `planejamento.py`: guia Gemini e contingência. |
| Aluno 3 — Backend e sessões | Antonio Carlos Gomes | 2025116TADS0024 | Em `app.py`: rotas Flask, sessões, criação e exclusão de viagens, padrão PRG e controle de requisições duplicadas. |
| Aluno 4 — JSON e resiliência | Micael Cardoso Reis| 2025116TADS0041 | Em `app.py`: persistência JSON com lock, sanitização, endpoint de viagens em JSON e tratamento dos erros 404/405. |

---

## 🚀 Como executar o projeto localmente

### 1. Clonar o fork

```bash
git clone https://github.com/gomes738/guia-turista-inteligente.git
cd guia-turista-inteligente
```

### 2. Criar e ativar o ambiente virtual

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar as dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente

**Linux/macOS:**

```bash
export GEMINI_API_KEY="SUA_CHAVE_GEMINI_AQUI"
export GOOGLE_CLIENT_ID="776335673676-dk7od4ljhh43bio4bppf94i8ou0u9v9i.apps.googleusercontent.com"
export PORT="8001"
```

**Windows (PowerShell):**

```powershell
$env:GEMINI_API_KEY="SUA_CHAVE_GEMINI_AQUI"
$env:GOOGLE_CLIENT_ID="776335673676-dk7od4ljhh43bio4bppf94i8ou0u9v9i.apps.googleusercontent.com"
$env:PORT="8001"
```

A chave Gemini pode ser obtida no [Google AI Studio](https://aistudio.google.com/).

### 5. Iniciar o servidor

```bash
python app.py
```

Acesse `http://localhost:8001` no navegador.

---

## 📂 Estrutura do projeto

```text
├── app.py                 # Rotas Flask, sessões e persistência — a implementar
├── config.py              # Configurações, chaves e catálogo das UFs
├── services.py            # Integrações com APIs externas — a implementar
├── planejamento.py        # Guia turístico com Gemini — a implementar
├── templates/
│   └── index.html         # Interface Jinja2
├── static/
│   ├── css/style.css      # Estilos
│   ├── js/app.js          # Interações da interface
│   └── data/
│       ├── estados_brasil.json
│       └── viagens.json
├── requirements.txt
└── README.md
```

---

## 🧪 Qualidade de código

```bash
ruff check .
mypy app.py services.py planejamento.py config.py
```
