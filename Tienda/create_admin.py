from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    u = User.query.filter_by(username="admin").first()
    if not u:
        u = User(username="admin", full_name="Administrador")
        u.set_password("admin123")
        db.session.add(u)
        db.session.commit()
        print("✅ Usuario creado: admin / admin123")
    else:
        print("ℹ️ Ya existe admin")
