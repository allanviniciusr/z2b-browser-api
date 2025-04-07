"""
Arquivo de ponte para iniciar facilmente a aplicação Z2B Browser API.
Este arquivo simplifica a inicialização para que a aplicação possa ser 
iniciada tanto com 'python main.py' quanto com 'python -m src.api.main'.
"""

if __name__ == "__main__":
    import sys
    from src.api.main import main
    
    # Executa a função main do módulo src.api.main
    sys.exit(main())
