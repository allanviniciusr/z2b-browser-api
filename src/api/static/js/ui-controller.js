/**
 * Controlador de interface do usuário para a API Z2B Browser
 * Gerencia a interação do usuário e a exibição de eventos do RabbitMQ
 */
class UIController {
    /**
     * Inicializa o controlador de UI
     */
    constructor() {
        // Cliente RabbitMQ
        this.rabbitmqClient = null;
        
        // Task ID atual
        this.currentTaskId = null;
        
        // Monitor de tarefa atual
        this.currentTaskMonitor = null;
        
        // Elementos da UI
        this.elements = {
            taskForm: document.getElementById('taskForm'),
            clientId: document.getElementById('clientId'),
            taskType: document.getElementById('taskType'),
            promptText: document.getElementById('promptText'),
            planSteps: document.getElementById('planSteps'),
            taskResult: document.getElementById('taskResult'),
            taskError: document.getElementById('taskError'),
            taskSuccess: document.getElementById('taskSuccess'),
            taskId: document.getElementById('taskId'),
            checkStatusBtn: document.getElementById('checkStatusBtn'),
            refreshStatusBtn: document.getElementById('refreshStatusBtn') || null,
            taskStatus: document.getElementById('taskStatus'),
            statusText: document.getElementById('statusText'),
            taskStep: document.getElementById('taskStep'),
            taskResultStatus: document.getElementById('taskResultStatus'),
            statusError: document.getElementById('statusError'),
            rabbitmqStatus: document.getElementById('rabbitmqStatus'),
            rabbitmqLog: document.getElementById('rabbitmqLog'),
            queueStatus: document.getElementById('queueStatus'),
            allTasksStatus: document.getElementById('allTasksStatus'),
            planPanel: document.getElementById('planPanel'),
            planDetails: document.getElementById('planDetails'),
            screenshots: document.getElementById('screenshots'),
            wsLog: document.getElementById('wsLog')
        };
        
        // Inicializa os event listeners
        this.initEventListeners();
    }
    
    /**
     * Inicializa o controlador
     */
    init() {
        try {
            // Carrega as configurações da API (do localStorage ou padrões)
            this.loadApiConfig();
            
            // Registra listener para eventos do RabbitMQ via WebSocket
            this.initRabbitMQEventListener();
            
            // Inicializa o estado da interface
            if (this.elements.taskType) {
                this.toggleTaskType();
            }
            
            // Inicializa o cliente RabbitMQ somente se não estivermos em uma versão simplificada
            const useWebSocketBridge = true; // Mudamos para usar o bridge WebSocket em vez do cliente RabbitMQ direto
            
            if (!useWebSocketBridge) {
                this.initRabbitMQClient();
            }
            
            // Verifica disponibilidade da API
            this.checkAPIAvailability();
            
            // Atualiza status só se os elementos existirem
            this.refreshAllStatus();
            
            this.addLogEntry("Interface inicializada. Conecte ao WebSocket para receber eventos.");
        } catch (error) {
            console.error("Erro ao inicializar a interface:", error);
            this.addLogEntry(`Erro ao inicializar: ${error.message}`);
        }
    }
    
    /**
     * Inicializa o cliente RabbitMQ
     */
    initRabbitMQClient() {
        // Extrai hostname da URL atual para permitir conexão local ou em produção
        const hostname = window.location.hostname;
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsPort = '15674'; // Porta padrão para WebSocket RabbitMQ
        const wsUrl = `${wsProtocol}//${hostname}:${wsPort}/ws`;

        this.addLogEntry(`Tentando conectar ao RabbitMQ em ${wsUrl}`);
        
        // Primeiro, verifica se o RabbitMQ está disponível
        this.checkRabbitMQAvailability(hostname, wsPort)
            .then(available => {
                if (!available) {
                    this.addLogEntry('RabbitMQ não está acessível. Verificando se o serviço está rodando...');
                    this.showRabbitMQStatus('Indisponível', 'error');
                    return;
                }
                
                // Cria o cliente e conecta
                this.createRabbitMQClient(wsUrl);
            })
            .catch(error => {
                this.addLogEntry(`Erro ao verificar disponibilidade do RabbitMQ: ${error.message}`);
                this.showRabbitMQStatus('Erro', 'error');
            });
    }
    
    /**
     * Verifica se o RabbitMQ está disponível
     * @param {string} hostname Hostname do RabbitMQ
     * @param {string} port Porta do RabbitMQ WebSocket
     * @returns {Promise<boolean>} Promessa resolvida com status de disponibilidade
     */
    checkRabbitMQAvailability(hostname, port) {
        return new Promise((resolve) => {
            // Timeout para limitar o tempo de verificação
            const timeoutId = setTimeout(() => {
                this.addLogEntry('Timeout ao verificar disponibilidade do RabbitMQ');
                resolve(false);
            }, 3000);

            // Tentativa de conexão direta com WebSocket
            try {
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const testSocket = new WebSocket(`${wsProtocol}//${hostname}:${port}/ws`);
                
                testSocket.onopen = () => {
                    clearTimeout(timeoutId);
                    this.addLogEntry('Conexão de teste com RabbitMQ bem-sucedida');
                    testSocket.close();
                    resolve(true);
                };
                
                testSocket.onerror = () => {
                    clearTimeout(timeoutId);
                    this.addLogEntry('RabbitMQ WebSocket não está disponível');
                    
                    // Adiciona uma mensagem com comandos para iniciar o RabbitMQ
                    this.addLogEntry('Para iniciar o RabbitMQ no Docker, execute:');
                    this.addLogEntry('docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 -p 15674:15674 rabbitmq:3-management');
                    this.addLogEntry('docker exec rabbitmq rabbitmq-plugins enable rabbitmq_web_stomp');
                    resolve(false);
                };
            } catch (error) {
                clearTimeout(timeoutId);
                this.addLogEntry(`Erro ao tentar conexão de teste: ${error.message}`);
                resolve(false);
            }
        });
    }
    
    /**
     * Cria e conecta o cliente RabbitMQ
     * @param {string} wsUrl URL do WebSocket RabbitMQ
     */
    createRabbitMQClient(wsUrl) {
        this.rabbitmqClient = new RabbitmqClient({
            wsUrl: wsUrl,
            username: 'guest',
            password: 'guest',
            virtualHost: '/',
            onConnected: () => {
                this.showRabbitMQStatus('Conectado', 'connected');
                this.addLogEntry('Conectado ao RabbitMQ');
            },
            onDisconnected: () => {
                this.showRabbitMQStatus('Desconectado', 'disconnected');
                this.addLogEntry('Desconectado do RabbitMQ');
            },
            onError: (error) => {
                this.showRabbitMQStatus('Erro de Conexão', 'error');
                this.addLogEntry(`Erro no RabbitMQ: ${error.message}`);
            }
        });
        
        // Conecta ao RabbitMQ
        this.rabbitmqClient.connect()
            .then(() => {
                this.addLogEntry('Conexão com RabbitMQ estabelecida com sucesso!');
                this.refreshAllStatus();
            })
            .catch(error => {
                this.addLogEntry(`Falha ao conectar ao RabbitMQ: ${error.message}`);
                this.showErrorWithTroubleshooting(
                    'statusError', 
                    'Erro de conexão com RabbitMQ', 
                    error.message,
                    [
                        'Verifique se o servidor RabbitMQ está rodando',
                        'Verifique se o plugin rabbitmq_web_stomp está habilitado',
                        'Verifique se a porta 15674 está acessível',
                        'Para desenvolvimento local, execute: docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 -p 15674:15674 rabbitmq:3-management'
                    ]
                );
            });
    }
    
    /**
     * Exibe o status do RabbitMQ na interface
     * @param {string} status Texto do status
     * @param {string} type Tipo do status (connected, disconnected, error)
     */
    showRabbitMQStatus(status, type) {
        this.elements.rabbitmqStatus.textContent = status;
        this.elements.rabbitmqStatus.className = `rabbitmq-${type}`;
    }
    
    /**
     * Exibe um erro com dicas de solução de problemas
     * @param {string} elementId ID do elemento para exibir o erro
     * @param {string} title Título do erro
     * @param {string} message Mensagem de erro
     * @param {string[]} troubleshooting Dicas de solução de problemas
     */
    showErrorWithTroubleshooting(elementId, title, message, troubleshooting = []) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        let html = `<div class="error-title">${title}</div>`;
        html += `<div class="error-message">${message}</div>`;
        
        if (troubleshooting.length > 0) {
            html += '<div class="troubleshooting">';
            html += '<h4>Solução de problemas:</h4>';
            html += '<ul>';
            troubleshooting.forEach(tip => {
                html += `<li>${tip}</li>`;
            });
            html += '</ul>';
            html += '</div>';
        }
        
        element.innerHTML = html;
        element.style.display = 'block';
    }
    
    /**
     * Inicializa os event listeners
     */
    initEventListeners() {
        // Form de criação de tarefa
        console.log("Configurando event listener do formulário de criação de tarefa");
        this.elements.taskForm.addEventListener('submit', event => {
            console.log("Formulário submit interceptado", event);
            event.preventDefault();
            console.log("Event default prevented");
            this.createTask();
        });
        
        // Botão de verificação de status
        this.elements.checkStatusBtn.addEventListener('click', () => {
            this.checkTaskStatus();
        });
        
        // Mudança no tipo de tarefa
        this.elements.taskType.addEventListener('change', () => {
            this.toggleTaskType();
        });
        
        // Botão de atualização de status
        if (this.elements.refreshStatusBtn) {
            this.elements.refreshStatusBtn.addEventListener('click', () => {
                this.refreshAllStatus();
            });
        }
        
        // Botão para tentar novamente conexão com RabbitMQ
        const retryRabbitMQBtn = document.getElementById('retryRabbitMQBtn');
        if (retryRabbitMQBtn) {
            retryRabbitMQBtn.addEventListener('click', () => {
                this.retryRabbitMQConnection();
            });
        }
        
        // Botão para salvar configurações da API
        const saveApiConfigBtn = document.getElementById('saveApiConfigBtn');
        if (saveApiConfigBtn) {
            saveApiConfigBtn.addEventListener('click', () => {
                this.saveApiConfig();
            });
        }
        
        // Botão para redefinir configurações da API
        const resetApiConfigBtn = document.getElementById('resetApiConfigBtn');
        if (resetApiConfigBtn) {
            resetApiConfigBtn.addEventListener('click', () => {
                this.resetApiConfig();
            });
        }
    }
    
    /**
     * Alterna entre os tipos de tarefa
     */
    toggleTaskType() {
        const taskType = this.elements.taskType.value;
        
        // Esconde todas as seções
        document.querySelectorAll('.task-type-section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Mostra a seção correspondente ao tipo selecionado
        document.getElementById(`${taskType}Section`).classList.add('active');
    }
    
    /**
     * Atualiza os dados da tarefa com base no tipo
     */
    updateTaskData() {
        const taskType = this.elements.taskType.value;
        let taskData = {};
        
        if (taskType === 'prompt') {
            const promptText = this.elements.promptText.value;
            taskData = {
                prompt: promptText
            };
        } else if (taskType === 'plan') {
            const planStepsText = this.elements.planSteps.value;
            const steps = planStepsText.split('\n').filter(step => step.trim() !== '');
            taskData = {
                plan: {
                    steps: steps
                }
            };
        }
        
        console.log("Dados da tarefa formatados:", taskData);
        return taskData;
    }
    
    /**
     * Cria uma nova tarefa
     */
    async createTask() {
        console.log("Método createTask iniciado");
        this.hideElement('taskError');
        this.hideElement('taskSuccess');
        this.hideElement('taskResult');
        
        console.log("Obtendo valores dos campos");
        const clientId = this.elements.clientId.value;
        const taskType = this.elements.taskType.value;
        
        console.log("ClientID:", clientId);
        console.log("TaskType:", taskType);
        
        // Validação básica
        if (!clientId) {
            console.log("ClientID vazio - exibindo erro");
            this.showError('taskError', 'Client ID é obrigatório');
            return;
        }
        
        console.log("Obtendo dados da tarefa");
        const taskData = this.updateTaskData();
        console.log("TaskData:", JSON.stringify(taskData));
        
        // Verifica se os dados da tarefa estão preenchidos conforme o tipo
        if (taskType === 'prompt' && (!taskData.prompt || taskData.prompt.trim() === '')) {
            console.log("Prompt vazio - exibindo erro");
            this.showError('taskError', 'Prompt é obrigatório');
            return;
        } else if (taskType === 'plan' && (!taskData.plan || !taskData.plan.steps || taskData.plan.steps.length === 0)) {
            console.log("Plano vazio - exibindo erro");
            this.showError('taskError', 'Pelo menos um passo do plano é obrigatório');
            return;
        }
        
        console.log("Validação concluída com sucesso");
        this.addLogEntry(`Criando tarefa do tipo: ${taskType}`);
        
        try {
            console.log("Obtendo URL da API");
            const url = this.getApiUrl('taskCreate');
            console.log("URL para criar tarefa:", url);
            this.addLogEntry(`Enviando requisição para: ${url}`);
            
            const requestData = {
                client_id: clientId,
                task_type: taskType,
                data: taskData
            };
            
            console.log("Dados formatados para envio:", JSON.stringify(requestData));
            
            console.log("Iniciando fetch para API");
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            console.log("Resposta recebida:", response.status);
            const data = await response.json();
            console.log("Dados da resposta:", data);
            
            if (response.ok) {
                console.log("Requisição bem-sucedida");
                this.showSuccess('taskSuccess', `Tarefa criada com sucesso! ID: ${data.task_id}`);
                this.showJsonResult('taskResult', data);
                
                // Atualiza o campo de Task ID para consulta
                this.elements.taskId.value = data.task_id;
                
                // Inicia o monitoramento da tarefa
                this.startTaskMonitoring(data.task_id, clientId);
                
                this.addLogEntry(`Tarefa criada com ID: ${data.task_id}`);
            } else {
                console.log("Requisição falhou com status:", response.status);
                this.showError('taskError', `Erro: ${data.detail || 'Erro desconhecido'}`);
                this.addLogEntry(`Erro ao criar tarefa: ${data.detail || 'Erro desconhecido'}`);
            }
        } catch (error) {
            console.error("Erro na requisição:", error);
            this.showError('taskError', `Erro ao criar tarefa: ${error.message}`);
            this.addLogEntry(`Erro ao criar tarefa: ${error.message}`);
        }
    }
    
    /**
     * Inicia o monitoramento de uma tarefa
     * @param {string} taskId ID da tarefa
     * @param {string} clientId ID do cliente
     */
    startTaskMonitoring(taskId, clientId) {
        // Limpa monitoramento anterior se existir
        if (this.currentTaskMonitor) {
            this.currentTaskMonitor.stopMonitoring();
        }
        
        this.currentTaskId = taskId;
        
        // Limpa painéis existentes
        this.elements.planPanel.style.display = 'none';
        this.elements.planDetails.innerHTML = '';
        this.elements.screenshots.innerHTML = '';
        
        // Adiciona log de monitoramento
        this.addLogEntry(`Iniciando monitoramento da tarefa ${taskId}`);
        
        // Inicia o monitoramento
        this.currentTaskMonitor = this.rabbitmqClient.monitorTask(taskId, {
            onPlan: (message) => {
                this.addLogEntry(`Recebido plano para tarefa ${taskId}`);
                
                // Exibe o plano recebido
                this.displayPlan(message);
                
                // Atualiza status
                const statusData = {
                    task_id: taskId,
                    status: 'processing',
                    current_step: 'Planejamento criado',
                };
                
                this.updateTaskStatusDisplay(statusData);
            },
            onAction: (message) => {
                this.addLogEntry(`Recebida ação: ${message.step_description || 'Executando ação'}`);
                
                // Atualiza status
                const statusData = {
                    task_id: taskId,
                    status: 'processing',
                    current_step: message.step_description || 'Executando ação',
                };
                
                this.updateTaskStatusDisplay(statusData);
            },
            onThinking: (message) => {
                const thought = message.data?.thought || 'Analisando próxima ação';
                this.addLogEntry(`Pensamento: ${thought}`);
                
                // Atualiza status
                const statusData = {
                    task_id: taskId,
                    status: 'processing',
                    current_step: thought,
                };
                
                this.updateTaskStatusDisplay(statusData);
            },
            onScreenshot: (message) => {
                this.addLogEntry(`Recebido screenshot da URL: ${message.current_url || 'Página atual'}`);
                
                // Exibe o screenshot
                this.displayScreenshot(message);
            },
            onCompleted: (message) => {
                this.addLogEntry(`Tarefa ${taskId} concluída!`);
                
                // Atualiza status
                const statusData = {
                    task_id: taskId,
                    status: 'completed',
                    current_step: 'Tarefa concluída',
                    result: message.data
                };
                
                this.updateTaskStatusDisplay(statusData);
                
                // Exibe o screenshot final se disponível
                if (message.screenshot) {
                    this.displayScreenshot(message);
                }
            },
            onError: (message) => {
                const errorMsg = message.data?.error || 'Erro desconhecido';
                this.addLogEntry(`Erro na tarefa ${taskId}: ${errorMsg}`);
                
                // Atualiza status
                const statusData = {
                    task_id: taskId,
                    status: 'error',
                    current_step: `Erro: ${errorMsg}`,
                };
                
                this.updateTaskStatusDisplay(statusData);
            },
            onMessage: (message) => {
                console.log("Mensagem recebida:", message);
            }
        });
    }
    
    /**
     * Exibe o plano recebido
     * @param {Object} message Mensagem com o plano
     */
    displayPlan(message) {
        // Exibe o painel do plano
        this.elements.planPanel.style.display = 'block';
        
        // Constrói o HTML para o plano
        let planHTML = '<h4>Planejamento da Tarefa</h4>';
        
        if (message.data && message.data.plan) {
            const plan = message.data.plan;
            
            // Tenta formatar o plano como uma lista de etapas
            try {
                if (typeof plan === 'string') {
                    // Tenta converter string para objeto se parecer JSON
                    try {
                        const planObj = JSON.parse(plan);
                        planHTML += '<ul>';
                        
                        if (planObj.steps) {
                            // Formato com steps
                            planObj.steps.forEach(step => {
                                planHTML += `<li>${step}</li>`;
                            });
                        } else if (Array.isArray(planObj)) {
                            // Array simples
                            planObj.forEach(step => {
                                planHTML += `<li>${step}</li>`;
                            });
                        } else {
                            // Outro formato de objeto
                            Object.entries(planObj).forEach(([key, value]) => {
                                planHTML += `<li><strong>${key}:</strong> ${value}</li>`;
                            });
                        }
                        
                        planHTML += '</ul>';
                    } catch (e) {
                        // Se não for JSON, exibe como texto
                        const lines = plan.split('\n');
                        
                        if (lines.length > 1) {
                            planHTML += '<ul>';
                            lines.forEach(line => {
                                if (line.trim()) {
                                    planHTML += `<li>${line}</li>`;
                                }
                            });
                            planHTML += '</ul>';
                        } else {
                            planHTML += `<p>${plan}</p>`;
                        }
                    }
                } else if (typeof plan === 'object') {
                    // Objeto JavaScript
                    planHTML += '<ul>';
                    if (Array.isArray(plan)) {
                        plan.forEach(step => {
                            planHTML += `<li>${step}</li>`;
                        });
                    } else {
                        Object.entries(plan).forEach(([key, value]) => {
                            planHTML += `<li><strong>${key}:</strong> ${value}</li>`;
                        });
                    }
                    planHTML += '</ul>';
                }
            } catch (error) {
                // Fallback: exibe o plano como JSON
                planHTML += `<pre>${JSON.stringify(plan, null, 2)}</pre>`;
            }
        } else {
            planHTML += '<p>Nenhum detalhe de plano disponível</p>';
        }
        
        // Adiciona o prompt original
        if (message.data && message.data.prompt) {
            planHTML += `<h4>Prompt Original</h4><div class="prompt-box">${message.data.prompt}</div>`;
        }
        
        // Insere o HTML no painel
        this.elements.planDetails.innerHTML = planHTML;
    }
    
    /**
     * Exibe um screenshot recebido
     * @param {Object} message Mensagem com o screenshot
     */
    displayScreenshot(message) {
        if (!message.screenshot) return;
        
        // Cria um novo elemento para o screenshot
        const screenshotContainer = document.createElement('div');
        screenshotContainer.className = 'screenshot-container';
        
        // Adiciona o cabeçalho com timestamp
        const timestamp = new Date(message.timestamp).toLocaleTimeString();
        const header = document.createElement('div');
        header.className = 'screenshot-header';
        header.innerHTML = `
            <span class="timestamp">${timestamp}</span>
            <span class="url">${message.current_url || ''}</span>
        `;
        
        // Adiciona a descrição se disponível
        if (message.step_description) {
            const description = document.createElement('div');
            description.className = 'screenshot-description';
            description.textContent = message.step_description;
            screenshotContainer.appendChild(description);
        }
        
        // Adiciona a imagem
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${message.screenshot}`;
        img.className = 'screenshot-img';
        img.alt = 'Screenshot da tarefa';
        
        // Monta o container
        screenshotContainer.appendChild(header);
        screenshotContainer.appendChild(img);
        
        // Adiciona ao painel de screenshots
        this.elements.screenshots.insertBefore(screenshotContainer, this.elements.screenshots.firstChild);
    }
    
    /**
     * Verifica o status de uma tarefa específica
     */
    async checkTaskStatus() {
        const taskId = this.elements.taskId.value;
        
        if (!taskId) {
            this.showError('statusError', 'Por favor, insira um Task ID');
            return;
        }
        
        this.hideElement('statusError');
        
        try {
            const response = await fetch(this.getApiUrl('taskDetail', { id: taskId }));
            const data = await response.json();
            
            if (response.ok) {
                this.updateTaskStatusDisplay(data);
                
                // Se não estamos já monitorando esta tarefa, iniciamos
                if (this.currentTaskId !== taskId) {
                    this.startTaskMonitoring(taskId, data.client_id || 'unknown');
                }
            } else {
                this.showError('statusError', `Erro: ${data.detail || 'Erro desconhecido'}`);
            }
        } catch (error) {
            this.showError('statusError', `Erro ao verificar status: ${error.message}`);
        }
    }
    
    /**
     * Atualiza a exibição do status da tarefa
     * @param {Object} data Dados de status da tarefa
     */
    updateTaskStatusDisplay(data) {
        const statusElement = this.elements.taskStatus;
        const statusTextElement = this.elements.statusText;
        const taskStepElement = this.elements.taskStep;
        const taskResultElement = this.elements.taskResultStatus;
        
        statusElement.style.display = 'block';
        statusTextElement.textContent = data.status;
        
        // Adiciona classe de estilo baseada no status
        statusElement.className = 'task-status';
        statusElement.classList.add(`status-${data.status}`);
        
        // Exibe o passo atual se disponível
        if (data.current_step) {
            taskStepElement.textContent = `Passo atual: ${data.current_step}`;
            taskStepElement.style.display = 'block';
        } else {
            taskStepElement.style.display = 'none';
        }
        
        // Exibe o resultado se disponível
        if (data.result) {
            taskResultElement.textContent = JSON.stringify(data.result, null, 2);
            taskResultElement.style.display = 'block';
        } else {
            taskResultElement.style.display = 'none';
        }
    }
    
    /**
     * Verifica o status das filas RabbitMQ
     */
    checkQueueStatus() {
        try {
            fetch(this.getApiUrl('queueStatus'))
                .then(response => response.json())
                .then(info => {
                    if (!this.elements.queueStatus) return;
                    
                    let html = '';
                    
                    // Verifica se info é um objeto válido e não está vazio
                    if (info && typeof info === 'object' && Object.keys(info).length > 0) {
                        try {
                            for (const [queueName, queueInfo] of Object.entries(info)) {
                                if (queueInfo) {
                                    html += `
                                        <div class="status-item">
                                            <div><strong>Nome:</strong> ${queueName}</div>
                                            <div><strong>Mensagens:</strong> ${queueInfo.messages || 0}</div>
                                            <div><strong>Consumidores:</strong> ${queueInfo.consumers || 0}</div>
                                            <div><strong>Estado:</strong> ${queueInfo.state || 'desconhecido'}</div>
                                        </div>
                                    `;
                                }
                            }
                        } catch (err) {
                            console.warn('Erro ao processar informações das filas:', err);
                            html = '<div class="status-item">Erro ao processar informações das filas</div>';
                        }
                    } else {
                        html = '<div class="status-item">Nenhuma fila encontrada ou servidor RabbitMQ não está disponível.</div>';
                    }
                    
                    this.elements.queueStatus.innerHTML = html;
                })
                .catch(error => {
                    console.error('Erro ao verificar status das filas:', error);
                    if (this.elements.queueStatus) {
                        this.elements.queueStatus.innerHTML = `
                            <div class="status-item">
                                <div>Não foi possível verificar o status das filas RabbitMQ</div>
                            </div>
                        `;
                    }
                });
        } catch (error) {
            console.log('Erro ao tentar verificar filas:', error);
            if (this.elements.queueStatus) {
                this.elements.queueStatus.innerHTML = '<div class="status-item">Erro ao verificar filas</div>';
            }
        }
    }
    
    /**
     * Verifica o status de todas as tarefas
     */
    checkAllTasksStatus() {
        try {
            fetch(this.getApiUrl('taskStatus'))
                .then(response => response.json())
                .then(data => {
                    if (!this.elements.allTasksStatus) return;
                    
                    let html = '';
                    
                    if (!data || !Array.isArray(data)) {
                        this.elements.allTasksStatus.innerHTML = '<div class="status-item">Não foi possível obter informações das tarefas.</div>';
                        return;
                    }
                    
                    if (data.length === 0) {
                        html = '<div class="status-item">Nenhuma tarefa encontrada.</div>';
                    } else {
                        data.forEach(task => {
                            let statusClass = '';
                            switch (task.status) {
                                case 'completed':
                                    statusClass = 'status-completed';
                                    break;
                                case 'processing':
                                    statusClass = 'status-processing';
                                    break;
                                case 'error':
                                    statusClass = 'status-error';
                                    break;
                                default:
                                    statusClass = 'status-queued';
                            }
                            
                            html += `
                                <div class="status-item ${statusClass}">
                                    <div><strong>ID:</strong> ${task.task_id}</div>
                                    <div><strong>Cliente:</strong> ${task.client_id || 'N/A'}</div>
                                    <div><strong>Status:</strong> ${task.status}</div>
                                    <div><strong>Tipo:</strong> ${task.type || 'N/A'}</div>
                                    ${task.current_step ? `<div><strong>Passo:</strong> ${task.current_step}</div>` : ''}
                                    <button class="monitor-btn" data-task-id="${task.task_id}">Monitorar</button>
                                </div>
                            `;
                        });
                    }
                    
                    this.elements.allTasksStatus.innerHTML = html;
                    
                    // Adiciona listeners aos botões de monitoramento
                    document.querySelectorAll('.monitor-btn').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const taskId = btn.getAttribute('data-task-id');
                            this.startTaskMonitoring(taskId);
                            this.elements.taskId.value = taskId;
                        });
                    });
                })
                .catch(error => {
                    console.error('Erro ao verificar status de todas as tarefas:', error);
                    if (this.elements.allTasksStatus) {
                        this.elements.allTasksStatus.innerHTML = '<div class="status-item">Erro ao verificar tarefas. Servidor API pode estar indisponível.</div>';
                    }
                });
        } catch (error) {
            console.log('Erro ao tentar verificar tarefas:', error);
        }
    }
    
    /**
     * Atualiza todos os status
     */
    refreshAllStatus() {
        this.checkQueueStatus();
        this.checkAllTasksStatus();
    }
    
    /**
     * Adiciona uma entrada ao log
     * @param {string} message Mensagem a ser adicionada
     * @param {HTMLElement} contentElement Elemento HTML opcional para adicionar como conteúdo
     */
    addLogEntry(message, contentElement = null) {
        if (!this.elements.wsLog) return;
        
        const logEntry = document.createElement('div');
        
        if (message) {
            logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        }
        
        if (contentElement) {
            if (message) {
                logEntry.appendChild(document.createElement('br'));
            }
            logEntry.appendChild(contentElement);
        }
        
        this.elements.wsLog.appendChild(logEntry);
        this.elements.wsLog.scrollTop = this.elements.wsLog.scrollHeight;
    }
    
    /**
     * Exibe uma mensagem de erro
     * @param {string} elementId ID do elemento para exibir o erro
     * @param {string} message Mensagem de erro
     */
    showError(elementId, message) {
        const element = document.getElementById(elementId);
        element.textContent = message;
        element.style.display = 'block';
    }
    
    /**
     * Exibe uma mensagem de sucesso
     * @param {string} elementId ID do elemento para exibir o sucesso
     * @param {string} message Mensagem de sucesso
     */
    showSuccess(elementId, message) {
        const element = document.getElementById(elementId);
        element.textContent = message;
        element.style.display = 'block';
    }
    
    /**
     * Exibe um resultado em formato JSON
     * @param {string} elementId ID do elemento para exibir o resultado
     * @param {Object} data Dados a serem exibidos
     */
    showJsonResult(elementId, data) {
        const element = document.getElementById(elementId);
        element.textContent = JSON.stringify(data, null, 2);
        element.style.display = 'block';
    }
    
    /**
     * Esconde um elemento
     * @param {string} elementId ID do elemento a ser escondido
     */
    hideElement(elementId) {
        document.getElementById(elementId).style.display = 'none';
    }
    
    /**
     * Tenta reconectar ao RabbitMQ
     */
    retryRabbitMQConnection() {
        // Limpa o log atual
        this.elements.rabbitmqLog.innerHTML = '';
        this.addLogEntry('Tentando estabelecer nova conexão com RabbitMQ...');
        
        // Extrai hostname e porta
        const hostname = window.location.hostname;
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsPort = '15674';
        const wsUrl = `${wsProtocol}//${hostname}:${wsPort}/ws`;
        
        // Verifica disponibilidade
        this.checkRabbitMQAvailability(hostname, wsPort)
            .then(available => {
                if (available) {
                    this.createRabbitMQClient(wsUrl);
                } else {
                    this.showRabbitMQStatus('Indisponível', 'error');
                    this.addLogEntry('RabbitMQ continua indisponível. Verifique as instruções acima.');
                }
            });
    }
    
    /**
     * Verifica se os endpoints da API estão disponíveis
     */
    checkAPIAvailability() {
        this.addLogEntry('Verificando disponibilidade dos endpoints da API...');
        
        // Endpoints para verificar (métodos GET apenas)
        const endpoints = [
            { url: this.getApiUrl('taskStatus'), name: 'Status das Tarefas' },
            { url: this.getApiUrl('queueStatus'), name: 'Status das Filas' }
        ];
        
        // Div para exibir status da API
        const existingApiStatus = document.getElementById('apiStatus');
        const apiStatusDiv = existingApiStatus || document.createElement('div');
        
        if (!existingApiStatus) {
            apiStatusDiv.id = 'apiStatus';
            apiStatusDiv.className = 'info-box';
            
            // Insere antes do status do RabbitMQ
            const rabbitmqLogElement = document.getElementById('rabbitmqLog');
            if (rabbitmqLogElement) {
                rabbitmqLogElement.parentNode.insertBefore(apiStatusDiv, rabbitmqLogElement);
            }
        }
        
        apiStatusDiv.innerHTML = '<h4>Verificando endpoints da API...</h4>';
        
        // Verifica cada endpoint
        let allAvailable = true;
        const results = [];
        
        Promise.all(endpoints.map(endpoint => 
            fetch(endpoint.url)
                .then(response => {
                    const available = response.ok;
                    results.push({
                        name: endpoint.name,
                        url: endpoint.url,
                        available,
                        status: response.status
                    });
                    return available;
                })
                .catch(() => {
                    results.push({
                        name: endpoint.name,
                        url: endpoint.url,
                        available: false,
                        status: 'Erro'
                    });
                    return false;
                })
        ))
        .then(availabilities => {
            allAvailable = availabilities.every(available => available);
            
            // Atualiza a interface com os resultados
            let html = '<h4>Status dos Endpoints da API</h4>';
            
            if (allAvailable) {
                html += '<div class="api-status-success">Todos os endpoints da API estão disponíveis!</div>';
            } else {
                html += '<div class="api-status-error">Alguns endpoints da API não estão disponíveis!</div>';
                html += '<div class="api-troubleshooting">';
                html += '<h5>Possíveis soluções:</h5>';
                html += '<ul>';
                html += '<li>Verifique se o servidor da API está em execução</li>';
                html += '<li>Verifique se as rotas da API correspondem às esperadas</li>';
                html += '<li>Use o painel de configurações abaixo para ajustar os endpoints</li>';
                html += '</ul>';
                html += '</div>';
            }
            
            html += '<div class="api-endpoints">';
            results.forEach(result => {
                const statusClass = result.available ? 'endpoint-available' : 'endpoint-unavailable';
                html += `<div class="${statusClass}">`;
                html += `<strong>${result.name}</strong>: ${result.url} - `;
                html += result.available ? 'Disponível' : `Indisponível (${result.status})`;
                html += '</div>';
            });
            html += '</div>';
            
            apiStatusDiv.innerHTML = html;
            
            // Adiciona informações ao log
            this.addLogEntry(`Verificação de API concluída. ${allAvailable ? 'Todos disponíveis' : 'Alguns indisponíveis'}.`);
            
            // Se API não estiver disponível, sugere possíveis soluções específicas
            if (!allAvailable) {
                this.addLogEntry('A API não está totalmente disponível. Use as configurações abaixo para ajustar os endpoints.');
            }
        });
    }
    
    /**
     * Carrega as configurações da API
     */
    loadApiConfig() {
        // Valores padrão
        this.apiConfig = {
            base: '',
            taskStatus: 'tasks/status',
            queueStatus: 'tasks/queue',
            taskCreate: 'tasks',  // Correto endpoint para criar tarefas
            taskDetail: 'tasks/{id}'
        };
        
        try {
            // Tenta carregar do localStorage
            const savedConfig = localStorage.getItem('apiConfig');
            if (savedConfig) {
                const parsedConfig = JSON.parse(savedConfig);
                this.apiConfig = { ...this.apiConfig, ...parsedConfig };
            }
        } catch (error) {
            console.error('Erro ao carregar configurações da API:', error);
        }
        
        // Preenche os campos do formulário com os valores carregados
        this.updateApiConfigForm();
    }
    
    /**
     * Atualiza o formulário com as configurações atuais da API
     */
    updateApiConfigForm() {
        // Preenche os campos do formulário
        const setElementValue = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.value = value;
            }
        };
        
        setElementValue('apiBase', this.apiConfig.base || '');
        setElementValue('taskStatusEndpoint', this.apiConfig.taskStatus || 'tasks/status');
        setElementValue('queueStatusEndpoint', this.apiConfig.queueStatus || 'tasks/queue');
        setElementValue('taskCreateEndpoint', this.apiConfig.taskCreate || 'tasks/create');
    }
    
    /**
     * Salva as configurações da API
     */
    saveApiConfig() {
        // Função auxiliar para obter valor de um elemento
        const getElementValue = (id, defaultValue = '') => {
            const element = document.getElementById(id);
            return element ? element.value.trim() : defaultValue;
        };
        
        // Coleta os valores do formulário
        const base = getElementValue('apiBase');
        const taskStatus = getElementValue('taskStatusEndpoint', '/tasks/status');
        const queueStatus = getElementValue('queueStatusEndpoint', '/tasks/queue');
        const taskCreate = getElementValue('taskCreateEndpoint', '/tasks/create');
        
        // Atualiza o objeto de configuração
        this.apiConfig = {
            base,
            taskStatus,
            queueStatus,
            taskCreate,
            taskDetail: taskStatus.replace(/\/status$/, '/{id}/status')
        };
        
        // Salva no localStorage
        try {
            localStorage.setItem('apiConfig', JSON.stringify(this.apiConfig));
            this.addLogEntry('Configurações da API salvas com sucesso!');
            
            // Rechecando a disponibilidade dos endpoints
            this.checkAPIAvailability();
        } catch (error) {
            console.error('Erro ao salvar configurações da API:', error);
            this.addLogEntry('Erro ao salvar configurações: ' + error.message);
        }
    }
    
    /**
     * Redefine as configurações da API para os valores padrão
     */
    resetApiConfig() {
        // Define os valores padrão
        this.apiConfig = {
            base: '',
            taskStatus: 'tasks/status',
            queueStatus: 'tasks/queue',
            taskCreate: 'tasks',
            taskDetail: 'tasks/{id}'
        };
        
        // Atualiza o formulário
        this.updateApiConfigForm();
        
        // Remove do localStorage
        try {
            localStorage.removeItem('apiConfig');
            this.addLogEntry('Configurações da API redefinidas para os valores padrão.');
            
            // Rechecando a disponibilidade dos endpoints
            this.checkAPIAvailability();
        } catch (error) {
            console.error('Erro ao redefinir configurações da API:', error);
        }
    }
    
    /**
     * Retorna a URL completa para um endpoint
     * @param {string} endpoint Nome do endpoint na configuração
     * @param {Object} params Parâmetros para substituir na URL
     * @returns {string} URL completa
     */
    getApiUrl(endpoint, params = {}) {
        let baseUrl = this.apiConfig.base || '';
        // Adiciona prefixo /api quando não tem base configurada
        if (!baseUrl) {
            baseUrl = '/api/';
        } else if (baseUrl.length > 0 && !baseUrl.endsWith('/')) {
            baseUrl += '/';
        }
        let url = baseUrl + this.apiConfig[endpoint];
        
        // Substitui parâmetros na URL
        Object.keys(params).forEach(key => {
            url = url.replace(`{${key}}`, params[key]);
        });
        
        return url;
    }
    
    /**
     * Inicializa o listener para eventos do RabbitMQ via WebSocket
     */
    initRabbitMQEventListener() {
        // Registra um ouvinte para eventos de teste que vêm do WebSocket
        document.addEventListener('test-event', (event) => {
            const eventData = event.detail;
            
            // Processa o evento com base no tipo
            switch (eventData.event_type) {
                case 'task.plan':
                    this.displayPlan(eventData);
                    this.addLogEntry(`Plano recebido para tarefa ${eventData.task_id}`);
                    this.updateCurrentTaskId(eventData.task_id);
                    break;
                
                case 'task.action':
                case 'task.thinking':
                    this.displayAction(eventData);
                    this.addLogEntry(`${eventData.event_type === 'task.action' ? 'Ação' : 'Pensamento'}: ${eventData.step_description || 'Sem descrição'}`);
                    this.updateCurrentTaskId(eventData.task_id);
                    break;
                
                case 'task.screenshot':
                    this.displayScreenshot(eventData);
                    this.addLogEntry(`Screenshot recebido para tarefa ${eventData.task_id}`);
                    this.updateCurrentTaskId(eventData.task_id);
                    break;
                
                case 'task.completed':
                    this.displayCompletion(eventData);
                    this.addLogEntry(`Tarefa ${eventData.task_id} concluída!`);
                    break;
                
                case 'task.error':
                    this.displayError(eventData);
                    this.addLogEntry(`Erro na tarefa ${eventData.task_id}: ${eventData.data?.error || 'Erro não especificado'}`);
                    break;
                
                default:
                    console.log('Evento desconhecido recebido:', eventData);
                    this.addLogEntry(`Evento ${eventData.event_type || 'desconhecido'} recebido`);
            }
        });
    }
    
    /**
     * Atualiza o ID da tarefa atual que está sendo monitorada
     * @param {string} taskId ID da tarefa
     */
    updateCurrentTaskId(taskId) {
        if (taskId && (!this.currentTaskId || this.currentTaskId !== taskId)) {
            this.currentTaskId = taskId;
            this.elements.taskId.value = taskId;
            this.addLogEntry(`Monitorando tarefa: ${taskId}`);
        }
    }
    
    /**
     * Exibe informações de uma ação ou pensamento
     * @param {Object} eventData Dados do evento
     */
    displayAction(eventData) {
        // Atualiza o status da tarefa
        if (this.elements.statusText) {
            this.elements.statusText.textContent = "Processando";
        }
        
        // Atualiza o passo atual
        if (this.elements.taskStep) {
            this.elements.taskStep.textContent = eventData.step_description || 'Executando ação';
            this.elements.taskStep.style.display = 'block';
        }
        
        // Se houver informações do modelo, exibe também
        if (eventData.model_info) {
            const modelInfo = document.createElement('div');
            modelInfo.className = 'model-info';
            modelInfo.innerHTML = `
                <strong>Modelo:</strong> ${eventData.model_info.model_name || 'Não especificado'}<br>
                <strong>Tokens:</strong> ${eventData.model_info.tokens_used || 0}<br>
                <strong>Custo estimado:</strong> $${eventData.model_info.estimated_cost?.toFixed(6) || '0.000000'}
            `;
            
            // Adiciona ao log
            this.addLogEntry('', modelInfo);
        }
    }
    
    /**
     * Exibe o plano de execução
     * @param {Object} eventData Dados do evento
     */
    displayPlan(eventData) {
        const planPanel = document.getElementById('planPanel');
        const planDetails = document.getElementById('planDetails');
        
        if (!planPanel || !planDetails) return;
        
        // Limpa o painel
        planDetails.innerHTML = '';
        
        // Exibe o prompt
        const promptDiv = document.createElement('div');
        promptDiv.innerHTML = `<h3>Prompt</h3>`;
        
        const promptBox = document.createElement('div');
        promptBox.className = 'prompt-box';
        promptBox.textContent = eventData.data?.prompt || 'Prompt não disponível';
        promptDiv.appendChild(promptBox);
        planDetails.appendChild(promptDiv);
        
        // Exibe os passos do plano
        if (eventData.data?.plan?.steps && eventData.data.plan.steps.length > 0) {
            const stepsDiv = document.createElement('div');
            stepsDiv.innerHTML = `<h3>Plano de Execução</h3>`;
            
            const stepsList = document.createElement('ul');
            eventData.data.plan.steps.forEach((step, index) => {
                const stepItem = document.createElement('li');
                stepItem.textContent = step;
                stepsList.appendChild(stepItem);
            });
            
            stepsDiv.appendChild(stepsList);
            planDetails.appendChild(stepsDiv);
        }
        
        // Exibe o painel
        planPanel.style.display = 'block';
        
        // Atualiza o status da tarefa
        if (this.elements.statusText) {
            this.elements.statusText.textContent = "Iniciando";
        }
        
        // Mostra o painel de status
        if (this.elements.taskStatus) {
            this.elements.taskStatus.style.display = 'block';
        }
    }
    
    /**
     * Exibe um screenshot
     * @param {Object} eventData Dados do screenshot
     */
    displayScreenshot(eventData) {
        const screenshotsContainer = document.getElementById('screenshots');
        if (!screenshotsContainer) return;
        
        // Cria o container do screenshot
        const container = document.createElement('div');
        container.className = 'screenshot-container';
        
        // Adiciona cabeçalho com informações
        const header = document.createElement('div');
        header.className = 'screenshot-header';
        
        const timestamp = new Date(eventData.timestamp).toLocaleTimeString();
        const stepInfo = document.createElement('div');
        stepInfo.textContent = `${timestamp} - Tarefa: ${eventData.task_id}`;
        
        const urlInfo = document.createElement('div');
        urlInfo.textContent = eventData.current_url || 'URL não disponível';
        
        header.appendChild(stepInfo);
        header.appendChild(urlInfo);
        container.appendChild(header);
        
        // Adiciona descrição do screenshot
        if (eventData.step_description) {
            const description = document.createElement('div');
            description.className = 'screenshot-description';
            description.textContent = eventData.step_description;
            container.appendChild(description);
        }
        
        // Adiciona a imagem
        if (eventData.screenshot) {
            const img = document.createElement('img');
            img.className = 'screenshot-img';
            img.src = `data:image/png;base64,${eventData.screenshot}`;
            img.alt = eventData.step_description || 'Screenshot';
            container.appendChild(img);
        } else {
            const noImage = document.createElement('div');
            noImage.className = 'no-screenshot';
            noImage.textContent = 'Screenshot não disponível';
            container.appendChild(noImage);
        }
        
        // Adiciona o container ao início da lista (para mostrar o mais recente primeiro)
        screenshotsContainer.insertBefore(container, screenshotsContainer.firstChild);
    }
    
    /**
     * Exibe a conclusão de uma tarefa
     * @param {Object} eventData Dados do evento
     */
    displayCompletion(eventData) {
        // Atualiza o status da tarefa
        if (this.elements.statusText) {
            this.elements.statusText.textContent = "Concluído";
        }
        
        // Atualiza o passo atual
        if (this.elements.taskStep) {
            this.elements.taskStep.textContent = 'Tarefa concluída';
        }
        
        // Exibe o resultado
        if (this.elements.taskResultStatus) {
            this.elements.taskResultStatus.textContent = eventData.data?.result || 'Sem resultado disponível';
            this.elements.taskResultStatus.style.display = 'block';
        }
        
        // Se houver informações do modelo, exibe também
        if (eventData.model_info) {
            const modelInfo = document.createElement('div');
            modelInfo.className = 'model-info success';
            modelInfo.innerHTML = `
                <strong>Estatísticas Finais</strong><br>
                <strong>Modelo:</strong> ${eventData.model_info.model_name || 'Não especificado'}<br>
                <strong>Total de Tokens:</strong> ${eventData.model_info.tokens_used || 0}<br>
                <strong>Custo Total:</strong> $${eventData.model_info.estimated_cost?.toFixed(6) || '0.000000'}
            `;
            
            // Adiciona ao log
            this.addLogEntry('', modelInfo);
        }
    }
    
    /**
     * Exibe um erro de tarefa
     * @param {Object} eventData Dados do evento
     */
    displayError(eventData) {
        // Atualiza o status da tarefa
        if (this.elements.statusText) {
            this.elements.statusText.textContent = "Erro";
        }
        
        // Atualiza o passo atual
        if (this.elements.taskStep) {
            this.elements.taskStep.textContent = 'Ocorreu um erro durante a execução';
        }
        
        // Exibe o erro
        if (this.elements.taskResultStatus) {
            this.elements.taskResultStatus.textContent = eventData.data?.error || 'Erro não especificado';
            this.elements.taskResultStatus.style.display = 'block';
        }
        
        // Exibe mensagem de erro
        this.showError('statusError', eventData.data?.error || 'Ocorreu um erro durante a execução da tarefa');
    }
    
    /**
     * Método simplificado para criar uma nova tarefa (versão alternativa)
     * Esta versão usa fetch diretamente sem reutilizar outras funções
     */
    async createTaskSimple() {
        console.log("Método createTaskSimple iniciado");
        
        // Oculta mensagens anteriores
        document.getElementById('taskError').style.display = 'none';
        document.getElementById('taskSuccess').style.display = 'none';
        document.getElementById('taskResult').style.display = 'none';
        
        // Obtém valores dos campos diretamente
        const clientId = document.getElementById('clientId').value;
        const taskType = document.getElementById('taskType').value;
        console.log("Input - ClientID:", clientId);
        console.log("Input - TaskType:", taskType);
        
        if (!clientId) {
            document.getElementById('taskError').textContent = 'Client ID é obrigatório';
            document.getElementById('taskError').style.display = 'block';
            return;
        }
        
        // Obtém o conteúdo do campo apropriado
        let taskData = {};
        if (taskType === 'prompt') {
            const promptText = document.getElementById('promptText').value;
            if (!promptText.trim()) {
                document.getElementById('taskError').textContent = 'Prompt é obrigatório';
                document.getElementById('taskError').style.display = 'block';
                return;
            }
            taskData = {
                prompt: promptText
            };
        } else if (taskType === 'plan') {
            const planStepsText = document.getElementById('planSteps').value;
            const steps = planStepsText.split('\n').filter(step => step.trim() !== '');
            if (steps.length === 0) {
                document.getElementById('taskError').textContent = 'Pelo menos um passo do plano é obrigatório';
                document.getElementById('taskError').style.display = 'block';
                return;
            }
            taskData = {
                plan: {
                    steps: steps
                }
            };
        }
        
        console.log("TaskData preparado:", taskData);
        
        // Cria o objeto de requisição
        const requestData = {
            client_id: clientId,
            task_type: taskType,
            data: taskData
        };
        
        console.log("Enviando requisição:", JSON.stringify(requestData));
        
        try {
            // Usa o endpoint correto com prefixo /api
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            console.log("Status da resposta:", response.status);
            const data = await response.json();
            console.log("Resposta recebida:", data);
            
            if (response.ok) {
                // Mostra sucesso
                document.getElementById('taskSuccess').textContent = `Tarefa criada com sucesso! ID: ${data.task_id}`;
                document.getElementById('taskSuccess').style.display = 'block';
                
                // Mostra resultado JSON
                document.getElementById('taskResult').textContent = JSON.stringify(data, null, 2);
                document.getElementById('taskResult').style.display = 'block';
                
                // Atualiza campo de ID
                document.getElementById('taskId').value = data.task_id;
                
                if (this.elements.wsLog) {
                    this.addLogEntry(`Tarefa criada com ID: ${data.task_id}`);
                }
            } else {
                // Mostra erro
                document.getElementById('taskError').textContent = `Erro: ${data.detail || 'Erro desconhecido'}`;
                document.getElementById('taskError').style.display = 'block';
                
                if (this.elements.wsLog) {
                    this.addLogEntry(`Erro ao criar tarefa: ${data.detail || 'Erro desconhecido'}`);
                }
            }
        } catch (error) {
            console.error("Erro na requisição:", error);
            document.getElementById('taskError').textContent = `Erro ao criar tarefa: ${error.message}`;
            document.getElementById('taskError').style.display = 'block';
            
            if (this.elements.wsLog) {
                this.addLogEntry(`Erro ao criar tarefa: ${error.message}`);
            }
        }
    }
}

// Inicializa o controlador de UI quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    const ui = new UIController();
    ui.init();
}); 