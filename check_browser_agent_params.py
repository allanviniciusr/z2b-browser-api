import inspect
from browser_use import Agent as BrowserAgent

# Obter assinatura do construtor
signature = inspect.signature(BrowserAgent.__init__)
print("Parâmetros aceitos pelo BrowserAgent:")
for param_name, param in signature.parameters.items():
    if param_name != "self":
        print(f"- {param_name}: {param.default if param.default != inspect.Parameter.empty else 'required'}")
