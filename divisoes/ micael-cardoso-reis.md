# Aluno 4 — Micael Cardoso Reis

- **Nome:** Micael Cardoso Reis
- **Matrícula:** 2025116TADS0041
- **Papel:** Aluno 4 — persistência JSON, sanitização e resiliência

## 1. Seu papel na atividade

Você cuidará do armazenamento dos roteiros e das respostas defensivas globais em `app.py`. Sua parte deve manter o JSON íntegro mesmo com acessos concorrentes, separar dados persistentes de usuários Google dos dados temporários de visitantes, expor a API JSON e tratar 404/405.

Você apresentará o **Teste 6**. Os handlers que você implementará também fazem parte do **Teste 3**, apresentado por Antonio.

## 2. Arquivo e funções que deverá implementar

### `app.py`

#### `sanitizar_entrada(texto, max_len=80)`

Deve remover tags HTML com a regex indicada (`r'<[^>]*>'`), caracteres de controle e espaços excedentes, além de respeitar o tamanho máximo. Exemplo: `"  <b>Recife</b>  "` deve resultar em `"Recife"`.

#### `criar_estrutura_padrao_viagens()`

Esta função já está preenchida no template e fornece a raiz com versão, descrição, totais, provedores e usuários. Você deverá usá-la como estrutura segura quando ainda não existir base válida; não há TODO nela para remover.

#### `carregar_dados_viagens_json()`

Deve ler `static/data/viagens.json` dentro de `lock_arquivo_json`, usando `json.load`. Em arquivo ausente, vazio ou inválido, deverá devolver uma estrutura padrão coerente, evitando erro 500.

#### `salvar_dados_viagens_json(dados_completos)`

Deve atualizar os metadados/totais necessários e gravar o dicionário com `json.dump`, indentação de 2 espaços e proteção de `lock_arquivo_json`.

#### `obter_viagens_usuario(user_id)`

Deve devolver a lista do armazenamento em memória quando o ID representar visitante; para usuário autenticado pelo Google, deve navegar defensivamente pelo JSON com `.get()` e valores padrão.

#### `adicionar_viagem_usuario(user_id, item, perfil_usuario=None)`

Deve acrescentar o roteiro em memória para visitante. Para usuário Google, deve criar ou atualizar seu nó no JSON, incluindo perfil, metadados e lista `roteiros`, mantendo os totais consistentes.

#### `remover_viagem_usuario(user_id, viagem_id)`

Deve localizar e excluir somente o roteiro com o ID solicitado, tanto na memória de visitante quanto no nó correto do JSON, e atualizar os metadados da base persistente.

#### `ver_viagens_json()` — `GET /viagens/json`

Deve retornar `jsonify()` com a árvore consolidada e `Content-Type: application/json`. Para visitante, o suporte deve ser dinâmico, sem transformar a sessão temporária em persistência permanente. O template também oferece os aliases `/api/viagens/json` e `/api/viagens`, embora o teste obrigatório use `/viagens/json`.

#### `metodo_nao_permitido(error)` e `pagina_nao_encontrada(error)`

Os handlers globais de 405 e 404 devem redirecionar para `url_for("index")`, substituindo as telas padrão de erro por um retorno suave à home.

## 3. Estrutura obrigatória do JSON

O payload deve manter, na raiz, `versao_schema`, `atualizado_em`, `total_usuarios`, `total_roteiros`, `provedores` e `usuarios`. Cada usuário deve ter `perfil`, `metadados` e `roteiros`. Cada roteiro reúne identificação e data, origem/destino, geolocalização, telemetria de clima e percurso, dicas do destino e metadados com o status dos serviços.

Use `.get()` encadeado ao ler partes aninhadas para que uma chave ausente não cause `KeyError`.

## 4. Atenção: diferença entre o enunciado e o template

O enunciado exige que `GET /viagens/criar` resulte em 405, mas o decorator atual dessa rota aceita `GET` e `POST`. Antonio é responsável por corrigir os métodos da rota; seu handler 405 só será chamado se o método realmente não estiver permitido.

O enunciado mostra explicitamente três rotinas principais desta área (`sanitizar_entrada`, leitura e escrita do JSON), mas o template divide a persistência também em `obter_viagens_usuario`, `adicionar_viagem_usuario` e `remover_viagem_usuario`. Pela distribuição da equipe e pelos TODOs do próprio template, essas três funções auxiliares também são sua responsabilidade.

## 5. Teste obrigatório que deverá apresentar

### Teste 6 — endpoint JSON e integridade

Clicar em **📄 Ver JSON (API)** ou abrir `/viagens/json`. O resultado esperado é um documento `application/json` válido, com a árvore hierárquica, metadados e status de cada serviço. Confirme que totais, usuário e roteiro exibidos correspondem ao que foi criado na interface.

Sua implementação de 404/405 também será validada no Teste 3 por Antonio: rota inexistente e método incorreto devem redirecionar para `/`.

## 6. O que deverá saber explicar na arguição

- A anatomia da raiz do JSON e dos nós por usuário.
- Como `threading.Lock()` evita leituras/escritas simultâneas que poderiam corromper o arquivo.
- A diferença entre `json.load`/`json.dump` (arquivo) e `json.loads`/`json.dumps` (texto em memória).
- Como `.get()` com valores padrão evita `KeyError` em estruturas aninhadas.
- Como funcionam `@app.errorhandler(404)`, `@app.errorhandler(405)` e `GET /viagens/json`.

## 7. Integração com os colegas

- **Antonio:** chama sua sanitização e suas funções de adicionar/remover/consultar; apresenta o Teste 3 que depende de seus handlers. Como ambos editam `app.py`, combinem as seções antes de integrar.
- **Maria:** fornece identidade validada e os dados corretos de geocodificação que entrarão no payload.
- **Roger:** fornece clima, percurso, texto do guia e diagnóstico da IA que serão persistidos.
