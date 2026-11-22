
import sqlite3
import pytest
import app as quickbite


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use a separate temporary database for testing
    test_db = tmp_path / "test_quickbite.db"

    monkeypatch.setattr(
        quickbite, "DATABASE", str(test_db)
    )

    quickbite.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key"
    )

    quickbite.init_db()

    with quickbite.app.test_client() as client:
        yield client


def test_homepage(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Chicken Burger" in response.data


def test_add_to_cart(client):
    response = client.post("/add-to-cart/1")

    assert response.status_code == 302

    response = client.get("/cart")

    assert response.status_code == 200
    assert b"Chicken Burger" in response.data


def test_invalid_food_item(client):
    response = client.post("/add-to-cart/999")

    assert response.status_code == 404


def test_checkout_saves_order(client):
    # Add two burgers to the session cart
    with client.session_transaction() as session:
        session["cart"] = {"1": 2}

    response = client.post(
        "/checkout",
        data={
            "name": "Test Customer",
            "phone": "03001234567",
            "address": "Karachi"
        }
    )

    assert response.status_code == 302
    assert "/order-confirmation/" in response.location

    # Verify order was saved in SQLite
    conn = sqlite3.connect(quickbite.DATABASE)

    order = conn.execute(
        "SELECT customer_name, total, status FROM orders"
    ).fetchone()

    item = conn.execute(
        "SELECT food_name, quantity FROM order_items"
    ).fetchone()

    conn.close()

    assert order == ("Test Customer", 1300, "Pending")
    assert item == ("Chicken Burger", 2)


def test_admin_login(client):
    response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "iba@2026"
        }
    )

    assert response.status_code == 302
    assert "/admin" in response.location


def test_admin_dashboard_requires_login(client):
    response = client.get("/admin")

    assert response.status_code == 302
    assert "/admin/login" in response.location
