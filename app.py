"""
ERP System - Main Flask Application
=====================================
This is the entry point for our inventory + manufacturing ERP system.
Flask is a lightweight Python web framework - it handles URL routing and
sends HTML pages back to the browser.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime, date
from functools import wraps

# Create the Flask application
app = Flask(__name__)
# Secret key is needed for sessions (login system)
app.secret_key = os.environ.get("SECRET_KEY", "erp_secret_key_2024")

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

def get_db():
    """Connect to the SQLite database. Creates the file if it doesn't exist."""
    db = sqlite3.connect("erp.db")
    db.row_factory = sqlite3.Row  # This lets us access columns by name (row["name"])
    return db

def init_db():
    """Create all tables and insert sample data on first run."""
    db = get_db()
    cursor = db.cursor()

    # ── Materials table: stores raw materials like copper, plastic ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT DEFAULT 'units',
            low_stock_threshold REAL DEFAULT 50
        )
    """)

    # ── Products table: finished goods that get manufactured and sold ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            stock INTEGER NOT NULL DEFAULT 0,
            selling_price REAL DEFAULT 0,
            cost_price REAL DEFAULT 0
        )
    """)

    # ── Bill of Materials (BOM): defines ingredients for each product ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            quantity_required REAL NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
            UNIQUE(product_id, material_id)
        )
    """)

    # ── Production logs: records every manufacturing run ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ── Sales records: every sale transaction ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL DEFAULT 0,
            total_amount REAL DEFAULT 0,
            date TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ── Users table for login system ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'staff'
        )
    """)

    # Insert default admin user (password: admin123)
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('admin', 'admin123', 'admin')
    """)

    # ── Insert sample data for testing ──
    sample_materials = [
        ("Copper Wire", 500, "kg", 50),
        ("Plastic Casing", 300, "units", 30),
        ("Steel Rod", 200, "kg", 20),
        ("Circuit Board", 150, "units", 15),
        ("Rubber Seal", 400, "units", 40),
        ("Aluminum Sheet", 80, "kg", 25),  
        ("LED Chip", 45, "units", 50),      
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO materials (name, quantity, unit, low_stock_threshold)
        VALUES (?, ?, ?, ?)
    """, sample_materials)

    sample_products = [
        ("Electric Motor", 20, 2500.0, 1800.0),
        ("Control Panel", 15, 5000.0, 3500.0),
        ("Cable Assembly", 30, 800.0, 500.0),
        ("Switch Box", 10, 1200.0, 850.0),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO products (name, stock, selling_price, cost_price)
        VALUES (?, ?, ?, ?)
    """, sample_products)

    db.commit()

    # Add BOM entries (after products & materials exist)
    bom_entries = [
        # Electric Motor uses: 5kg Copper, 2 Plastic Casings, 3kg Steel, 1 Circuit Board
        ("Electric Motor", "Copper Wire", 5.0),
        ("Electric Motor", "Plastic Casing", 2.0),
        ("Electric Motor", "Steel Rod", 3.0),
        ("Electric Motor", "Circuit Board", 1.0),
        # Control Panel uses: 2kg Copper, 4 Plastic Casings, 2 Circuit Boards
        ("Control Panel", "Copper Wire", 2.0),
        ("Control Panel", "Plastic Casing", 4.0),
        ("Control Panel", "Circuit Board", 2.0),
        # Cable Assembly uses: 10kg Copper, 5 Rubber Seals
        ("Cable Assembly", "Copper Wire", 10.0),
        ("Cable Assembly", "Rubber Seal", 5.0),
        # Switch Box uses: 1kg Steel, 2 Plastic Casings, 10 LED Chips
        ("Switch Box", "Steel Rod", 1.0),
        ("Switch Box", "Plastic Casing", 2.0),
        ("Switch Box", "LED Chip", 10.0),
    ]
    for prod_name, mat_name, qty in bom_entries:
        cursor.execute("""
            INSERT OR IGNORE INTO bom (product_id, material_id, quantity_required)
            SELECT p.id, m.id, ?
            FROM products p, materials m
            WHERE p.name = ? AND m.name = ?
        """, (qty, prod_name, mat_name))

    db.commit()
    db.close()

# ─────────────────────────────────────────────
# LOGIN / AUTHENTICATION
# ─────────────────────────────────────────────

def login_required(f):
    """Decorator: redirects to login page if user is not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page - checks username and password."""
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        db.close()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()

    # Count total materials and their quantities
    materials = db.execute("SELECT * FROM materials").fetchall()
    total_materials = len(materials)
    low_stock = [m for m in materials if m["quantity"] <= m["low_stock_threshold"]]

    # Product stats
    products = db.execute("SELECT * FROM products").fetchall()
    total_products = len(products)
    total_stock = sum(p["stock"] for p in products)

    # Sales summary (last 30 days)
    sales = db.execute("""
        SELECT s.*, p.name as product_name
        FROM sales s JOIN products p ON s.product_id = p.id
        ORDER BY s.date DESC LIMIT 10
    """).fetchall()

    total_revenue = db.execute(
        "SELECT COALESCE(SUM(total_amount), 0) as rev FROM sales"
    ).fetchone()["rev"]

    total_sales_qty = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) as qty FROM sales"
    ).fetchone()["qty"]

    # Production summary
    total_produced = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) as qty FROM production"
    ).fetchone()["qty"]

    db.close()

    return render_template("dashboard.html",
        materials=materials,
        total_materials=total_materials,
        low_stock=low_stock,
        products=products,
        total_products=total_products,
        total_stock=total_stock,
        recent_sales=sales,
        total_revenue=total_revenue,
        total_sales_qty=total_sales_qty,
        total_produced=total_produced,
    )

# ─────────────────────────────────────────────
# MATERIALS MODULE
# ─────────────────────────────────────────────

@app.route("/materials")
@login_required
def materials():
    db = get_db()
    mats = db.execute("SELECT * FROM materials ORDER BY name").fetchall()
    db.close()
    return render_template("materials.html", materials=mats)

@app.route("/materials/add", methods=["POST"])
@login_required
def add_material():
    name = request.form["name"].strip()
    qty = float(request.form["quantity"])
    unit = request.form.get("unit", "units")
    threshold = float(request.form.get("threshold", 50))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO materials (name, quantity, unit, low_stock_threshold) VALUES (?,?,?,?)",
            (name, qty, unit, threshold)
        )
        db.commit()
        flash(f"Material '{name}' added successfully!", "success")
    except sqlite3.IntegrityError:
        flash(f"Material '{name}' already exists.", "error")
    db.close()
    return redirect(url_for("materials"))

@app.route("/materials/update/<int:id>", methods=["POST"])
@login_required
def update_material(id):
    qty = float(request.form["quantity"])
    unit = request.form.get("unit", "units")
    threshold = float(request.form.get("threshold", 50))

    db = get_db()
    db.execute(
        "UPDATE materials SET quantity=?, unit=?, low_stock_threshold=? WHERE id=?",
        (qty, unit, threshold, id)
    )
    db.commit()
    db.close()
    flash("Material updated!", "success")
    return redirect(url_for("materials"))

@app.route("/materials/delete/<int:id>")
@login_required
def delete_material(id):
    db = get_db()
    db.execute("DELETE FROM materials WHERE id=?", (id,))
    db.commit()
    db.close()
    flash("Material deleted.", "info")
    return redirect(url_for("materials"))

# ─────────────────────────────────────────────
# PRODUCTS MODULE
# ─────────────────────────────────────────────

@app.route("/products")
@login_required
def products():
    db = get_db()
    prods = db.execute("SELECT * FROM products ORDER BY name").fetchall()
    db.close()
    return render_template("products.html", products=prods)

@app.route("/products/add", methods=["POST"])
@login_required
def add_product():
    name = request.form["name"].strip()
    stock = int(request.form.get("stock", 0))
    sell_price = float(request.form.get("selling_price", 0))
    cost_price = float(request.form.get("cost_price", 0))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO products (name, stock, selling_price, cost_price) VALUES (?,?,?,?)",
            (name, stock, sell_price, cost_price)
        )
        db.commit()
        flash(f"Product '{name}' added!", "success")
    except sqlite3.IntegrityError:
        flash(f"Product '{name}' already exists.", "error")
    db.close()
    return redirect(url_for("products"))

@app.route("/products/update/<int:id>", methods=["POST"])
@login_required
def update_product(id):
    sell_price = float(request.form.get("selling_price", 0))
    cost_price = float(request.form.get("cost_price", 0))

    db = get_db()
    db.execute(
        "UPDATE products SET selling_price=?, cost_price=? WHERE id=?",
        (sell_price, cost_price, id)
    )
    db.commit()
    db.close()
    flash("Product updated!", "success")
    return redirect(url_for("products"))

@app.route("/products/delete/<int:id>")
@login_required
def delete_product(id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (id,))
    db.commit()
    db.close()
    flash("Product deleted.", "info")
    return redirect(url_for("products"))

# ─────────────────────────────────────────────
# BOM MODULE
# ─────────────────────────────────────────────

@app.route("/bom")
@login_required
def bom():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY name").fetchall()
    materials = db.execute("SELECT * FROM materials ORDER BY name").fetchall()

    # Get BOM entries with product and material names
    bom_entries = db.execute("""
        SELECT b.id, p.name as product_name, m.name as material_name,
               b.quantity_required, m.unit, b.product_id, b.material_id
        FROM bom b
        JOIN products p ON b.product_id = p.id
        JOIN materials m ON b.material_id = m.id
        ORDER BY p.name, m.name
    """).fetchall()

    db.close()
    return render_template("bom.html", bom_entries=bom_entries,
                           products=products, materials=materials)

@app.route("/bom/add", methods=["POST"])
@login_required
def add_bom():
    product_id = int(request.form["product_id"])
    material_id = int(request.form["material_id"])
    qty = float(request.form["quantity_required"])

    db = get_db()
    try:
        db.execute(
            "INSERT INTO bom (product_id, material_id, quantity_required) VALUES (?,?,?)",
            (product_id, material_id, qty)
        )
        db.commit()
        flash("BOM entry added!", "success")
    except sqlite3.IntegrityError:
        flash("This material is already in the BOM for this product. Delete it first to update.", "error")
    db.close()
    return redirect(url_for("bom"))

@app.route("/bom/delete/<int:id>")
@login_required
def delete_bom(id):
    db = get_db()
    db.execute("DELETE FROM bom WHERE id=?", (id,))
    db.commit()
    db.close()
    flash("BOM entry removed.", "info")
    return redirect(url_for("bom"))

# ─────────────────────────────────────────────
# MANUFACTURING MODULE
# ─────────────────────────────────────────────

@app.route("/manufacturing")
@login_required
def manufacturing():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY name").fetchall()

    # Get production history
    history = db.execute("""
        SELECT pr.*, p.name as product_name
        FROM production pr JOIN products p ON pr.product_id = p.id
        ORDER BY pr.date DESC LIMIT 20
    """).fetchall()

    db.close()
    return render_template("manufacturing.html", products=products, history=history)

@app.route("/manufacturing/check", methods=["POST"])
@login_required
def check_manufacturing():
    """AJAX endpoint: checks if enough materials exist before manufacturing."""
    product_id = int(request.form["product_id"])
    quantity = int(request.form["quantity"])

    db = get_db()
    bom = db.execute("""
        SELECT b.quantity_required, m.name, m.quantity, m.unit
        FROM bom b JOIN materials m ON b.material_id = m.id
        WHERE b.product_id = ?
    """, (product_id,)).fetchall()

    if not bom:
        db.close()
        return jsonify({"ok": False, "message": "No BOM defined for this product."})

    shortages = []
    for item in bom:
        needed = item["quantity_required"] * quantity
        available = item["quantity"]
        if available < needed:
            shortages.append({
                "material": item["name"],
                "needed": needed,
                "available": available,
                "unit": item["unit"]
            })

    db.close()

    if shortages:
        return jsonify({"ok": False, "shortages": shortages})
    return jsonify({"ok": True, "message": "All materials available. Ready to manufacture!"})

@app.route("/manufacturing/produce", methods=["POST"])
@login_required
def produce():
    """
    Core manufacturing logic:
    1. Check BOM exists
    2. Verify all materials are available
    3. Deduct materials
    4. Increase product stock
    5. Log the production run
    """
    product_id = int(request.form["product_id"])
    quantity = int(request.form["quantity"])

    db = get_db()

    # Step 1: Get BOM
    bom = db.execute("""
        SELECT b.material_id, b.quantity_required, m.name, m.quantity
        FROM bom b JOIN materials m ON b.material_id = m.id
        WHERE b.product_id = ?
    """, (product_id,)).fetchall()

    if not bom:
        flash("Cannot manufacture: No Bill of Materials defined for this product.", "error")
        db.close()
        return redirect(url_for("manufacturing"))

    # Step 2: Check availability
    for item in bom:
        needed = item["quantity_required"] * quantity
        if item["quantity"] < needed:
            flash(f"Insufficient stock: {item['name']} needs {needed} but only {item['quantity']} available.", "error")
            db.close()
            return redirect(url_for("manufacturing"))

    # Step 3: Deduct materials
    for item in bom:
        needed = item["quantity_required"] * quantity
        db.execute(
            "UPDATE materials SET quantity = quantity - ? WHERE id = ?",
            (needed, item["material_id"])
        )

    # Step 4: Increase product stock
    db.execute(
        "UPDATE products SET stock = stock + ? WHERE id = ?",
        (quantity, product_id)
    )

    # Step 5: Log production
    db.execute(
        "INSERT INTO production (product_id, quantity, date) VALUES (?,?,?)",
        (product_id, quantity, date.today().isoformat())
    )

    db.commit()
    db.close()

    product_name = db.execute if False else ""
    flash(f"Successfully manufactured {quantity} units! Stock updated.", "success")
    return redirect(url_for("manufacturing"))

# ─────────────────────────────────────────────
# SALES MODULE
# ─────────────────────────────────────────────

@app.route("/sales")
@login_required
def sales():
    db = get_db()
    products = db.execute("SELECT * FROM products WHERE stock > 0 ORDER BY name").fetchall()
    all_products = db.execute("SELECT * FROM products ORDER BY name").fetchall()

    # Sales history
    history = db.execute("""
        SELECT s.*, p.name as product_name
        FROM sales s JOIN products p ON s.product_id = p.id
        ORDER BY s.date DESC
    """).fetchall()

    total_revenue = sum(s["total_amount"] for s in history)

    db.close()
    return render_template("sales.html", products=products,
                           all_products=all_products,
                           history=history, total_revenue=total_revenue)

@app.route("/sales/sell", methods=["POST"])
@login_required
def sell():
    """
    Sales logic:
    1. Check product stock is sufficient
    2. Deduct from product stock
    3. Record the sale with revenue
    """
    product_id = int(request.form["product_id"])
    quantity = int(request.form["quantity"])

    db = get_db()

    # Check stock
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        db.close()
        return redirect(url_for("sales"))

    if product["stock"] < quantity:
        flash(f"Insufficient stock! Only {product['stock']} units available.", "error")
        db.close()
        return redirect(url_for("sales"))

    unit_price = product["selling_price"]
    total = unit_price * quantity

    # Deduct stock
    db.execute(
        "UPDATE products SET stock = stock - ? WHERE id=?",
        (quantity, product_id)
    )

    # Record sale
    db.execute(
        "INSERT INTO sales (product_id, quantity, unit_price, total_amount, date) VALUES (?,?,?,?,?)",
        (product_id, quantity, unit_price, total, date.today().isoformat())
    )

    db.commit()
    db.close()

    flash(f"Sale recorded! {quantity} × {product['name']} = ₹{total:,.2f}", "success")
    return redirect(url_for("sales"))

# ─────────────────────────────────────────────
# REPORTS / PROFIT
# ─────────────────────────────────────────────

@app.route("/reports")
@login_required
def reports():
    db = get_db()

    # Revenue vs cost per product
    product_profit = db.execute("""
        SELECT p.name,
               COALESCE(SUM(s.quantity), 0) as total_sold,
               COALESCE(SUM(s.total_amount), 0) as revenue,
               COALESCE(SUM(s.quantity * p.cost_price), 0) as cost,
               COALESCE(SUM(s.total_amount) - SUM(s.quantity * p.cost_price), 0) as profit
        FROM products p
        LEFT JOIN sales s ON p.id = s.product_id
        GROUP BY p.id
        ORDER BY profit DESC
    """).fetchall()

    total_revenue = sum(r["revenue"] for r in product_profit)
    total_cost = sum(r["cost"] for r in product_profit)
    total_profit = total_revenue - total_cost

    db.close()
    return render_template("reports.html",
                           product_profit=product_profit,
                           total_revenue=total_revenue,
                           total_cost=total_cost,
                           total_profit=total_profit)

# ─────────────────────────────────────────────
# RUN THE APP
# ─────────────────────────────────────────────

init_db()
if __name__ == "__main__":
    print("=" * 50)
    print("  ERP System Running!")
    print("  Open: http://127.0.0.1:5000")
    print("  Login: admin / admin123")
    print("=" * 50)
    app.run(debug=True)
