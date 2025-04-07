import os
import asyncio
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar event loop para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def test_openrouter():
    # Obter configurações
    api_key = os.getenv("LLM_API_KEY") 
    api_base = os.getenv("LLM_ENDPOINT")
    model = os.getenv("LLM_MODEL_NAME")
    
    print(f"Testando conexão com: {api_base}")
    print(f"Modelo: {model}")
    print(f"API Key: {api_key[:4]}...{api_key[-4:]}")
    
    # Configurar cliente
    import openai
    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    
    # Testar formato browser-use
    prompt = """
    Você é um agente de automação web. Descreva como você navegaria para o Google e pesquisaria por "preço do bitcoin hoje".
    Use apenas comandos compatíveis com automação de navegador.
    """
    
    # Testar com modelo GPT
    response = client.chat.completions.create(
        model="openai/gpt-4o",  # Testar com modelo OpenAI
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    print("\nResposta do modelo OpenAI:")
    print(response.choices[0].message.content)
    
    # Testar com modelo atual
    response2 = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    print(f"\nResposta do modelo {model}:")
    print(response2.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(test_openrouter()) 