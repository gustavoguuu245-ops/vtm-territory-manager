#!/usr/bin/env python3
import subprocess
import sys
import webbrowser
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def main():
    print("🧛 VTM Territory Manager - Inicializador")
    print("=" * 50)
    print("\n📦 Verificando e instalando dependências...")
    
    try:
        import streamlit
        import folium
        import sqlalchemy
        print("   ✅ Dependências já instaladas")
    except ImportError as e:
        print(f"   ⚠️ Pacote faltando: {e}")
        print("   📥 Instalando dependências...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("   ✅ Dependências instaladas!")
    
    # BANCO 
    print("\n🌱 Populando banco de dados...")
    seed_script = BASE_DIR / "scripts" / "seed.py"
    if seed_script.exists():
        try:
            subprocess.run([sys.executable, str(seed_script)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️ Erro no seed: {e}")
            print("   Continuando mesmo assim...")
    else:
        print("   ⚠️ Script scripts/seed.py não encontrado. Pulando seed.")
    
    #  ABRE O NAVEGADOR 
    print("\n🌐 Abrindo navegador em http://localhost:8501...")
    time.sleep(2) 
    webbrowser.open("http://localhost:8501")
    
    # INICIA 
    print("\n🚀 Iniciando Streamlit...")
    main_app = BASE_DIR / "app" / "main.py"
    if not main_app.exists():
        print(f"   ❌ Erro: Arquivo principal não encontrado em {main_app}")
        sys.exit(1)
    
    print(f"   🌐 Acesse: http://localhost:8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(main_app),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true"
    ])

if __name__ == "__main__":
    main()