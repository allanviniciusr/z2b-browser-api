# Z2B Browser API

API para automação de navegador com suporte a modelos de linguagem (LLMs) para o projeto Zap2B.

## Descrição

Este projeto implementa uma API para automação de navegador web utilizando o Playwright e modelos de linguagem como GPT-4 e Claude. A API permite executar tarefas complexas através de comandos de alto nível, facilitando a criação de automações inteligentes.

## Componentes Principais

- **BrowserAgent**: Classe base para interação com o navegador
- **Z2BAgent**: Implementação customizada do agente para o Zap2B
- **AgentTracker**: Sistema de rastreamento e logging de execução de agentes
- **BrowserUseLogInterceptor**: Interceptador de logs para captura de pensamentos e ações do agente
- **TimelineBuilder**: Criador de visualizações em timeline para análise de execução

## Histórico de Desenvolvimento

O projeto passa por melhorias constantes, todas documentadas no arquivo [MELHORIAS_INTERCEPTADOR_LOGS.md](MELHORIAS_INTERCEPTADOR_LOGS.md).

## Configuração e Uso

```python
from src.agent.agent import Agent

# Criar um agente com um prompt
agent = Agent(prompt="Navegue para o site do Google e pesquise por 'Preço do bitcoin hoje'")

# Executar o agente e obter o resultado
result = await agent.execute_prompt_task()
```

## Testes

O projeto inclui testes automatizados para verificar o funcionamento correto:

```bash
python test_log_interceptor.py
python test_agent_simple.py
```

## Requisitos

- Python 3.9 ou superior
- Google Chrome instalado
- RabbitMQ (opcional, para mensageria)

## Configuração Rápida

1. Clone o repositório
2. Instale as dependências:
```
pip install -r requirements.txt
```
3. Configure o arquivo `.env` (use o exemplo fornecido)
4. Inicie a API:
```
python -m src.api.main
```

## Executando no Windows

Graças às últimas atualizações, agora o sistema funciona nativamente no Windows sem configurações especiais:

1. Simplesmente inicie a API normalmente:
   ```
   python -m src.api.main
   ```

2. O sistema iniciará automaticamente uma instância do Chrome quando necessário e gerenciará todo o ciclo de vida dela.

### Métodos Alternativos (Somente se o Automático Falhar)

Se por alguma razão o modo automático não funcionar no seu ambiente, você ainda pode usar um dos métodos abaixo:

#### Método com Script de Conveniência

Use o script de conveniência `run_windows.bat` que configura tudo manualmente:

```
run_windows.bat
```

Este script:
1. Inicia o Chrome com a porta de depuração aberta
2. Aguarda o Chrome inicializar
3. Inicia o servidor API

#### Método Manual

Se preferir fazer manualmente:

1. Primeiro, edite o arquivo `.env` e mude `CHROME_CDP=auto` para `CHROME_CDP=http://localhost:9222`

2. Inicie o Chrome com a porta de depuração aberta:
   ```
   python start_chrome.py
   ```

3. Deixe essa janela aberta e inicie o servidor em outro terminal:
   ```
   python -m src.api.main
   ```

## Como Funciona

O sistema utiliza a biblioteca browser-use para controlar o Chrome e o Hypercorn como servidor ASGI, que oferece melhor suporte para Windows do que o Uvicorn. Existem três modos de operação:

1. **Modo totalmente automático** (padrão): O sistema inicia e gerencia o Chrome automaticamente. Você não precisa fazer nada, basta iniciar a API e o Chrome será iniciado quando necessário.

2. **Modo manual com CDP**: Para casos especiais, você pode iniciar o Chrome manualmente e configurar a API para se conectar a ele.

3. **Modo Playwright** (não recomendado no Windows): Esse modo usa o Playwright para controlar o Chrome, mas pode causar erros no Windows.

A API recebe solicitações e executa as tarefas no navegador usando um modelo de linguagem (LLM) para interpretar comandos em linguagem natural e convertê-los em ações no navegador.

## Estrutura do Projeto

```
z2b-browser-api/
├── .env                    # Configurações do ambiente
├── requirements.txt        # Dependências
├── src/
│   ├── api/                # Código da API
│   │   ├── main.py         # Ponto de entrada
│   │   ├── models/         # Modelos de dados
│   │   ├── routes/         # Rotas da API
│   │   ├── services/       # Serviços
│   │   ├── static/         # Arquivos estáticos
│   │   └── websocket/      # Código WebSocket
│   └── agent/              # Agente de automação
│       ├── agent.py        # Implementação do agente
└── chrome_data/            # Diretório para dados do Chrome (criado automaticamente)
```

## Troubleshooting

### Problemas Comuns

1. **Erro ao iniciar o Chrome**
   - Verifique se o Chrome está instalado e acessível
   - Se o sistema não conseguir detectar o caminho do Chrome, você pode especificá-lo manualmente no arquivo `.env` usando a variável `CHROME_PATH`
   - Certifique-se de que não há bloqueios de firewall ou antivírus impedindo a execução

2. **Erro `NotImplementedError` no Windows**
   - Este erro deve ser coisa do passado com a nova implementação automática
   - Se ainda ocorrer, configure explicitamente `CHROME_CDP=http://localhost:9222` no arquivo `.env` e use o método manual descrito acima
   - A nova implementação usa `subprocess.Popen()` em vez de `asyncio.create_subprocess_exec()` para contornar esse problema

3. **Chrome é iniciado mas a conexão falha**
   - Verifique se a porta 9222 está disponível e não bloqueada por firewall
   - Tente mudar a porta de depuração no arquivo `.env` para outro valor (ex: 9223)
   - Certifique-se de que o Chrome está sendo iniciado com as flags corretas

4. **Erro no Playwright**
   - Execute `playwright install` para garantir que os navegadores necessários estejam instalados

## API Endpoints

- `POST /tasks` - Criar uma nova tarefa
- `GET /tasks/{task_id}` - Obter status de uma tarefa
- `GET /tasks/queue` - Obter status da fila
- `GET /tasks/status` - Obter status de todas as tarefas

## Modelos de Linguagem Suportados

O sistema suporta múltiplos modelos de LLM através da interface unificada de LangChain:

### Configurando LLMs

#### Configuração Global via `.env`

Para configurar o LLM padrão, defina as seguintes variáveis de ambiente no arquivo `.env`:

```
# OpenAI / OpenRouter (padrão)
LLM_PROVIDER=openrouter  # ou openai
LLM_API_KEY=sua-chave-api
LLM_MODEL_NAME=gpt-3.5-turbo  # ou outro modelo
LLM_TEMPERATURE=0.7
LLM_ENDPOINT=https://openrouter.ai/api/v1  # opcional para OpenRouter

# Google Gemini
# LLM_PROVIDER=gemini
# GOOGLE_API_KEY=sua-chave-api
# LLM_MODEL_NAME=gemini-pro

# Anthropic Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sua-chave-api
# LLM_MODEL_NAME=claude-3-sonnet-20240229

# Mistral AI
# LLM_PROVIDER=mistral
# MISTRAL_API_KEY=sua-chave-api
# LLM_MODEL_NAME=mistral-medium

# Ollama (modelos locais)
# LLM_PROVIDER=ollama
# LLM_MODEL_NAME=llama2
# OLLAMA_BASE_URL=http://localhost:11434
```

#### Configuração via API

Você pode configurar o LLM globalmente para todas as tarefas através da API:

```bash
# Atualizar configurações do LLM
curl -X POST "http://localhost:8000/llm/settings" \
  -H "Content-Type: application/json" \
  -d '{"api_url": "https://api.openai.com/v1", "api_key": "sua-chave-api"}'

# Obter configurações atuais
curl -X GET "http://localhost:8000/llm/settings"

# Testar configurações do LLM
curl -X POST "http://localhost:8000/llm/test"
```

#### Configuração por Tarefa

Você também pode definir o LLM específico para cada tarefa, incluindo o campo `llm_options` no corpo da requisição:

```json
POST /tasks
{
  "client_id": "user123",
  "task_type": "prompt",
  "data": {
    "prompt": "Acesse o site google.com e faça uma pesquisa por 'fastapi'"
  },
  "llm_options": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.5,
    "max_tokens": 4000
  }
}
```

Quando `llm_options` é fornecido, essas configurações têm prioridade sobre as configurações globais apenas para essa tarefa específica.

### Instalando Dependências para LLMs Específicos

As dependências para os diferentes provedores de LLM estão comentadas no arquivo `requirements.txt`. Descomente e instale conforme necessário:

```bash
# Para usar OpenAI/OpenRouter
pip install langchain-openai

# Para usar Google Gemini
pip install langchain-google-genai

# Para usar Anthropic Claude
pip install langchain-anthropic

# Para usar Mistral AI
pip install langchain-mistralai

# Para usar Ollama (modelos locais)
pip install langchain-community
```

## Tecnologias Utilizadas

- **FastAPI**: Framework web para construção de APIs
- **browser-use**: Biblioteca para controle de navegador
- **RabbitMQ**: Sistema de mensageria para processamento assíncrono
- **Pydantic**: Validação de dados e serialização/deserialização
- **Docker**: Containerização para ambiente de produção

## Licença

Este projeto está licenciado sob a licença MIT. 