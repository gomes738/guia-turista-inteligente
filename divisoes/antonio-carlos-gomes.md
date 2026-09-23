# Antonio Carlos Gomes

- **Matrícula:** 2025116TADS0024
- **Papel:** Aluno 3 — backend, sessões e idempotência

## 1. Seu papel na atividade

Você será responsável pelo gateway Flask em `app.py`: recebe as ações do navegador, controla a sessão, chama as funções dos colegas, cria ou exclui viagens e redireciona o usuário. Também implementará a proteção do backend contra requisições duplicadas.

Você apresentará os **Testes 3 e 4**. No Teste 3, os handlers 404/405 são código do Aluno 4, embora a apresentação do comportamento completo seja sua.

## 2. Arquivo e funções que deverá implementar

### `app.py`

#### `index()` — `GET /`

Deve ler `session["usuario"]`, buscar as viagens do usuário quando houver sessão e renderizar `index.html` com usuário, viagens, UFs e `GOOGLE_CLIENT_ID`.

#### `google_callback()` — callback do Google

Deve receber a credencial JWT enviada pelo formulário, criar um `httpx.Client`, chamar `verificar_token_google()` e, se o token for válido, guardar em `session["usuario"]` o perfil necessário. Depois, redireciona para a página inicial.

#### `login_demo()` — `/auth/demo`

Deve criar uma sessão temporária para `Viajante Convidado`, com identificador próprio e armazenamento isolado em `viagens_visitante_memoria`, e redirecionar para `/`.

#### `logout()` — `/auth/logout`

Deve identificar se a sessão é de visitante, descartar suas viagens temporárias e limpar a sessão. Em seguida, redireciona para `/`.

#### `criar_viagem()` — `/viagens/criar`

Deve exigir usuário em sessão, sanitizar os dados do formulário por meio da função do Aluno 4 e impedir processamento duplicado com `lock_requisicoes`, `requisicoes_ativas` e `requisicoes_recentes`. Em uma requisição válida, deverá:

1. geocodificar origem e destino com as funções de Maria;
2. obter clima e percurso com as funções de Roger;
3. gerar o guia e diagnóstico da IA com Roger;
4. montar o roteiro no formato esperado pelo payload;
5. chamar `adicionar_viagem_usuario()` do Aluno 4;
6. aplicar Post/Redirect/Get, respondendo com redirecionamento HTTP 302 para a home.

O PRG evita que atualizar a página com `F5` reenvie o formulário POST.

#### `deletar_viagem(viagem_id)` — `/viagens/deletar/<id>`

Deve validar a sessão, chamar `remover_viagem_usuario()` e redirecionar para a home.

## 3. Atenção: diferença entre o enunciado e o template

O enunciado define `POST /auth/google/callback`, `GET /auth/demo`, `GET /auth/logout`, `POST /viagens/criar` e `POST /viagens/deletar/<id>`. No template atual, todas essas rotas estão declaradas com `methods=["GET", "POST"]`.

Isso afeta diretamente o Teste 3: para `GET /viagens/criar` produzir 405 e ser interceptado pelo handler, essa rota não pode aceitar GET. A equipe deverá alinhar a implementação aos métodos exigidos no enunciado. A mesma revisão deve ser feita nas demais rotas, sem confundir o método correto de cada uma.

## 4. Testes obrigatórios que deverá apresentar

### Teste 3 — 404 e 405

1. Abrir uma rota inexistente para provocar 404.
2. Digitar `http://localhost:8001/viagens/criar` na barra do navegador, o que envia GET a uma rota que deve aceitar somente POST.

Resultado esperado: em ambos os casos, o usuário é redirecionado suavemente para `/`, sem ver a página padrão de erro. Você apresenta o teste; o Aluno 4 implementa os handlers globais.

### Teste 4 — cliques duplos

Submeter o formulário e disparar cliques rápidos sucessivos. O frontend já desabilita o botão e mostra o estado de carregamento; seu backend deve descartar repetições usando `lock_requisicoes` e o controle de requisições recentes. O resultado deve ser apenas um roteiro criado.

## 5. O que deverá saber explicar na arguição

- A diferença entre `GET /`, que apenas consulta e é idempotente, e `POST /viagens/criar`, que altera estado e não é naturalmente idempotente.
- Como o padrão PRG usa HTTP 302 para impedir reenvio por `F5`.
- Como o bloqueio do frontend e o lock/registro temporal do backend se complementam contra cliques duplos.
- Como `session["usuario"]` mantém o usuário entre requisições por cookie assinado pelo Flask e como o modo visitante usa memória temporária.

## 6. Integração com os colegas

- **Maria:** valida o token e entrega coordenadas/UF real; você implementa as rotas de login, visitante e logout que ela demonstra no Teste 1.
- **Roger:** fornece clima, percurso, guia e diagnóstico chamados durante a criação.
- **Aluno 4:** fornece sanitização, persistência, consulta/remoção de viagens e handlers 404/405. Como ambos editam `app.py`, combinem seções e integração para evitar conflitos.
