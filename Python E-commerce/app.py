from flask import Flask, redirect, url_for, render_template, request, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key" 


db_config = {
    'host': 'localhost',
    'user': 'root',  
    'password': 'root',  
    'database': 'user_login'  
}


def init_db():
    conn = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password']
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS user_login")
    conn.close()

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            image VARCHAR(255) NOT NULL,
            quantity INT DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        flash("Please log in to add items to the cart.", "warning")
        return redirect('/login')

    product_name = request.form['product_name']
    price = float(request.form['price'])  
    image = request.form['image']
    user_id = session['user_id']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        
        cursor.execute("SELECT id, quantity FROM cart_items WHERE user_id = %s AND product_name = %s",
                       (user_id, product_name))
        existing_item = cursor.fetchone()

        if existing_item:
            cursor.execute("UPDATE cart_items SET quantity = quantity + 1 WHERE id = %s",
                           (existing_item[0],))
        else:
            cursor.execute("INSERT INTO cart_items (user_id, product_name, price, image, quantity) VALUES (%s, %s, %s, %s, %s)",
                           (user_id, product_name, price, image, 1))

        conn.commit()
        flash(f"Added {product_name} to cart!", "success")

    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
    
    finally:
        cursor.close()
        conn.close()

    return redirect('/clothes') 

    
    


@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM cart_items WHERE user_id = %s AND id = %s
    """, (user_id, item_id))

    conn.commit()
    cursor.close()
    conn.close()

    
    return redirect('/cart')



@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM cart_items WHERE user_id = %s", (user_id,))
    cart_items = cursor.fetchall()

    # Calculate total price
    cursor.execute("SELECT SUM(price * quantity) AS grand_total FROM cart_items WHERE user_id = %s", (user_id,))
    grand_total = cursor.fetchone()['grand_total'] or 0

    cursor.close()
    conn.close()

    return render_template("cart.html", cart_items=cart_items, grand_total=grand_total)

@app.route('/')
def home():
    if 'user_id' in session:
        user_id = session['user_id']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template("index.html", user=user)
    return redirect('/home')

@app.route('/home')
def index():
    return render_template("index.html")


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash("Login successful!", "success")
            return redirect('/main')
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("./Auth/login.html")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                           (username, email, password))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Registration successful! Please log in.", "success")
            return redirect('/login')
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
            return redirect('/signup')

    return render_template("./Auth/signUp.html")


@app.route('/main')
def main():
    if 'user_id' in session:
        user_id = session['user_id']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template("main.html", user=user)
    return redirect('/login')


@app.route('/clothes')
def clothes():
    return render_template("./Pages/clothes.html")


@app.route('/shoes')
def shoes():
    return render_template("./Pages/shoes.html")


@app.route('/laptops')
def laptops():
    return render_template("./Pages/laptops.html")


@app.route('/access')
def access():
    return render_template("./Pages/access.html")


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "success")
    return redirect('/home')

if __name__ == '__main__':
    init_db()
    app.run()
