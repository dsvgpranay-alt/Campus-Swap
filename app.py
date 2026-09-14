import os
from functools import wraps
from urllib.parse import urlparse

import mysql.connector
from google import genai
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "campus-swap-dev-secret-key")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": "campus_swap"
}

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

CATEGORIES = [
    "Books",
    "Electronics",
    "Stationery",
    "Lab Equipment",
    "Furniture",
    "Clothing",
    "Sports",
    "Accessories",
    "Other"
]

CONDITIONS = [
    "New",
    "Like New",
    "Good",
    "Used"
]


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login", next=request.full_path))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def listing_count_for(user_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT COUNT(*) FROM items WHERE seller_id = %s",
            (user_id,)
        )
        return cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/marketplace")
def marketplace():
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        query = """
            SELECT items.*, users.first_name, users.last_name
            FROM items
            JOIN users ON items.seller_id = users.id
            WHERE 1=1
        """

        params = []

        if category:
            query += " AND items.category = %s"
            params.append(category)

        if search:
            query += """
                AND (
                    items.title LIKE %s
                    OR items.description LIKE %s
                )
            """
            search_value = f"%{search}%"
            params.extend([search_value, search_value])

        query += " ORDER BY items.created_at DESC"

        cur.execute(query, tuple(params))
        items = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    return render_template(
        "marketplace.html",
        items=items,
        categories=CATEGORIES,
        selected_category=category,
        search=search
    )


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT items.*,
                   users.first_name,
                   users.last_name,
                   users.email AS seller_email,
                   users.phone AS seller_phone,
                   users.campus
            FROM items
            JOIN users ON items.seller_id = users.id
            WHERE items.id = %s
        """, (item_id,))

        item = cur.fetchone()

    finally:
        cur.close()
        conn.close()

    if not item:
        abort(404)

    is_owner = session.get("user_id") == item["seller_id"]

    return render_template(
        "item_detail.html",
        item=item,
        is_owner=is_owner
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    if not name or not email or not password:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("register"))

    if "@" not in email:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("register"))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "error")
        return redirect(url_for("register"))

    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("register"))

    name_parts = name.split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        if cur.fetchone():
            flash("An account with this email already exists.", "error")
            return redirect(url_for("login"))

        password_hash = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users (first_name, last_name, email, password_hash)
            VALUES (%s, %s, %s, %s)
        """, (first_name, last_name, email, password_hash))

        conn.commit()
        session["user_id"] = cur.lastrowid

    except Exception:
        conn.rollback()
        flash("Unable to create your account. Please try again.", "error")
        return redirect(url_for("register"))

    finally:
        cur.close()
        conn.close()

    flash("Account created successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    next_url = request.args.get("next", "")

    if not email or not password:
        flash("Please enter your email and password.", "error")
        return redirect(url_for("login", next=next_url))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )
        user = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("login", next=next_url))

    session["user_id"] = user["id"]

    parsed = urlparse(next_url)

    if next_url and parsed.netloc == "" and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    user = current_user()

    if not user:
        session.clear()
        return redirect(url_for("login"))

    listing_count = listing_count_for(user["id"])

    return render_template(
        "profile.html",
        user=user,
        listing_count=listing_count
    )


@app.route("/profile/basic", methods=["POST"])
@login_required
def update_basic_info():
    user_id = session["user_id"]

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not first_name or not email:
        flash("First name and email are required.", "error")
        return redirect(url_for("profile"))

    if "@" not in email:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("profile"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT id FROM users WHERE email = %s AND id != %s",
            (email, user_id)
        )

        if cur.fetchone():
            flash("That email is already being used.", "error")
            return redirect(url_for("profile"))

        cur.execute("""
            UPDATE users
            SET first_name = %s,
                last_name = %s,
                email = %s
            WHERE id = %s
        """, (first_name, last_name, email, user_id))

        conn.commit()
        flash("Basic information updated successfully.", "success")

    except Exception:
        conn.rollback()
        flash("Unable to update your information.", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("profile"))


@app.route("/profile/campus", methods=["POST"])
@login_required
def update_campus_info():
    user_id = session["user_id"]

    campus = request.form.get("campus", "").strip()
    hostel_block = request.form.get("hostel_block", "").strip()
    department = request.form.get("department", "").strip()
    reg_number = request.form.get("reg_number", "").strip()
    semester_year = request.form.get("semester_year", "").strip()
    room_alt = request.form.get("room_alt", "").strip()

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET campus = %s,
                hostel_block = %s,
                department = %s,
                reg_number = %s,
                semester_year = %s,
                room_alt = %s
            WHERE id = %s
        """, (
            campus,
            hostel_block,
            department,
            reg_number,
            semester_year,
            room_alt,
            user_id
        ))

        conn.commit()
        flash("Campus information updated successfully.", "success")

    except Exception:
        conn.rollback()
        flash("Unable to update your campus information.", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("profile"))


@app.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "DELETE FROM users WHERE id = %s",
            (user_id,)
        )

        conn.commit()
        session.clear()
        flash("Your account has been deleted.", "success")

    except Exception:
        conn.rollback()
        flash("Unable to delete your account.", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("index"))


@app.route("/my-listings")
@login_required
def my_listings():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT *
            FROM items
            WHERE seller_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        items = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    return render_template("my_listings.html", items=items)


@app.route("/add-item", methods=["GET", "POST"])
@login_required
def add_item():
    if request.method == "GET":
        return render_template(
            "add_item.html",
            categories=CATEGORIES,
            conditions=CONDITIONS
        )

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    condition = request.form.get("condition", "").strip()
    price = request.form.get("price", "").strip()
    image_url = request.form.get("image_url", "").strip()

    if not title or not category or not condition or not price:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("add_item"))

    if category not in CATEGORIES:
        flash("Invalid category.", "error")
        return redirect(url_for("add_item"))

    if condition not in CONDITIONS:
        flash("Invalid condition.", "error")
        return redirect(url_for("add_item"))

    try:
        price_val = float(price)

        if price_val < 0:
            raise ValueError

    except ValueError:
        flash("Please enter a valid non-negative price.", "error")
        return redirect(url_for("add_item"))

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO items
            (seller_id, title, description, price, category, item_condition, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            title,
            description,
            price_val,
            category,
            condition,
            image_url or None
        ))

        conn.commit()
        flash("Item listed successfully.", "success")

    except Exception:
        conn.rollback()
        flash("Unable to list the item.", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("my_listings"))


@app.route("/generate-description", methods=["POST"])
@login_required
def generate_description():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    condition = data.get("condition", "").strip()

    if not title or not category or not condition:
        return {"error": "Title, category and condition are required."}, 400

    prompt = f"""
Write a short marketplace description for a college student selling an item.

Item: {title}
Category: {category}
Condition: {condition}

Keep it natural and between 40 and 70 words.
Do not invent specifications or features.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        return {"description": response.text.strip()}

    except Exception:
        return {"error": "Unable to generate a description right now."}, 500


@app.route("/edit-item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT *
            FROM items
            WHERE id = %s AND seller_id = %s
        """, (item_id, user_id))

        item = cur.fetchone()

        if not item:
            abort(404)

        if request.method == "GET":
            return render_template(
                "edit_item.html",
                item=item,
                categories=CATEGORIES,
                conditions=CONDITIONS
            )

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        condition = request.form.get("condition", "").strip()
        price = request.form.get("price", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not title or not category or not condition or not price:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("edit_item", item_id=item_id))

        if category not in CATEGORIES:
            flash("Invalid category.", "error")
            return redirect(url_for("edit_item", item_id=item_id))

        if condition not in CONDITIONS:
            flash("Invalid condition.", "error")
            return redirect(url_for("edit_item", item_id=item_id))

        try:
            price_val = float(price)

            if price_val < 0:
                raise ValueError

        except ValueError:
            flash("Please enter a valid non-negative price.", "error")
            return redirect(url_for("edit_item", item_id=item_id))

        cur.execute("""
            UPDATE items
            SET title = %s,
                description = %s,
                price = %s,
                category = %s,
                item_condition = %s,
                image_url = %s
            WHERE id = %s AND seller_id = %s
        """, (
            title,
            description,
            price_val,
            category,
            condition,
            image_url or None,
            item_id,
            user_id
        ))

        conn.commit()
        flash("Item updated successfully.", "success")

    except Exception:
        conn.rollback()
        flash("Unable to update the item.", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("my_listings"))


@app.route("/delete-item/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM items
            WHERE id = %s AND seller_id = %s
        """, (item_id, user_id))

        if cur.rowcount == 0:
            abort(404)

        conn.commit()
        flash("Item deleted successfully.", "success")

    except Exception:
        conn.rollback()
        flash("Unable to delete the item.", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("my_listings"))


if __name__ == "__main__":
    app.run(debug=True)