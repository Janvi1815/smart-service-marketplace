from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector

app = Flask(__name__)
app.secret_key = "mysecret12345"

# ---------------- DATABASE CONNECTION ---------------- #
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Janvi@123",
    database="smart_service"
)

cursor = db.cursor(dictionary=True)

# -------------------------- ROUTES -------------------------- #
@app.route('/')
def home():
    if 'user' in session:
        return render_template('home.html', user=session['user'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()

        if user:
            session['user'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))

        cursor.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, password)
        )
        db.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('cart', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# -------------------------- SERVICES ROUTE -------------------------- #
@app.route('/services')
def services():
    if 'user' in session:
        cursor.execute("SELECT * FROM services")
        all_services = cursor.fetchall()
        return render_template('services.html', services=all_services)
    return redirect(url_for('login'))

# -------------------------- PROFILE ROUTE -------------------------- #
@app.route('/profile')
def profile():
    if 'user' in session:
        user_email = session['user']
        user_name = user_email.split('@')[0]

        cart_items = []
        if 'cart' in session:
            for service_id in session['cart']:
                if str(service_id).isnumeric():
                    cursor.execute("SELECT * FROM services WHERE id=%s", (int(service_id),))
                    service = cursor.fetchone()
                    if service:
                        cart_items.append(service)

        return render_template('profile.html', user_name=user_name, user_email=user_email, cart_items=cart_items)
    return redirect(url_for('login'))

# -------------------------- SEARCH ROUTE -------------------------- #
@app.route('/search')
def search():
    if 'user' not in session:
        return redirect(url_for('login'))

    query = request.args.get('q')
    cursor.execute(
        "SELECT * FROM services WHERE name LIKE %s OR category LIKE %s",
        (f"%{query}%", f"%{query}%")
    )
    results = cursor.fetchall()

    return render_template('services.html', services=results, search=query)

# -------------------------- CART ROUTES -------------------------- #
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    if 'user' not in session:
        return jsonify({"status":"error", "message":"Login required!"})

    service_id = request.json.get("service_id")
    if not service_id:
        return jsonify({"status":"error", "message":"No service specified!"})

    if 'cart' not in session:
        session['cart'] = []

    service_id = str(service_id)
    if service_id not in session['cart']:
        session['cart'].append(service_id)
        session.modified = True
        return jsonify({"status":"success", "message":"Added to cart!"})
    return jsonify({"status":"error", "message":"Already in cart!"})

@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    service_id = request.json.get("service_id")
    if 'cart' in session:
        service_id = str(service_id)
        if service_id in session['cart']:
            session['cart'].remove(service_id)
            session.modified = True
            return jsonify({"status":"success", "message":"Removed from cart!"})
    return jsonify({"status":"error", "message":"Item not in cart!"})

@app.route('/show_cart')
def show_cart():
    if 'user' not in session:
        return redirect(url_for('login'))

    cart_items = []
    if 'cart' in session:
        for service_id in session['cart']:
            if str(service_id).isnumeric():
                cursor.execute("SELECT * FROM services WHERE id=%s", (int(service_id),))
                service = cursor.fetchone()
                if service:
                    cart_items.append(service)

    return render_template('show_cart.html', cart_items=cart_items)

@app.route('/checkout')
def checkout():
    if 'user' not in session:
        return redirect(url_for('login'))
    session.pop('cart', None)
    flash("Checkout successful!", "success")
    return redirect(url_for('services'))

# -------------------------- OTHER PAGES -------------------------- #
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")
        print(name, email, subject, message)
    return render_template("contact.html")

# -------------------------- MY ORDERS -------------------------- #
@app.route("/my_orders")
def my_orders():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Fetch full service info for all items in cart
    cart_items = []
    if 'cart' in session:
        for service_id in session['cart']:
            if str(service_id).isnumeric():
                cursor.execute("SELECT * FROM services WHERE id=%s", (int(service_id),))
                service = cursor.fetchone()
                if service and service not in cart_items:
                    cart_items.append(service)  # prevent duplicates

    return render_template("my_orders.html", cart_items=cart_items)

# -------------------------- NEW ORDER FORM HANDLER -------------------------- #
@app.route("/add_order_form", methods=["POST"])
def add_order_form():
    """Handles form submission from the services page Order button"""
    if 'user' not in session:
        flash("Login first to add orders", "danger")
        return redirect(url_for('login'))

    service_id = request.form.get("service_id")
    if not service_id:
        flash("Service not specified", "danger")
        return redirect(url_for('services'))

    if 'cart' not in session:
        session['cart'] = []

    service_id = str(service_id)
    if service_id not in session['cart']:
        session['cart'].append(service_id)
        session.modified = True
        flash("Service added to your orders!", "success")
    else:
        flash("Service already in your orders!", "info")

    return redirect(url_for('services'))

# -------------------------------------------------------- #
if __name__ == '__main__':
    app.run(debug=True, port=5001)
