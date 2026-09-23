# Roger Pierre Reis Silva

- **Matrícula:** 2025116TADS0010
- **Papel:** Aluno 2 — telemetria, rotas e inteligência artificial

## 1. Seu papel na atividade

Você implementará a consulta de clima e o cálculo do percurso rodoviário em `services.py`. Também será responsável por toda a integração com o Gemini, pela limpeza da resposta e pelo guia de contingência em `planejamento.py`.

Você apresentará o **Teste 2** e dividirá o **Teste 5** com Maria.

## 2. Arquivos e funções que deverá implementar

### `services.py`

#### `obter_clima(client, lat, lon)`

Deve consultar o Open-Meteo Forecast e retornar um dicionário com temperatura em °C, umidade em % e vento em km/h. Se as coordenadas forem inválidas, como `(0.0, 0.0)`, ou a API exceder o timeout de `4.0s`, deve retornar valores `N/D`, sem derrubar a aplicação.

Exemplo de formato esperado: `{"temperatura": "28.5 °C", "umidade": "35%", "vento": "12.0 km/h"}`.

#### `obter_percurso(client, lat_o, lon_o, lat_d, lon_d)`

Deve consultar o OSRM com as coordenadas de origem e destino. Converta a distância de metros para quilômetros com arredondamento de uma casa (`round(m/1000, 1)`) e a duração em segundos para horas e minutos. Se não existir percurso rodoviário ou ocorrer timeout de `6.0s`, deve retornar as mensagens `Sem rota direta` e `Considere voos ou barcos`.

Exemplo: um destino em uma ilha pode ter coordenadas válidas, mas nenhuma rota de carro; isso é um fallback esperado, não um erro 500.

### `planejamento.py`

#### `limpar_formato_texto(texto)`

Deve usar expressões regulares para retirar marcações residuais de Markdown, como asteriscos, hashtags e crases, além de saudações indesejadas. Os emojis e o texto útil do roteiro devem ser preservados.

#### `obter_guia_destino_com_diagnostico(destino)`

Deve preparar um prompt que peça um guia turístico e culinário em texto puro, com emojis e sem Markdown, e chamar o modelo `gemini-3.6-flash`. A chamada deve ficar isolada em `ThreadPoolExecutor` com limite de `6.0s`. Em timeout, chave inválida ou falta de cota, a função deve gerar um roteiro estruturado de contingência e devolver também os metadados de diagnóstico, inclusive o status e se o fallback foi utilizado.

#### `obter_guia_destino(destino)`

Este wrapper já está implementado: chama a função anterior e devolve apenas o texto. Você deverá garantir que a função principal entregue a tupla esperada para que o wrapper continue funcionando.

## 3. Testes obrigatórios que deverá apresentar

### Teste 2 — Fallback da IA Gemini

Definir `GEMINI_API_KEY="CHAVE_INVALIDA"` no ambiente e gerar uma viagem. O sistema não deve responder com erro 500. Deve aparecer um card com o roteiro de contingência, em texto puro e com emojis.

### Teste 5 — Sua parte: destino sem estrada

Usar `Fernando de Noronha / PE` como destino. O OSRM deve mostrar `Sem rota direta` e `Considere voos ou barcos`. Maria faz antes a parte da UF divergente usando `Teresina / RJ`.

## 4. O que deverá saber explicar na arguição

- As anotações modernas de tipo, como `tuple[float, float, str]` e `dict[str, Any] | None`, e o uso de `ruff check .` e `mypy .`.
- Como Open-Meteo e OSRM são consultados e como metros/segundos viram km e horas/minutos.
- Como o prompt exige texto puro com emojis, sem asteriscos ou Markdown.
- Como `limpar_formato_texto()` usa regex.
- Como o timeout no `ThreadPoolExecutor` limita o tempo de espera pela resposta, por que a implementação deve garantir que uma tarefa ainda em execução não bloqueie o retorno e quando o fallback é acionado.

## 5. Integração com os colegas

- **Maria:** entrega as coordenadas e a UF real usadas por clima e OSRM; vocês apresentam juntos o Teste 5. Como ambos editam `services.py`, combinem seções e revisem conflitos antes de integrar.
- **Antonio:** orquestra suas funções ao criar uma viagem e aplica o padrão PRG.
- **Aluno 4:** grava no payload os dados de clima, percurso, guia e diagnóstico dos serviços.
