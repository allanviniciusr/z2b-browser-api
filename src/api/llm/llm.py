from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import logging
from langchain_core.language_models.chat_models import BaseChatModel

# Tentar importar os modelos específicos
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from langchain_mistralai import ChatMistralAI
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False

# Configurar logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Carregar variáveis de ambiente
load_dotenv()

class LLMProvider(str, Enum):
    """Provedores de LLM suportados"""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    OLLAMA = "ollama"

class LLMConfig(BaseModel):
    """Configuração para o provedor de LLM"""
    provider: LLMProvider
    model: str
    api_key: str
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

def get_llm_config() -> Dict[str, Any]:
    """
    Obtém a configuração do LLM das variáveis de ambiente
    
    Returns:
        Dict[str, Any]: Configuração do LLM
    """
    return {
        "provider": os.getenv("LLM_PROVIDER", os.getenv("OPENAI_PROVIDER", "openai")).lower(),
        "api_key": os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        "model_name": os.getenv("LLM_MODEL_NAME", os.getenv("OPENAI_MODEL_NAME", "")),
        "temperature": float(os.getenv("LLM_TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.7"))),
        "api_base": os.getenv("LLM_ENDPOINT", os.getenv("OPENAI_ENDPOINT", None)),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
        "mistral_api_key": os.getenv("MISTRAL_API_KEY", ""),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "google_api_key": os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    }

def get_llm(config: Optional[Dict[str, Any]] = None) -> BaseChatModel:
    """
    Cria e retorna uma instância de LLM baseada nas configurações
    
    Args:
        config (Optional[Dict[str, Any]]): Configuração opcional para sobrescrever variáveis de ambiente
        
    Returns:
        BaseChatModel: Uma instância do modelo de linguagem configurado
    """
    # Obter configurações
    cfg = get_llm_config()
    
    # Sobrescrever com configurações fornecidas
    if config:
        cfg.update(config)
    
    provider = cfg["provider"]
    
    # Validar configurações essenciais
    if provider != "ollama" and not cfg.get(f"{provider}_api_key") and not cfg.get("api_key"):
        raise ValueError(f"API key não fornecida para o provedor {provider}")
    
    if not cfg.get("model_name"):
        raise ValueError("Nome do modelo não fornecido nas variáveis de ambiente")
    
    # Log das configurações
    logger.info(f"Inicializando LLM com provider: {provider}")
    logger.debug(f"Modelo: {cfg['model_name']}, temperatura: {cfg['temperature']}")
    
    # Criar e retornar o modelo apropriado baseado no provedor
    if provider == "gemini" and GEMINI_AVAILABLE:
        logger.info("Usando ChatGoogleGenerativeAI")
        return ChatGoogleGenerativeAI(
            model=cfg["model_name"],
            google_api_key=cfg.get("google_api_key", cfg.get("api_key")),
            temperature=cfg["temperature"],
            convert_system_message_to_human=True,
            max_output_tokens=cfg.get("max_tokens")
        )
    
    elif provider == "anthropic" and ANTHROPIC_AVAILABLE:
        logger.info("Usando ChatAnthropic")
        return ChatAnthropic(
            model=cfg["model_name"],
            anthropic_api_key=cfg.get("anthropic_api_key", cfg.get("api_key")),
            temperature=cfg["temperature"],
            max_tokens=cfg.get("max_tokens")
        )
    
    elif provider == "mistral" and MISTRAL_AVAILABLE:
        logger.info("Usando ChatMistralAI")
        return ChatMistralAI(
            model=cfg["model_name"],
            mistral_api_key=cfg.get("mistral_api_key", cfg.get("api_key")),
            temperature=cfg["temperature"],
            max_tokens=cfg.get("max_tokens")
        )
    
    elif provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
            logger.info("Usando ChatOllama")
            return ChatOllama(
                model=cfg["model_name"],
                base_url=cfg.get("ollama_base_url"),
                temperature=cfg["temperature"]
            )
        except ImportError:
            raise ImportError("Langchain Ollama não está instalado. Instale com 'pip install langchain-community'")
    
    elif provider in ["openai", "openrouter"] and OPENAI_AVAILABLE:
        logger.info(f"Usando ChatOpenAI com {provider}")
        
        # Configuração específica para OpenRouter
        if provider == "openrouter":
            if not cfg.get("api_base"):
                cfg["api_base"] = "https://openrouter.ai/api/v1"
                logger.warning("API base para OpenRouter não fornecida, usando padrão")
            
            # OpenRouter exige cabeçalhos HTTP específicos
            headers = {
                "HTTP-Referer": "https://z2b-browser-api",
                "X-Title": "Z2B Browser API"
            }
        else:
            headers = None
        
        return ChatOpenAI(
            model=cfg["model_name"],
            openai_api_key=cfg["api_key"],
            temperature=cfg["temperature"],
            openai_api_base=cfg.get("api_base"),
            max_tokens=cfg.get("max_tokens"),
            headers=headers
        )
    
    else:
        raise ValueError(f"Provedor {provider} não suportado ou biblioteca não disponível")

def list_available_providers() -> Dict[str, bool]:
    """
    Lista os provedores disponíveis na instalação atual
    
    Returns:
        Dict[str, bool]: Dicionário com disponibilidade de cada provedor
    """
    return {
        "openai": OPENAI_AVAILABLE,
        "openrouter": OPENAI_AVAILABLE,
        "gemini": GEMINI_AVAILABLE,
        "anthropic": ANTHROPIC_AVAILABLE,
        "mistral": MISTRAL_AVAILABLE,
        "ollama": True  # Disponível via langchain-community
    }