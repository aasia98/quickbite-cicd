
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ==========================================
# FLASK APPLICATION CONFIGURATION
# ==========================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "quickbite-local-development-key"
)

# Demo admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("iba@2026")


# ==========================================
# FOOD MENU - 12 ITEMS
# ==========================================

menu = [
    {"id": 1, "name": "Chicken Burger", "price": 650, "image": "burger.jpg"},
    {"id": 2, "name": "Chicken Pizza", "price": 1200, "image": "pizza.jpg"},
    {"id": 3, "name": "French Fries", "price": 300, "image": "fries.jpg"},
    {"id": 4, "name": "Chicken Biryani", "price": 450, "image": "biryani.jpg"},
    {"id": 5, "name": "Chicken Karahi", "price": 1600, "image": "karahi.jpg"},
    {"id": 6, "name": "Chicken Tikka", "price": 550, "image": "tikka.jpg"},
    {"id": 7, "name": "Beef Nihari", "price": 750, "image": "nihari.jpg"},
    {"id": 8, "name": "Chicken Pulao", "price": 400, "image": "pulao.jpg"},
    {"id": 9, "name": "Cold Drink", "price": 150, "image": "drink.jpg"},
    {"id": 10, "name": "Chocolate Cake", "price": 500, "image": "cake.jpg"},
    {"id": 11, "name": "Raita", "price": 100, "image": "raita.jpg"},
    {"id": 12, "name": "Naan", "price": 80, "image": "naan.jpg"}
]


# ==========================================
# DATABASE CONNECTION
# ==========================================

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "quickbite.db"
)


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# HOMEPAGE
# ==========================================

@app.route("/")
def home():
    cart = session.get("cart", {})
    cart_count = sum(cart.values())

    return render_template(
        "index.html",
        menu=menu,
        cart_count=cart_count
    )


# ==========================================
# ADD TO CART
# ==========================================

@app.route("/add-to-cart/<int:item_id>", methods=["POST"])
def add_to_cart(item_id):

    item = next(
        (food for food in menu if food["id"] == item_id),
        None
    )

    if item is None:
        return "Food item not found", 404

    cart = session.get("cart", {})
    key = str(item_id)

    cart[key] = cart.get(key, 0) + 1

    session["cart"] = cart

    return redirect(url_for("home"))


# ==========================================
# VIEW SHOPPING CART
# ==========================================

@app.route("/cart")
def view_cart():

    cart = session.get("cart", {})
    cart_items = []
    total = 0

    for item_id, quantity in cart.items():

        item = next(
            (food for food in menu if food["id"] == int(item_id)),
            None
        )

        if item:
            subtotal = item["price"] * quantity
            total += subtotal

            cart_items.append({
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "image": item["image"],
                "quantity": quantity,
                "subtotal": subtotal
            })

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )


# ==========================================
# REMOVE ITEM FROM CART
# ==========================================

@app.route("/remove-from-cart/<int:item_id>", methods=["POST"])
def remove_from_cart(item_id):

    cart = session.get("cart", {})

    cart.pop(str(item_id), None)

    session["cart"] = cart

    return redirect(url_for("view_cart"))


# ==========================================
# CLEAR SHOPPING CART
# ==========================================

@app.route("/clear-cart", methods=["POST"])
def clear_cart():

    session.pop("cart", None)

    return redirect(url_for("view_cart"))


# ==========================================
# CHECKOUT AND PLACE ORDER
# ==========================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart = session.get("cart", {})

    if not cart:
        return redirect(url_for("view_cart"))

    cart_items = []
    total = 0

    for item_id, quantity in cart.items():

        item = next(
            (food for food in menu if food["id"] == int(item_id)),
            None
        )

        if item:
            subtotal = item["price"] * quantity
            total += subtotal

            cart_items.append({
                "name": item["name"],
                "price": item["price"],
                "quantity": quantity,
                "subtotal": subtotal
            })

    if not cart_items:
        return redirect(url_for("view_cart"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not phone or not address:

            return render_template(
                "checkout.html",
                cart_items=cart_items,
                total=total,
                error="Please fill in all fields."
            )

        conn = get_db_connection()

        try:
            cursor = conn.execute("""
                INSERT INTO orders
                (
                    customer_name,
                    phone,
                    address,
                    total,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                phone,
                address,
                total,
                "Pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            order_id = cursor.lastrowid

            for item in cart_items:

                conn.execute("""
                    INSERT INTO order_items
                    (
                        order_id,
                        food_name,
                        price,
                        quantity
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    order_id,
                    item["name"],
                    item["price"],
                    item["quantity"]
                ))

            conn.commit()

        except sqlite3.Error:
            conn.rollback()
            return "Unable to place order. Please try again.", 500

        finally:
            conn.close()

        session.pop("cart", None)

        return redirect(
            url_for(
                "order_confirmation",
                order_id=order_id
            )
        )

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )


# ==========================================
# ORDER CONFIRMATION
# ==========================================

@app.route("/order-confirmation/<int:order_id>")
def order_confirmation(order_id):

    conn = get_db_connection()

    order = conn.execute("""
        SELECT *
        FROM orders
        WHERE id = ?
    """, (order_id,)).fetchone()

    conn.close()

    if order is None:
        return "Order not found", 404

    return render_template(
        "confirmation.html",
        order=order
    )


# ==========================================
# CUSTOMER ORDER TRACKING
# TRACK USING PHONE NUMBER ONLY
# ==========================================

@app.route("/track-order", methods=["GET", "POST"])
def track_order():

    orders = []
    error = None

    if request.method == "POST":

        phone = request.form.get("phone", "").strip()

        if not phone:
            error = "Please enter your phone number."

        else:
            conn = get_db_connection()

            orders = conn.execute("""
                SELECT
                    id,
                    customer_name,
                    total,
                    status,
                    created_at
                FROM orders
                WHERE phone = ?
                ORDER BY id DESC
            """, (phone,)).fetchall()

            conn.close()

            if not orders:
                error = "No orders found for this phone number."

    return render_template(
        "track.html",
        orders=orders,
        error=error
    )


# ==========================================
# ADMIN AUTHENTICATION DECORATOR
# ==========================================

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return f(*args, **kwargs)

    return decorated_function


# ==========================================
# ADMIN LOGIN
# ==========================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and check_password_hash(
                ADMIN_PASSWORD_HASH,
                password
            )
        ):

            session.clear()
            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        else:
            error = "Invalid username or password."

    return render_template(
        "admin_login.html",
        error=error
    )


# ==========================================
# ADMIN LOGOUT
# ==========================================

@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():

    session.clear()

    return redirect(url_for("admin_login"))


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = get_db_connection()

    orders = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """).fetchall()

    order_items = conn.execute("""
        SELECT *
        FROM order_items
        ORDER BY order_id
    """).fetchall()

    conn.close()

    items_by_order = {}

    for item in order_items:

        order_id = item["order_id"]

        if order_id not in items_by_order:
            items_by_order[order_id] = []

        items_by_order[order_id].append(item)

    return render_template(
        "admin.html",
        orders=orders,
        items_by_order=items_by_order
    )


# ==========================================
# UPDATE ORDER STATUS
# ==========================================

@app.route("/update-status/<int:order_id>", methods=["POST"])
@admin_required
def update_status(order_id):

    new_status = request.form.get("status")

    allowed_statuses = [
        "Pending",
        "Preparing",
        "Out for Delivery",
        "Delivered"
    ]

    if new_status not in allowed_statuses:
        return "Invalid status", 400

    conn = get_db_connection()

    conn.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (
        new_status,
        order_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
