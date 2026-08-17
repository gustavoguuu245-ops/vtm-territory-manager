import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.db.database import init_db, SessionLocal
from core.auth.authenticator import AuthManager
from core.models.region import Region
from core.models.territory import Territory
from core.services.territory_service import TerritoryService

def seed():
    print("🌱 Inicializando banco de dados...")
    init_db()
    
    db = SessionLocal()
    
    print("👤 Criando usuarios de demonstracao...")
    users_data = [
        ("narrador", "narrador123", "narrador", "Global", None),
        ("jogador_br", "br123", "jogador", "Brasil", "Brujah"),
        ("jogador_es", "es123", "jogador", "Espanha", "Lasombra"),
        ("jogador_fr", "fr123", "jogador", "Franca", "Toreador"),
    ]
    
    for username, password, role, region, clan in users_data:
        existing = AuthManager.get_user_by_username(db, username)
        if not existing:
            AuthManager.create_user(
                db, username, password,
                role=role, assigned_region=region, clan=clan
            )
            print(f"   ✅ Usuario criado: {username} ({role})")
        else:
            print(f"   ⚠️ {username} já existe")
    
    print("🌍 Criando regioes...")
    regions_data = [
        ("brasil", "Brasil", "pais", -14.2350, -51.9253, 4),
        ("espanha", "Espanha", "pais", 40.4637, -3.7492, 6),
        ("franca", "França", "pais", 46.2276, 2.2137, 6),
        ("rio_de_janeiro", "Rio de Janeiro", "cidade", -22.9068, -43.1729, 12),
        ("madri", "Madri", "cidade", 40.4168, -3.7038, 12),
    ]
    
    for name, display, rtype, lat, lng, zoom in regions_data:
        existing = db.query(Region).filter(Region.name == name).first()
        if not existing:
            r = Region(name=name, display_name=display, region_type=rtype,
                       center_lat=lat, center_lng=lng, zoom_level=zoom)
            db.add(r)
            print(f"   ✅ Regiao criada: {display}")
        else:
            print(f"   ⚠️ {display} já existe")
    
    db.commit()
    db.close()
    print("\n🎉 Seed concluído! Agora tente logar na página web.")

if __name__ == "__main__":
    seed()