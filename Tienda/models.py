from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)

    # Cédula/RUC
    doc_id = db.Column(db.String(20), unique=True, nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Sale(db.Model):
    __tablename__ = "sales"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relación opcional al cliente
    customer_fk = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    customer = db.relationship("Customer", lazy=True)

    # Snapshot en la venta (para que la factura no cambie si editas el cliente luego)
    customer_name = db.Column(db.String(120), nullable=True)
    customer_id = db.Column(db.String(20), nullable=True)      # cédula/RUC
    customer_phone = db.Column(db.String(30), nullable=True)
    customer_address = db.Column(db.String(200), nullable=True)
    customer_email = db.Column(db.String(120), nullable=True)

    payment_method = db.Column(db.String(30), nullable=False, default="EFECTIVO")

    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    items = db.relationship("SaleItem", backref="sale", lazy=True, cascade="all, delete-orphan")
    invoice = db.relationship("Invoice", backref="sale", uselist=False, cascade="all, delete-orphan")


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    barcode = db.Column(db.String(64), nullable=False)

    qty = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False, unique=True)
    invoice_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, plain: str) -> None:
        self.password_hash = generate_password_hash(plain)

    def check_password(self, plain: str) -> bool:
        return check_password_hash(self.password_hash, plain)