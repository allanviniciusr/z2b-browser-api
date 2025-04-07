/**
 * Cliente para conexão e recebimento de eventos do RabbitMQ
 * Este cliente pode ser facilmente reutilizado em outras aplicações
 */
class RabbitmqClient {
    /**
     * Inicializa o cliente RabbitMQ
     * @param {Object} config Configuração inicial
     * @param {string} config.wsUrl URL do WebSocket RabbitMQ (ex: "ws://localhost:15674/ws")
     * @param {string} config.username Usuário do RabbitMQ
     * @param {string} config.password Senha do RabbitMQ
     * @param {string} config.virtualHost Virtual host do RabbitMQ
     * @param {function} config.onConnected Callback quando conectado
     * @param {function} config.onDisconnected Callback quando desconectado
     * @param {function} config.onError Callback quando ocorre erro
     */
    constructor(config = {}) {
        this.config = {
            wsUrl: config.wsUrl || "ws://localhost:15674/ws",
            username: config.username || "guest",
            password: config.password || "guest",
            virtualHost: config.virtualHost || "/",
            onConnected: config.onConnected || (() => {}),
            onDisconnected: config.onDisconnected || (() => {}),
            onError: config.onError || ((error) => console.error("RabbitMQ Erro:", error))
        };
        
        this.client = null;
        this.connected = false;
        this.subscriptions = new Map();
        this.eventHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = config.maxReconnectAttempts || 10;
        this.reconnectDelay = config.reconnectDelay || 2000;
    }

    /**
     * Conecta ao RabbitMQ
     * @returns {Promise} Promessa resolvida quando conectado
     */
    connect() {
        return new Promise((resolve, reject) => {
            if (this.client && this.connected) {
                resolve();
                return;
            }

            try {
                // Verifica se StompJS está disponível em alguma forma
                let stompClient;
                const self = this;
                
                if (typeof StompJs !== 'undefined') {
                    // Versão moderna do StompJS
                    stompClient = new StompJs.Client({
                        brokerURL: this.config.wsUrl,
                        connectHeaders: {
                            login: this.config.username,
                            passcode: this.config.password,
                            host: this.config.virtualHost
                        },
                        debug: function(str) {
                            // console.log('STOMP: ' + str);
                        },
                        reconnectDelay: 5000,
                        heartbeatIncoming: 30000,
                        heartbeatOutgoing: 30000
                    });
                } else if (typeof Stomp !== 'undefined') {
                    // Versão legada do STOMP
                    const ws = new WebSocket(this.config.wsUrl);
                    stompClient = Stomp.over(ws);
                    stompClient.heartbeat.outgoing = 30000;
                    stompClient.heartbeat.incoming = 30000;
                    
                    // Cria um adaptador para a API moderna
                    stompClient.activate = function() {
                        this.connect(
                            self.config.username,
                            self.config.password,
                            frame => {
                                if (typeof this.onConnect === 'function') {
                                    this.onConnect(frame);
                                }
                            },
                            error => {
                                if (typeof this.onStompError === 'function') {
                                    this.onStompError(error);
                                }
                            },
                            self.config.virtualHost
                        );
                    };
                    
                    stompClient.deactivate = function() {
                        this.disconnect();
                    };
                } else {
                    reject(new Error("Biblioteca STOMP não encontrada. Certifique-se de incluir stomp.js ou @stomp/stompjs"));
                    return;
                }
                
                // Configura callbacks
                stompClient.onConnect = frame => {
                    this.connected = true;
                    this.reconnectAttempts = 0;
                    this.client = stompClient;
                    this.config.onConnected(frame);
                    resolve(frame);
                };
                
                stompClient.onStompError = frame => {
                    const error = new Error(`STOMP Error: ${frame.headers?.message || 'Erro desconhecido'}`);
                    this.config.onError(error);
                    reject(error);
                };
                
                stompClient.onWebSocketClose = () => {
                    this.connected = false;
                    this.config.onDisconnected();
                };
                
                // Inicia a conexão
                stompClient.activate();
                this.client = stompClient;
            } catch (error) {
                this.config.onError(error);
                reject(error);
            }
        });
    }

    /**
     * Tratamento de erros de conexão
     * @param {Object} error Erro de conexão
     */
    handleConnectionError(error) {
        this.connected = false;
        this.config.onError(error);
        this.config.onDisconnected();
        
        // Reconectar após um intervalo
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Tentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.connect()
                    .then(() => {
                        console.log("Reconectado ao RabbitMQ");
                        // Restaura assinaturas após reconexão
                        this.restoreSubscriptions();
                    })
                    .catch(err => {
                        console.error("Falha ao reconectar:", err);
                    });
            }, this.reconnectDelay);
        }
    }

    /**
     * Restaura todas as assinaturas após reconexão
     */
    async restoreSubscriptions() {
        for (const [queueName, callback] of this.subscriptions.entries()) {
            try {
                await this.subscribe(queueName, callback);
                console.log(`Assinatura restaurada para fila: ${queueName}`);
            } catch (error) {
                console.error(`Falha ao restaurar assinatura para fila ${queueName}:`, error);
            }
        }
    }

    /**
     * Desconecta do RabbitMQ
     */
    disconnect() {
        if (this.client && this.connected) {
            this.client.deactivate();
            this.connected = false;
            this.subscriptions.clear();
            this.config.onDisconnected();
        }
    }

    /**
     * Assina uma fila para receber mensagens
     * @param {string} queueName Nome da fila ou routing key
     * @param {function} callback Função chamada quando uma mensagem é recebida
     * @returns {Promise} Promessa resolvida quando assinado
     */
    async subscribe(queueName, callback) {
        if (!this.connected) {
            await this.connect();
        }

        return new Promise((resolve, reject) => {
            try {
                const routingKey = `/exchange/task_exchange/event.${queueName}`;
                
                const subscription = this.client.subscribe(routingKey, (message) => {
                    try {
                        const body = JSON.parse(message.body);
                        callback(body);
                        
                        // Processa os manipuladores de eventos específicos
                        if (body.event_type && this.eventHandlers.has(body.event_type)) {
                            const handlers = this.eventHandlers.get(body.event_type);
                            handlers.forEach(handler => handler(body));
                        }
                    } catch (error) {
                        console.error("Erro ao processar mensagem:", error);
                    }
                }, { ack: "auto" });

                this.subscriptions.set(queueName, subscription);
                resolve(subscription);
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * Cancela a assinatura de uma fila
     * @param {string} queueName Nome da fila
     */
    unsubscribe(queueName) {
        if (this.client && this.connected && this.subscriptions.has(queueName)) {
            const subscription = this.subscriptions.get(queueName);
            subscription.unsubscribe();
            this.subscriptions.delete(queueName);
        }
    }

    /**
     * Registra um manipulador para um tipo específico de evento
     * @param {string} eventType Tipo de evento (task.started, task.thinking, task.action, task.plan, etc)
     * @param {function} handler Função que processa o evento
     */
    onEvent(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        
        this.eventHandlers.get(eventType).push(handler);
    }

    /**
     * Remove um manipulador de evento específico
     * @param {string} eventType Tipo de evento
     * @param {function} handler Manipulador a ser removido
     */
    offEvent(eventType, handler) {
        if (this.eventHandlers.has(eventType)) {
            const handlers = this.eventHandlers.get(eventType);
            const index = handlers.indexOf(handler);
            
            if (index !== -1) {
                handlers.splice(index, 1);
            }
            
            if (handlers.length === 0) {
                this.eventHandlers.delete(eventType);
            }
        }
    }

    /**
     * Monitora uma tarefa específica
     * @param {string} taskId ID da tarefa
     * @param {Object} options Opções adicionais
     * @param {function} options.onPlan Callback para plano da tarefa
     * @param {function} options.onAction Callback para ações da tarefa
     * @param {function} options.onThinking Callback para pensamentos da tarefa
     * @param {function} options.onScreenshot Callback para screenshots
     * @param {function} options.onCompleted Callback para conclusão da tarefa
     * @param {function} options.onError Callback para erros da tarefa
     * @param {function} options.onMessage Callback para qualquer mensagem
     * @returns {Object} Objeto com método stopMonitoring para interromper o monitoramento
     */
    monitorTask(taskId, options = {}) {
        const handlers = new Map();
        
        // Processa planos
        if (options.onPlan) {
            const handler = (message) => {
                if (message.event_type === 'task.plan') {
                    options.onPlan(message);
                }
            };
            this.onEvent('task.plan', handler);
            handlers.set('task.plan', handler);
        }
        
        // Processa ações
        if (options.onAction) {
            const handler = (message) => {
                if (message.event_type === 'task.action') {
                    options.onAction(message);
                }
            };
            this.onEvent('task.action', handler);
            handlers.set('task.action', handler);
        }
        
        // Processa pensamentos
        if (options.onThinking) {
            const handler = (message) => {
                if (message.event_type === 'task.thinking') {
                    options.onThinking(message);
                }
            };
            this.onEvent('task.thinking', handler);
            handlers.set('task.thinking', handler);
        }
        
        // Processa screenshots
        if (options.onScreenshot) {
            const handler = (message) => {
                if (message.event_type === 'task.screenshot') {
                    options.onScreenshot(message);
                }
            };
            this.onEvent('task.screenshot', handler);
            handlers.set('task.screenshot', handler);
        }
        
        // Processa conclusão
        if (options.onCompleted) {
            const handler = (message) => {
                if (message.event_type === 'task.completed') {
                    options.onCompleted(message);
                }
            };
            this.onEvent('task.completed', handler);
            handlers.set('task.completed', handler);
        }
        
        // Processa erros
        if (options.onError) {
            const handler = (message) => {
                if (message.event_type === 'task.error') {
                    options.onError(message);
                }
            };
            this.onEvent('task.error', handler);
            handlers.set('task.error', handler);
        }
        
        // Assina a fila da tarefa
        this.subscribe(taskId, (message) => {
            if (options.onMessage) {
                options.onMessage(message);
            }
        }).catch(error => {
            console.error(`Erro ao assinar fila para tarefa ${taskId}:`, error);
        });
        
        // Retorna método para interromper o monitoramento
        return {
            stopMonitoring: () => {
                this.unsubscribe(taskId);
                
                // Remove todos os manipuladores registrados
                for (const [eventType, handler] of handlers.entries()) {
                    this.offEvent(eventType, handler);
                }
            }
        };
    }
} 