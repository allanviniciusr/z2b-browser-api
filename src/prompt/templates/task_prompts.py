"""
Implementação de prompts específicos para diferentes tipos de tarefas.

Este módulo contém templates de prompts para tarefas específicas
que os agentes podem executar, como navegação, extração de dados,
preenchimento de formulários, etc.
"""

# Template para tarefa de navegação
NAVIGATION_TASK_TEMPLATE = """
Navegue para a URL: {{url}}

Depois de carregar a página:
1. Verifique se a página carregou corretamente
2. Analise o conteúdo principal
3. Identifique os elementos de navegação principais

{% if verification_elements %}
Elementos para verificar carregamento correto:
{% for element in verification_elements %}
- {{element.description}}: {{element.selector}}
{% endfor %}
{% endif %}

{% if additional_instructions %}
Instruções adicionais:
{{additional_instructions}}
{% endif %}
"""

# Template para tarefa de extração de dados
EXTRACTION_TASK_TEMPLATE = """
Extraia as seguintes informações da página atual:

{% for field in fields %}
- {{field.name}}: {{field.description}}
{% endfor %}

{% if output_format == "json" %}
Retorne os dados extraídos em formato JSON estruturado.
{% elif output_format == "csv" %}
Retorne os dados extraídos em formato CSV.
{% else %}
Retorne os dados extraídos de forma organizada.
{% endif %}

{% if pagination %}
Esta tarefa envolve paginação:
- Extraia dados de cada página
- Navegue para a próxima página usando: {{pagination.selector}}
- Continue até {{pagination.max_pages}} páginas ou até não haver mais páginas
{% endif %}

{% if additional_instructions %}
Instruções adicionais:
{{additional_instructions}}
{% endif %}
"""

# Template para tarefa de preenchimento de formulário
FORM_TASK_TEMPLATE = """
Preencha o formulário na página atual com os seguintes dados:

{% for field in form_data %}
- Campo "{{field.name}}" {% if field.selector %}({{field.selector}}){% endif %}: {{field.value}}
{% endfor %}

{% if submission_action %}
Após preencher todos os campos, {{submission_action}}.
{% else %}
Após preencher todos os campos, clique no botão de submissão do formulário.
{% endif %}

{% if validation %}
Validação pós-submissão:
- Verifique se há mensagens de erro após a submissão
- Confirme se a submissão foi bem-sucedida procurando por: {{validation.success_indicator}}
{% endif %}

{% if additional_instructions %}
Instruções adicionais:
{{additional_instructions}}
{% endif %}
"""

# Template para tarefa de login
LOGIN_TASK_TEMPLATE = """
Realize login no site {{website_name}} usando as seguintes credenciais:

- Nome de usuário/Email: {{username}}
- Senha: {{password}}

Passos:
1. Navegue para a página de login: {{login_url}}
2. Localize os campos de usuário e senha
3. Preencha as credenciais fornecidas
4. Clique no botão de login
5. Verifique se o login foi bem-sucedido

{% if verification_method %}
Verifique o sucesso do login através de: {{verification_method}}
{% endif %}

{% if two_factor %}
Esta conta possui autenticação de dois fatores:
- Aguarde pelo código de verificação
- Insira o código quando solicitado
{% endif %}

{% if additional_instructions %}
Instruções adicionais:
{{additional_instructions}}
{% endif %}
"""

# Template para tarefa de pesquisa
SEARCH_TASK_TEMPLATE = """
Realize uma pesquisa por "{{search_term}}" no site atual.

Passos:
1. Localize o campo de pesquisa na página
{% if search_selector %}(Use o seletor: {{search_selector}}){% endif %}
2. Insira o termo de pesquisa: {{search_term}}
3. Submeta a pesquisa (geralmente pressionando Enter ou clicando em um botão)
4. Aguarde os resultados da pesquisa carregarem

{% if results_parsing %}
Nos resultados da pesquisa:
{% for action in results_parsing.actions %}
- {{action}}
{% endfor %}
{% endif %}

{% if additional_instructions %}
Instruções adicionais:
{{additional_instructions}}
{% endif %}
"""

# Template para tarefa de captura de screenshot
SCREENSHOT_TASK_TEMPLATE = """
Capture screenshots dos seguintes elementos na página atual:

{% for element in elements %}
- {{element.description}}
{% if element.selector %}(Use o seletor: {{element.selector}}){% endif %}
{% endfor %}

Para cada elemento:
1. Localize o elemento na página
2. Verifique se ele está visível e carregado corretamente
3. Capture um screenshot do elemento
4. Dê um nome descritivo para o arquivo de screenshot

{% if viewport_adjustments %}
Ajustes de viewport:
{% for adjustment in viewport_adjustments %}
- {{adjustment}}
{% endfor %}
{% endif %}

{% if additional_instructions %}
Instruções adicionais:
{{additional_instructions}}
{% endif %}
"""

# Dicionário mapeando tipos de tarefas para seus templates
TASK_TEMPLATES = {
    "navigation": NAVIGATION_TASK_TEMPLATE,
    "extraction": EXTRACTION_TASK_TEMPLATE,
    "form": FORM_TASK_TEMPLATE,
    "login": LOGIN_TASK_TEMPLATE,
    "search": SEARCH_TASK_TEMPLATE,
    "screenshot": SCREENSHOT_TASK_TEMPLATE,
} 