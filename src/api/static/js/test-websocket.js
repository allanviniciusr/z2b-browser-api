/**
 * WebSocket de teste para receber eventos do RabbitMQ via bridge WebSocket
 */
class TestWebSocket {
    constructor() {
        this.webSocket = null;
        this.connected = false;
        this.logElement = document.getElementById('wsLog');
        this.statusElement = document.getElementById('wsStatus');
        this.eventHandlers = {};
        this.simulationInterval = null;
        this.currentTaskId = null;
        
        this.log('Cliente WebSocket pronto para se conectar ao RabbitMQ.');
    }
    
    /**
     * Inicia o WebSocket para conectar ao bridge RabbitMQ
     */
    start() {
        if (this.connected) {
            this.log('WebSocket já está conectado.');
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/rabbitmq`;
        
        try {
            this.log(`Conectando ao bridge RabbitMQ em ${wsUrl}...`);
            this.webSocket = new WebSocket(wsUrl);
            
            this.webSocket.onopen = () => {
                this.connected = true;
                this.log('WebSocket conectado! Aguardando eventos do RabbitMQ.');
                this.updateStatus('Conectado', 'connected');
            };
            
            this.webSocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // Se for uma mensagem do sistema, apenas exibe no log
                    if (data.type === 'system') {
                        this.log(`Sistema: ${data.message}`);
                        return;
                    }
                    
                    // Registra a mensagem no log
                    const eventType = data.event_type || 'desconhecido';
                    this.log(`Evento recebido: ${eventType} - Tarefa: ${data.task_id || 'N/A'}`);
                    
                    // Aciona o evento customizado para a interface
                    const customEvent = new CustomEvent('test-event', { detail: data });
                    document.dispatchEvent(customEvent);
                } catch (error) {
                    this.log(`Erro ao processar mensagem: ${error.message}`);
                    console.error("Mensagem recebida:", event.data);
                }
            };
            
            this.webSocket.onclose = () => {
                this.connected = false;
                this.log('WebSocket desconectado do bridge RabbitMQ.');
                this.updateStatus('Desconectado', 'disconnected');
            };
            
            this.webSocket.onerror = (error) => {
                this.log(`Erro no WebSocket: ${error.message || 'Erro desconhecido'}`);
                this.updateStatus('Erro', 'error');
                
                // Sugestão para o usuário
                this.log("Verifique se o RabbitMQ está em execução e acessível pelo servidor da API.");
                this.log("O bridge WebSocket/RabbitMQ deve estar funcionando na API para receber eventos.");
            };
        } catch (error) {
            this.log(`Erro ao iniciar WebSocket: ${error.message}`);
            this.updateStatus('Erro', 'error');
        }
    }
    
    /**
     * Para o WebSocket
     */
    stop() {
        if (this.webSocket) {
            this.webSocket.close();
            this.webSocket = null;
        }
        
        this.connected = false;
        this.updateStatus('Desconectado', 'disconnected');
        this.log('Conexão com o bridge RabbitMQ encerrada.');
    }
    
    /**
     * Solicita uma demonstração via RabbitMQ
     */
    requestDemo() {
        if (!this.webSocket || this.webSocket.readyState !== WebSocket.OPEN) {
            this.log('Não é possível solicitar demonstração. WebSocket não está conectado.');
            return;
        }
        
        this.log('Solicitando demonstração via RabbitMQ...');
        this.webSocket.send(JSON.stringify({
            command: 'simulate'
        }));
    }
    
    /**
     * Adiciona uma entrada ao log
     * @param {string} message Mensagem a ser adicionada
     */
    log(message) {
        if (!this.logElement) return;
        
        const logEntry = document.createElement('div');
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        this.logElement.appendChild(logEntry);
        this.logElement.scrollTop = this.logElement.scrollHeight;
    }
    
    /**
     * Atualiza o status visual
     * @param {string} status Texto do status
     * @param {string} type Tipo do status (connected, disconnected, error)
     */
    updateStatus(status, type) {
        if (!this.statusElement) return;
        
        this.statusElement.textContent = status;
        this.statusElement.className = `rabbitmq-${type}`;
    }
} 