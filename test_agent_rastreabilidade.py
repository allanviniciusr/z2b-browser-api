#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import json
import base64
import time
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Configurar logging básico
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agent_rastreador")

# Carregar variáveis de ambiente
load_dotenv()

# Importar a classe Agent do arquivo certo
from src.agent.agent import Agent

class AgentRastreador:
    """
    Classe para rastrear a execução detalhada do agente
    """
    def __init__(self, prompt_original: str):
        # Salvar o prompt original do usuário
        self.prompt_original = prompt_original
        
        # Criar diretório para logs e screenshots
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = os.path.join("agent_logs", f"execucao_{self.timestamp}")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Arquivo de log principal
        self.log_file = os.path.join(self.log_dir, "execucao_log.json")
        
        # Inicializar estrutura de dados do log
        self.log_data = {
            "prompt_original": prompt_original,
            "prompt_efetivo": None,  # Será preenchido depois
            "plano_acoes": None,     # Será preenchido se disponível
            "etapas": [],            # Lista de etapas executadas
            "timestamp_inicio": datetime.now().isoformat(),
            "timestamp_fim": None,
            "duracao_segundos": None,
            "status": "iniciado"
        }
        
        # Salvar log inicial
        self._salvar_log()
        
        # Contador de etapas
        self.contador_etapas = 0
        
        logger.info(f"Rastreador inicializado. Logs serão salvos em: {self.log_dir}")
    
    async def _callback_rastreador(self, event_data: Dict[str, Any]):
        """
        Callback que processa eventos do agente e registra no log
        """
        # Extrair tipo de evento
        event_type = event_data.get("event_type", "desconhecido")
        logger.info(f"Evento recebido: {event_type}")
        
        # Processar evento conforme seu tipo
        if event_type == "agent.plan":
            # Plano de ação do agente
            plano = event_data.get("plan", [])
            self.log_data["plano_acoes"] = plano
            
            # Salvar plano separadamente para fácil acesso
            plano_file = os.path.join(self.log_dir, "plano_acoes.json")
            with open(plano_file, "w", encoding="utf-8") as f:
                json.dump(plano, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Plano com {len(plano)} ações registrado")
            
        elif event_type == "agent.step":
            # Etapa do agente sendo executada
            self.contador_etapas += 1
            
            # Criar diretório para esta etapa
            etapa_dir = os.path.join(self.log_dir, f"etapa_{self.contador_etapas}")
            os.makedirs(etapa_dir, exist_ok=True)
            
            # Extrair informações da etapa
            etapa_info = {
                "numero": self.contador_etapas,
                "timestamp": datetime.now().isoformat(),
                "action": event_data.get("action"),
                "prompt_llm": event_data.get("prompt"),
                "browser_state": {},
                "resposta_llm": event_data.get("response"),
                "screenshot_path": None,
                "error": event_data.get("error")
            }
            
            # Salvar informações detalhadas da etapa
            etapa_file = os.path.join(etapa_dir, "etapa_info.json")
            with open(etapa_file, "w", encoding="utf-8") as f:
                # Criar cópia para salvar, removendo dados binários grandes
                etapa_info_save = dict(etapa_info)
                if "browser_state" in etapa_info_save and "screenshot" in etapa_info_save["browser_state"]:
                    etapa_info_save["browser_state"]["screenshot"] = "[DADOS BINÁRIOS]"
                    
                json.dump(etapa_info_save, f, indent=2, ensure_ascii=False)
            
            # Adicionar à lista de etapas no log principal
            self.log_data["etapas"].append(etapa_info)
            self._salvar_log()
            
            logger.info(f"Etapa {self.contador_etapas} registrada em {etapa_dir}")
            
        elif event_type == "llm.prompt":
            # Prompt enviado ao LLM
            prompt_info = {
                "timestamp": datetime.now().isoformat(),
                "prompt": event_data.get("prompt"),
                "model": event_data.get("model")
            }
            
            # Salvar prompt em arquivo separado
            prompt_file = os.path.join(self.log_dir, f"prompt_llm_{int(time.time())}.txt")
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(str(prompt_info.get("prompt", "")))
            
            logger.info(f"Prompt para LLM registrado em {prompt_file}")
            
        elif event_type == "llm.response":
            # Resposta recebida do LLM
            response_info = {
                "timestamp": datetime.now().isoformat(),
                "response": event_data.get("response"),
                "model": event_data.get("model")
            }
            
            # Salvar resposta em arquivo separado
            response_file = os.path.join(self.log_dir, f"resposta_llm_{int(time.time())}.txt")
            with open(response_file, "w", encoding="utf-8") as f:
                f.write(str(response_info.get("response", "")))
            
            logger.info(f"Resposta do LLM registrada em {response_file}")
            
        elif event_type == "task.screenshot" or "screenshot" in event_data:
            # Screenshot capturado
            if "screenshot" in event_data:
                screenshot_data = event_data["screenshot"]
                etapa_atual = f"etapa_{self.contador_etapas}"
                
                # Verificar se o diretório da etapa existe
                etapa_dir = os.path.join(self.log_dir, etapa_atual)
                os.makedirs(etapa_dir, exist_ok=True)
                
                # Salvar screenshot
                screenshot_path = os.path.join(
                    etapa_dir, 
                    f"screenshot_{int(time.time())}.png"
                )
                
                try:
                    with open(screenshot_path, "wb") as f:
                        f.write(base64.b64decode(screenshot_data))
                    
                    # Atualizar o caminho do screenshot na etapa atual
                    if self.log_data["etapas"] and len(self.log_data["etapas"]) >= self.contador_etapas:
                        self.log_data["etapas"][self.contador_etapas-1]["screenshot_path"] = screenshot_path
                        self._salvar_log()
                    
                    logger.info(f"Screenshot salvo em: {screenshot_path}")
                except Exception as e:
                    logger.error(f"Erro ao salvar screenshot: {str(e)}")
            
        elif event_type == "task.result":
            # Resultado final da tarefa
            self.log_data["status"] = "concluído"
            self.log_data["resultado"] = event_data.get("result")
            self.log_data["timestamp_fim"] = datetime.now().isoformat()
            
            # Calcular duração
            inicio = datetime.fromisoformat(self.log_data["timestamp_inicio"])
            fim = datetime.fromisoformat(self.log_data["timestamp_fim"])
            self.log_data["duracao_segundos"] = (fim - inicio).total_seconds()
            
            # Salvar resultado em arquivo separado
            result_file = os.path.join(self.log_dir, "resultado_final.json")
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(event_data.get("result", {}), f, indent=2, ensure_ascii=False)
            
            # Atualizar log principal
            self._salvar_log()
            
            logger.info(f"Tarefa concluída. Duração: {self.log_data['duracao_segundos']:.2f} segundos")
            
        elif event_type == "task.error":
            # Erro na execução da tarefa
            self.log_data["status"] = "erro"
            self.log_data["erro"] = event_data.get("error")
            self.log_data["timestamp_fim"] = datetime.now().isoformat()
            
            # Calcular duração
            inicio = datetime.fromisoformat(self.log_data["timestamp_inicio"])
            fim = datetime.fromisoformat(self.log_data["timestamp_fim"])
            self.log_data["duracao_segundos"] = (fim - inicio).total_seconds()
            
            # Salvar informações de erro
            error_file = os.path.join(self.log_dir, "erro.txt")
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(str(event_data.get("error", "")))
            
            # Atualizar log principal
            self._salvar_log()
            
            logger.error(f"Erro na tarefa: {self.log_data['erro']}")
        
        # Se o evento tiver prompt efetivo
        if "prompt_efetivo" in event_data:
            self.log_data["prompt_efetivo"] = event_data["prompt_efetivo"]
            self._salvar_log()
    
    def _salvar_log(self):
        """Salva o log atual no arquivo JSON"""
        try:
            # Criar cópia para salvar, removendo dados binários grandes
            log_data_save = dict(self.log_data)
            
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(log_data_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar log: {str(e)}")
    
    async def executar_agente(self, prompt: Optional[str] = None):
        """
        Executa o agente com rastreamento detalhado
        """
        # Usar o prompt original ou o novo fornecido
        prompt_execucao = prompt or self.prompt_original
        
        # Registrar o prompt efetivo
        self.log_data["prompt_efetivo"] = prompt_execucao
        self._salvar_log()
        
        logger.info(f"Executando agente com prompt: '{prompt_execucao}'")
        
        # Criar agente
        agent = Agent(prompt=prompt_execucao)
        
        try:
            # Executar o agente com nosso callback de rastreamento
            result = await agent.execute_prompt_task(
                prompt=prompt_execucao,
                callback=self._callback_rastreador
            )
            
            # Registrar conclusão bem-sucedida (caso o evento task.result não tenha sido capturado)
            if self.log_data["status"] == "iniciado":
                self.log_data["status"] = "concluído"
                self.log_data["resultado"] = result
                self.log_data["timestamp_fim"] = datetime.now().isoformat()
                
                # Calcular duração
                inicio = datetime.fromisoformat(self.log_data["timestamp_inicio"])
                fim = datetime.fromisoformat(self.log_data["timestamp_fim"])
                self.log_data["duracao_segundos"] = (fim - inicio).total_seconds()
                
                # Atualizar log principal
                self._salvar_log()
            
            return result
            
        except Exception as e:
            # Registrar erro (caso o evento task.error não tenha sido capturado)
            if self.log_data["status"] == "iniciado":
                self.log_data["status"] = "erro"
                self.log_data["erro"] = str(e)
                self.log_data["timestamp_fim"] = datetime.now().isoformat()
                
                # Calcular duração
                inicio = datetime.fromisoformat(self.log_data["timestamp_inicio"])
                fim = datetime.fromisoformat(self.log_data["timestamp_fim"])
                self.log_data["duracao_segundos"] = (fim - inicio).total_seconds()
                
                # Atualizar log principal
                self._salvar_log()
            
            logger.error(f"Erro ao executar agente: {str(e)}")
            raise
    
    def gerar_relatorio_html(self):
        """
        Gera um relatório HTML com os logs capturados
        """
        # Criar arquivo HTML
        html_path = os.path.join(self.log_dir, "relatorio.html")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Relatório de Execução do Agente - {self.timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 1200px; margin: 0 auto; }}
                h1, h2, h3 {{ color: #333; }}
                .container {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                .etapa {{ border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .screenshot {{ max-width: 100%; border: 1px solid #ddd; margin: 10px 0; }}
                pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }}
                .info {{ color: #333; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
                .metadata {{ font-size: 0.9em; color: #666; }}
                .plano {{ background-color: #f0f8ff; padding: 10px; border-left: 3px solid #4682b4; }}
            </style>
        </head>
        <body>
            <h1>Relatório de Execução do Agente</h1>
            
            <div class="container">
                <h2>Informações Gerais</h2>
                <p><strong>ID da Execução:</strong> {self.timestamp}</p>
                <p><strong>Status:</strong> <span class="{'success' if self.log_data['status'] == 'concluído' else 'error'}">{self.log_data['status']}</span></p>
                <p><strong>Início:</strong> {self.log_data['timestamp_inicio'].replace('T', ' ').split('.')[0]}</p>
                <p><strong>Fim:</strong> {self.log_data.get('timestamp_fim', '').replace('T', ' ').split('.')[0] if self.log_data.get('timestamp_fim') else 'N/A'}</p>
                <p><strong>Duração:</strong> {f"{self.log_data.get('duracao_segundos', 0):.2f} segundos" if self.log_data.get('duracao_segundos') else 'N/A'}</p>
            </div>
            
            <div class="container">
                <h2>Prompts</h2>
                <h3>Prompt Original do Usuário</h3>
                <pre>{self.log_data['prompt_original']}</pre>
                
                <h3>Prompt Efetivo Executado</h3>
                <pre>{self.log_data.get('prompt_efetivo', 'N/A')}</pre>
            </div>
        """
        
        # Adicionar plano de ações se disponível
        if self.log_data.get('plano_acoes'):
            html_content += """
            <div class="container">
                <h2>Plano de Ações</h2>
                <div class="plano">
                    <ol>
            """
            for acao in self.log_data['plano_acoes']:
                html_content += f"<li>{acao}</li>\n"
            
            html_content += """
                    </ol>
                </div>
            </div>
            """
        
        # Adicionar etapas
        html_content += """
            <div class="container">
                <h2>Etapas de Execução</h2>
        """
        
        for etapa in self.log_data['etapas']:
            etapa_num = etapa.get('numero', 'N/A')
            screenshot_path = etapa.get('screenshot_path', '')
            
            html_content += f"""
                <div class="etapa">
                    <h3>Etapa {etapa_num}</h3>
                    <p class="metadata">Timestamp: {etapa.get('timestamp', '').replace('T', ' ').split('.')[0]}</p>
                    
                    <h4>Ação:</h4>
                    <pre>{etapa.get('action', 'N/A')}</pre>
                    
                    <h4>Prompt para LLM:</h4>
                    <pre>{etapa.get('prompt_llm', 'N/A')}</pre>
                    
                    <h4>Resposta do LLM:</h4>
                    <pre>{etapa.get('resposta_llm', 'N/A')}</pre>
            """
            
            # Adicionar screenshot se disponível
            if screenshot_path and os.path.exists(screenshot_path):
                # Obter caminho relativo para o HTML
                rel_path = os.path.relpath(screenshot_path, self.log_dir)
                html_content += f"""
                    <h4>Screenshot:</h4>
                    <img src="{rel_path}" class="screenshot" alt="Screenshot da etapa {etapa_num}">
                """
            
            # Adicionar erro se houver
            if etapa.get('error'):
                html_content += f"""
                    <h4>Erro:</h4>
                    <pre class="error">{etapa.get('error')}</pre>
                """
            
            html_content += """
                </div>
            """
        
        html_content += """
            </div>
            
            <div class="container">
                <h2>Resultado Final</h2>
                <pre>{}</pre>
            </div>
        """.format(json.dumps(self.log_data.get('resultado', {}), indent=2, ensure_ascii=False))
        
        # Finalizar HTML
        html_content += """
        </body>
        </html>
        """
        
        # Salvar arquivo HTML
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Relatório HTML gerado em: {html_path}")
        return html_path

async def main():
    # Prompt básico para buscar o preço do Bitcoin
    prompt = "Abra o google e digite 'Preço do bitcoin hoje', e retorne o preço atual do bitcoin."
    
    # Criar rastreador
    print(f"Iniciando teste de rastreabilidade do agente com prompt: '{prompt}'")
    rastreador = AgentRastreador(prompt_original=prompt)
    
    try:
        # Executar agente com rastreamento
        start_time = time.time()
        resultado = await rastreador.executar_agente()
        end_time = time.time()
        
        # Gerar relatório HTML
        html_path = rastreador.gerar_relatorio_html()
        
        # Mostrar resultado
        print("\nResultado da tarefa:")
        print(resultado)
        
        print(f"\nTempo de execução: {end_time - start_time:.2f} segundos")
        print(f"Logs completos disponíveis em: {rastreador.log_dir}")
        print(f"Relatório HTML disponível em: {html_path}")
        
        return resultado
    
    except Exception as e:
        print(f"\nErro durante execução: {str(e)}")
        return None

if __name__ == "__main__":
    # Executar o teste
    asyncio.run(main()) 