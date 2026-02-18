from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify

from config import Config
from models import db, Product, Sale, SaleItem, Invoice, Customer, User


def money(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # ---------------- Helpers ----------------
    @app.context_processor
    def inject_store():
        return dict(
            STORE_NAME=app.config["STORE_NAME"],
            STORE_RUC=app.config["STORE_RUC"],
            STORE_ADDRESS=app.config["STORE_ADDRESS"],
            STORE_PHONE=app.config["STORE_PHONE"],
            TAX_RATE=app.config["TAX_RATE"],
        )

    def get_cart():
        return session.setdefault("cart", {})  # {product_id: qty}

    def cart_totals():
        cart = get_cart()
        items = []
        subtotal = Decimal("0.00")

        for pid_str, qty in cart.items():
            p = db.session.get(Product, int(pid_str))
            if not p:
                continue

            qty = int(qty)
            line = money(p.price) * qty
            subtotal += line
            items.append({"p": p, "qty": qty, "line": money(line)})

        tax = money(subtotal * Decimal(str(app.config["TAX_RATE"])))
        total = money(subtotal + tax)
        return items, money(subtotal), tax, total

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("welcome"))
            return fn(*args, **kwargs)
        return wrapper

    # ---------------- Auth / Welcome ----------------
    @app.route("/welcome")
    def welcome():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return render_template("welcome.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            u = User.query.filter_by(username=username, is_active=True).first()
            if not u or not u.check_password(password):
                flash("Usuario o contraseña incorrectos.", "danger")
                return redirect(url_for("login"))

            session["user_id"] = u.id
            session["username"] = u.username
            session["full_name"] = u.full_name or u.username
            flash(f"Bienvenido, {session['full_name']} ✅", "success")
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("Sesión cerrada.", "info")
        return redirect(url_for("welcome"))

    # ---------------- Dashboard ----------------
    @app.route("/")
    @login_required
    def dashboard():
        today = datetime.now().date()
        sales_today = Sale.query.filter(
            Sale.created_at >= datetime(today.year, today.month, today.day)
        ).all()
        total_today = sum([Decimal(str(s.total)) for s in sales_today], Decimal("0.00"))
        low_stock = Product.query.filter(Product.stock <= 5).order_by(Product.stock.asc()).limit(10).all()

        return render_template(
            "dashboard.html",
            sales_today=len(sales_today),
            total_today=money(total_today),
            low_stock=low_stock
        )

    # ---------------- Products ----------------
    @app.route("/products")
    @login_required
    def products():
        q = request.args.get("q", "").strip()
        if q:
            rows = Product.query.filter(
                (Product.name.ilike(f"%{q}%")) | (Product.barcode.ilike(f"%{q}%"))
            ).order_by(Product.name.asc()).all()
        else:
            rows = Product.query.order_by(Product.name.asc()).all()
        return render_template("products.html", rows=rows, q=q)

    @app.route("/products/new", methods=["GET", "POST"])
    @login_required
    def product_new():
        if request.method == "POST":
            barcode = request.form.get("barcode", "").strip()
            name = request.form.get("name", "").strip()
            price = request.form.get("price", "0").strip()
            stock = request.form.get("stock", "0").strip()

            if not barcode or not name:
                flash("Barcode y nombre son obligatorios.", "danger")
                return redirect(url_for("product_new"))

            if Product.query.filter_by(barcode=barcode).first():
                flash("Ese barcode ya existe.", "danger")
                return redirect(url_for("product_new"))

            p = Product(barcode=barcode, name=name, price=money(price), stock=int(stock))
            db.session.add(p)
            db.session.commit()
            flash("Producto creado.", "success")
            return redirect(url_for("products"))

        return render_template("product_form.html", mode="new", p=None)

    @app.route("/products/<int:pid>/edit", methods=["GET", "POST"])
    @login_required
    def product_edit(pid):
        p = Product.query.get_or_404(pid)

        if request.method == "POST":
            barcode = request.form.get("barcode", "").strip()
            name = request.form.get("name", "").strip()
            price = request.form.get("price", "0").strip()
            stock = request.form.get("stock", "0").strip()

            if not barcode or not name:
                flash("Barcode y nombre son obligatorios.", "danger")
                return redirect(url_for("product_edit", pid=pid))

            other = Product.query.filter(Product.barcode == barcode, Product.id != pid).first()
            if other:
                flash("Ese barcode ya existe en otro producto.", "danger")
                return redirect(url_for("product_edit", pid=pid))

            p.barcode = barcode
            p.name = name
            p.price = money(price)
            p.stock = int(stock)
            db.session.commit()

            flash("Producto actualizado.", "success")
            return redirect(url_for("products"))

        return render_template("product_form.html", mode="edit", p=p)

    # ---------------- POS ----------------
    @app.route("/pos")
    @login_required
    def pos():
        items, subtotal, tax, total = cart_totals()
        return render_template("pos.html", items=items, subtotal=subtotal, tax=tax, total=total)

    @app.route("/products/search")
    @login_required
    def products_search():
        q = request.args.get("q", "").strip()
        if not q or len(q) < 2:
            return jsonify(results=[])

        rows = Product.query.filter(
            (Product.name.ilike(f"%{q}%")) | (Product.barcode.ilike(f"%{q}%"))
        ).order_by(Product.name.asc()).limit(10).all()

        return jsonify(results=[
            {"id": p.id, "barcode": p.barcode, "name": p.name, "price": float(p.price), "stock": p.stock}
            for p in rows
        ])

    @app.route("/customers/by_doc")
    @login_required
    def customer_by_doc():
        doc = request.args.get("doc", "").strip()
        if not doc or len(doc) < 5:
            return jsonify(found=False)

        c = Customer.query.filter_by(doc_id=doc).first()
        if not c:
            return jsonify(found=False)

        return jsonify(
            found=True,
            customer={
                "doc_id": c.doc_id,
                "name": c.name,
                "phone": c.phone or "",
                "address": c.address or "",
                "email": c.email or "",
            }
        )

    @app.route("/cart/clear", methods=["POST"])
    @login_required
    def cart_clear():
        session["cart"] = {}
        flash("Carrito limpiado.", "info")
        return redirect(url_for("pos"))

    @app.route("/cancel", methods=["POST"])
    @login_required
    def cancel_sale():
        session["cart"] = {}
        flash("Venta cancelada.", "info")
        return redirect(url_for("pos"))

    @app.route("/cart/add_barcode", methods=["POST"])
    @login_required
    def cart_add_barcode():
        barcode = request.form.get("barcode", "").strip()
        if not barcode:
            return redirect(url_for("pos"))

        p = Product.query.filter_by(barcode=barcode).first()
        if not p:
            flash(f"No existe producto con barcode: {barcode}", "danger")
            return redirect(url_for("pos"))

        cart = get_cart()
        pid = str(p.id)
        cart[pid] = int(cart.get(pid, 0)) + 1
        session["cart"] = cart
        return redirect(url_for("pos"))

    @app.route("/cart/add_product", methods=["POST"])
    @login_required
    def cart_add_product():
        pid = request.form.get("product_id", "").strip()
        if not pid.isdigit():
            return redirect(url_for("pos"))

        p = Product.query.get(int(pid))
        if not p:
            flash("Producto no encontrado.", "danger")
            return redirect(url_for("pos"))

        cart = get_cart()
        sid = str(p.id)
        cart[sid] = int(cart.get(sid, 0)) + 1
        session["cart"] = cart
        return redirect(url_for("pos"))

    @app.route("/cart/update", methods=["POST"])
    @login_required
    def cart_update():
        cart = get_cart()
        for key, val in request.form.items():
            if not key.startswith("qty_"):
                continue

            pid = key.replace("qty_", "")
            try:
                qty = int(val)
            except:
                qty = 1

            if qty <= 0:
                cart.pop(pid, None)
            else:
                cart[pid] = qty

        session["cart"] = cart
        return redirect(url_for("pos"))

    @app.route("/checkout", methods=["POST"])
    @login_required
    def checkout():
        customer_name = request.form.get("customer_name", "").strip() or None
        customer_id = request.form.get("customer_id", "").strip() or None
        customer_phone = request.form.get("customer_phone", "").strip() or None
        customer_address = request.form.get("customer_address", "").strip() or None
        customer_email = request.form.get("customer_email", "").strip() or None

        payment_method = request.form.get("payment_method", "EFECTIVO").strip()

        items, subtotal, tax, total = cart_totals()
        if not items:
            flash("El carrito está vacío.", "danger")
            return redirect(url_for("pos"))

        for it in items:
            p = it["p"]
            if p.stock < it["qty"]:
                flash(f"Stock insuficiente para {p.name}. Disponible: {p.stock}", "danger")
                return redirect(url_for("pos"))

        # Upsert Customer
        customer_fk = None
        if customer_id:
            c = Customer.query.filter_by(doc_id=customer_id).first()
            if c:
                if customer_name:    c.name = customer_name
                if customer_phone:   c.phone = customer_phone
                if customer_address: c.address = customer_address
                if customer_email:   c.email = customer_email
                customer_fk = c.id
            else:
                if customer_name:
                    c = Customer(
                        doc_id=customer_id,
                        name=customer_name,
                        phone=customer_phone,
                        address=customer_address,
                        email=customer_email
                    )
                    db.session.add(c)
                    db.session.flush()
                    customer_fk = c.id

        sale = Sale(
            customer_fk=customer_fk,
            customer_name=customer_name,
            customer_id=customer_id,
            customer_phone=customer_phone,
            customer_address=customer_address,
            customer_email=customer_email,
            payment_method=payment_method,
            subtotal=subtotal,
            tax=tax,
            total=total
        )
        db.session.add(sale)
        db.session.flush()

        for it in items:
            p = it["p"]
            qty = it["qty"]
            unit = money(p.price)
            line_total = money(unit * qty)

            db.session.add(SaleItem(
                sale_id=sale.id,
                product_id=p.id,
                product_name=p.name,
                barcode=p.barcode,
                qty=qty,
                unit_price=unit,
                line_total=line_total,
            ))
            p.stock -= qty

        inv_number = f"{datetime.now():%Y%m%d}-{sale.id:06d}"
        db.session.add(Invoice(sale_id=sale.id, invoice_number=inv_number))

        db.session.commit()

        session["cart"] = {}
        flash("✅ Venta realizada. Factura lista para imprimir.", "success")
        return redirect(url_for("invoice_view", sale_id=sale.id))

    @app.route("/invoice/<int:sale_id>")
    @login_required
    def invoice_view(sale_id):
        sale = Sale.query.get_or_404(sale_id)
        if not sale.invoice:
            abort(404)
        return render_template("invoice.html", sale=sale)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
