import os
from functools import wraps
import mysql.connector
from google import genai
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv("credentials.env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "campus-swap-dev-secret-key")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),
    "database": "campus_swap"
}

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CATEGORIES = ["Books", "Electronics", "Stationery", "Lab Equipment","Furniture", "Clothing", "Sports", "Accessories", "Other"]

CONDITIONS = ["New", "Like New", "Good", "Used"]


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if not session.get("user_id"):
        return None

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM users WHERE id = %s",
        (session["user_id"],)
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    return user


def listing_count_for(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM items WHERE seller_id = %s",
        (user_id,)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()

    return count


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/marketplace")
def marketplace():
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip()

    sql = """
        SELECT items.*, users.first_name, users.last_name, users.campus
        FROM items
        JOIN users ON users.id = items.seller_id
        WHERE 1 = 1
    """

    params = []

    if category:
        sql += " AND items.category = %s"
        params.append(category)

    if q:
        sql += " AND (items.title LIKE %s OR items.description LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like])

    sql += " ORDER BY items.created_at DESC"

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    items = cur.fetchall()
    cur.close()
    conn.close()

    return render_template(
        "marketplace.html",
        items=items,
        categories=CATEGORIES,
        selected_category=category,
        q=q
    )


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT items.*, users.first_name, users.last_name, users.campus,
               users.email AS seller_email, users.phone AS seller_phone
        FROM items
        JOIN users ON users.id = items.seller_id
        WHERE items.id = %s
        """,
        (item_id,)
    )

    item = cur.fetchone()
    cur.close()
    conn.close()

    if not item:
        abort(404)

    is_owner = session.get("user_id") == item["seller_id"]

    return render_template(
        "items/item_detail.html",
        item=item,
        is_owner=is_owner
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("register"))

        if password != password_confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("register"))

        parts = name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        if cur.fetchone():
            cur.close()
            conn.close()
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        cur.execute(
            """
            INSERT INTO users
            (first_name, last_name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (first_name, last_name, email, password_hash)
        )

        conn.commit()
        new_id = cur.lastrowid

        cur.close()
        conn.close()

        session["user_id"] = new_id

        flash(
            "Welcome to Campus Swap! Add your campus details to complete your profile.",
            "success"
        )

        return redirect(url_for("profile"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user or not check_password_hash(
            user["password_hash"],
            password
        ):
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]

        flash(
            f"Welcome back, {user['first_name']}!",
            "success"
        )

        next_url = request.args.get("next")

        return redirect(
            next_url or url_for("index")
        )

    return render_template("auth/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    user = current_user()
    count = listing_count_for(user["id"])

    return render_template(
        "profile/profile.html",
        user=user,
        listing_count=count
    )


@app.route("/profile/basic", methods=["POST"])
@login_required
def update_basic_info():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    bio = request.form.get("bio", "").strip()

    if not first_name or not email:
        flash("First name and email are required.", "error")
        return redirect(url_for("profile"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET first_name = %s,
            last_name = %s,
            email = %s,
            phone = %s,
            bio = %s
        WHERE id = %s
        """,
        (
            first_name,
            last_name,
            email,
            phone,
            bio,
            session["user_id"]
        )
    )

    conn.commit()
    cur.close()
    conn.close()

    flash("Your basic info has been updated.", "success")

    return redirect(url_for("profile"))

@app.route("/profile/campus", methods=["POST"])
@login_required
def update_campus_info():
    campus = request.form.get("campus", "").strip()
    hostel_block = request.form.get("hostel_block", "").strip()
    department = request.form.get("department", "").strip()
    reg_number = request.form.get("reg_number", "").strip()
    semester_year = request.form.get("semester_year", "").strip()
    room_alt = request.form.get("room_alt", "").strip()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users
        SET campus = %s,
            hostel_block = %s,
            department = %s,
            reg_number = %s,
            semester_year = %s,
            room_alt = %s
        WHERE id = %s
        """,
        (
            campus,
            hostel_block,
            department,
            reg_number,
            semester_year,
            room_alt,
            session["user_id"]
        )
    )

    conn.commit()
    cur.close()
    conn.close()
    flash("Your campus details have been updated.", "success")
    return redirect(url_for("profile"))

@app.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM users WHERE id = %s",
        (user_id,)
    )

    conn.commit()
    cur.close()
    conn.close()

    session.clear()

    flash("Your account has been deleted.", "success")

    return redirect(url_for("index"))

@app.route("/my-listings")
@login_required
def my_listings():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT *
        FROM items
        WHERE seller_id = %s
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    )

    items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "items/my_listings.html",
        items=items
    )
@app.route("/add-item", methods=["GET", "POST"])
@login_required
def add_item():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0").strip() or "0"
        category = request.form.get("category", "").strip()
        condition = request.form.get("condition", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not title or not category or not condition:
            flash(
                "Title, category and condition are required.",
                "error"
            )
            return redirect(url_for("add_item"))

        try:
            price_val = float(price)
        except ValueError:
            price_val = 0

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO items
            (seller_id, title, description, price, category,
             item_condition, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                title,
                description,
                price_val,
                category,
                condition,
                image_url or None
            )
        )

        conn.commit()
        new_id = cur.lastrowid

        cur.close()
        conn.close()

        flash("Your item has been listed!", "success")

        return redirect(
            url_for("item_detail", item_id=new_id)
        )

    return render_template(
        "items/add_item.html",
        categories=CATEGORIES,
        conditions=CONDITIONS
    )


@app.route("/generate-description", methods=["POST"])
@login_required
def generate_description():
    data = request.get_json()

    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    condition = data.get("condition", "").strip()

    if not title:
        return {"error": "Enter the item title first."}, 400

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

        return {"description": response.text}

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/edit-item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT * FROM items WHERE id = %s",
        (item_id,)
    )

    item = cur.fetchone()

    if not item:
        cur.close()
        conn.close()
        abort(404)

    if item["seller_id"] != session["user_id"]:
        cur.close()
        conn.close()

        flash(
            "You can only edit your own listings.",
            "error"
        )

        return redirect(url_for("my_listings"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0").strip() or "0"
        category = request.form.get("category", "").strip()
        condition = request.form.get("condition", "").strip()
        image_url = request.form.get("image_url", "").strip()

        try:
            price_val = float(price)
        except ValueError:
            price_val = 0

        cur2 = conn.cursor()

        cur2.execute(
            """
            UPDATE items
            SET title = %s,
                description = %s,
                price = %s,
                category = %s,
                item_condition = %s,
                image_url = %s
            WHERE id = %s
            AND seller_id = %s
            """,
            (
                title,
                description,
                price_val,
                category,
                condition,
                image_url or None,
                item_id,
                session["user_id"]
            )
        )

        conn.commit()

        cur2.close()
        cur.close()
        conn.close()

        flash("Listing updated.", "success")

        return redirect(
            url_for("item_detail", item_id=item_id)
        )

    cur.close()
    conn.close()

    return render_template(
        "items/edit_item.html",
        item=item,
        categories=CATEGORIES,
        conditions=CONDITIONS
    )

@app.route("/delete-item/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT * FROM items WHERE id = %s",
        (item_id,)
    )
    item = cur.fetchone()
    if not item:
        cur.close()
        conn.close()
        abort(404)
    if item["seller_id"] != session["user_id"]:
        cur.close()
        conn.close()

        flash(
            "You can only delete your own listings.",
            "error")

        return redirect(url_for("my_listings"))
    cur2 = conn.cursor()

    cur2.execute(
        """
        DELETE FROM items
        WHERE id = %s
        AND seller_id = %s
        """,
        (
            item_id,
            session["user_id"]
        )
    )
    conn.commit()
    cur2.close()
    cur.close()
    conn.close()

    flash("Listing deleted.", "success")

    return redirect(url_for("my_listings"))

@app.route("/docs/about/")
def about():
    return render_template("docs/about.html")

@app.route("/docs/blogs")
def blogs():
  return render_template("docs/blogs.html")

@app.route("/docs/mission")
def mission():
    return render_template("docs/mission.html")

@app.route("/support/contact")
def contact():
    return render_template("support/contact.html")

@app.route("/docs/faqs")
def faqs():
    return render_template("support/faqs.html")

@app.route("/support/help_center")
def help_center():
    return render_template("support/help_center.html")

@app.route("/support/report")
def report():
  return return_template("support/report.html")

@app.route("/support/safety_guidelines")
def safety_guidelines():
    return render_template("support/safety_guidelines.html")
  

if __name__ == "__main__":
    app.run(debug=True)

