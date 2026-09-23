# Maria Clara Almeida Martins

- **Matrícula:** 2025116TADS0012
- **Papel:** Aluno 1 — APIs REST, autenticação e geocodificação

## 1. Seu papel na atividade

Você ficará responsável pela primeira camada de integração externa do sistema. Sua parte valida a credencial recebida do Google e transforma nomes de cidades em coordenadas confiáveis. Todo o seu código deverá ficar na seção do **Aluno 1** em `services.py`.

Você apresentará o **Teste 1** e dividirá o **Teste 5** com Roger. No Teste 1, você demonstra o login Google e o modo visitante, mas as rotas de login, visitante e logout pertencem a Antonio.

## 2. Arquivo e funções que deverá implementar

### `services.py`

#### `verificar_token_google(client, token)`

Deve consultar o endpoint oficial `https://oauth2.googleapis.com/tokeninfo`, usando o cliente HTTPX recebido. Além de aceitar somente uma resposta válida, deve conferir se o campo `aud` do token é igual ao `GOOGLE_CLIENT_ID` configurado. Se tudo estiver correto, retorna os dados úteis do usuário, como `sub`, `name`, `email` e `picture`; se o token for inválido, estiver destinado a outro sistema ou a chamada falhar, retorna `None`.

Exemplo: um token válido para o Client ID da equipe libera a criação da sessão; um token com outro `aud` deve ser recusado.

#### `obter_sigla_uf(admin1, uf_informada="")`

Deve normalizar o estado informado pela API para a sigla oficial de duas letras, consultando `ESTADOS_BRASIL`. Por exemplo, se `admin1` for `Piauí`, o resultado deve ser `PI`. A UF digitada pelo usuário serve somente como alternativa quando o valor retornado pela API não puder ser reconhecido e essa UF for válida.

#### `buscar_coordenadas(client, cidade, uf="")`

Deve consultar a API de geocodificação do Open-Meteo com filtro do Brasil (`country_codes=BR`) e timeout de `4.0s`. A escolha do resultado deve usar o campo `admin1` para descobrir a UF verdadeira, mesmo quando o usuário selecionar uma UF errada.

Exemplo: para `Teresina / RJ`, o resultado deve identificar Teresina no Piauí e corrigir a exibição para `Teresina - PI`.

## 3. Atenção: diferença entre o enunciado e o template

O enunciado diz que `buscar_coordenadas()` retorna `(latitude, longitude, uf_oficial_detectada)` e, em falha, usa coordenadas aproximadas da capital da UF. Já o comentário atual de `services.py` diz que a função retorna `(latitude, longitude, nome_formatado)` e usa `(0.0, 0.0, "Cidade - UF")` como fallback. Essa diferença deverá ser alinhada com a equipe e o professor antes da implementação. Não altere silenciosamente o contrato, pois Antonio e Roger consumirão esse retorno.

## 4. Testes obrigatórios que deverá apresentar

### Teste 1 — Autenticação Google e modo visitante

1. Fazer login com Google.
2. Entrar também pelo modo visitante em `/auth/demo`.
3. Encerrar a sessão pelo logout.

Resultado esperado: o login Google valida o JWT em `/tokeninfo`; o visitante recebe uma sessão de teste isolada; o logout limpa a sessão. Você explica a validação, enquanto Antonio garante o funcionamento das rotas e da sessão.

### Teste 5 — Sua parte: divergência de UF

Informar `Teresina` como cidade de origem e `RJ` como UF. O resultado esperado é `Teresina - PI`, corrigido a partir de `admin1`. Roger completa o mesmo teste usando Fernando de Noronha para demonstrar o fallback do OSRM.

## 5. O que deverá saber explicar na arguição

- Por que `with httpx.Client() as client` reaproveita conexões TCP/TLS e é mais eficiente que chamadas isoladas.
- Por que timeouts defensivos evitam que o servidor Flask fique preso aguardando uma API.
- Como `country_codes=BR` limita a busca ao Brasil e como `admin1` permite corrigir a UF.
- Como a credencial JWT do Google é consultada em `/tokeninfo` e por que comparar `aud` com `GOOGLE_CLIENT_ID` impede aceitar tokens destinados a outro aplicativo.

## 6. Integração com os colegas

- **Antonio:** fornece o token recebido pela rota de callback, cria as sessões e implementa visitante/logout.
- **Roger:** usa as coordenadas produzidas por sua função para consultar clima e OSRM; vocês apresentam juntos o Teste 5.
- **Aluno 4:** persiste no JSON as cidades, UFs e coordenadas consolidadas pela orquestração.
