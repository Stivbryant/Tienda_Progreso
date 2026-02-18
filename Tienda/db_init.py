from flask import Flask
from config import Config
from models import db, Product

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Productos demo (cambia los códigos a tus códigos reales)
        demo = [
            Product(barcode="7501031311309", name="Coca Cola 500ml", price=0.75, stock=100),
            Product(barcode="7861001240017", name="Pan Bimbo", price=1.65, stock=50),
            Product(barcode="7862104340108", name="Arroz 1kg", price=1.25, stock=80),
            Product(barcode="1234567890123", name="Galletas", price=0.50, stock=200),
        ]
        db.session.add_all(demo)
        db.session.commit()

    print("✅ BD creada y productos demo insertados.")
