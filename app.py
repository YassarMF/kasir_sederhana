# app.py

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    make_response
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

project_dir = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(project_dir, 'kasir.db')

# --- FUNGSI DATABASE ---
def get_db_connection():
    """Membuat koneksi ke database dan mengembalikan objek koneksi."""
    conn = sqlite3.connect(database_path) # Gunakan path yang sudah kita tentukan
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inisialisasi skema database dan data default."""
    conn = get_db_connection()
    c = conn.cursor()
    # Tabel Pengguna
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'cashier', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )
    # Tabel Produk
    c.execute(
        """CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL, stock INTEGER NOT NULL, category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )
    # Tabel Transaksi
    c.execute(
        """CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_date DATE NOT NULL, total_amount REAL NOT NULL, tax_amount REAL NOT NULL, cashier_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (cashier_id) REFERENCES users (id))"""
    )
    # Tabel Item Transaksi
    c.execute(
        """CREATE TABLE IF NOT EXISTS transaction_items (id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER, product_id INTEGER, quantity INTEGER NOT NULL, price REAL NOT NULL, FOREIGN KEY (transaction_id) REFERENCES transactions (id), FOREIGN KEY (product_id) REFERENCES products (id))"""
    )
    # Tabel Pengaturan
    c.execute(
        """CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"""
    )

    # Isi data default jika tabel kosong
    if not c.execute("SELECT * FROM users WHERE username = 'admin'").fetchone():
        admin_password = generate_password_hash("admin123")
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", admin_password, "admin"),
        )

    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        sample_products = [
            ("Nasi Putih", 5000, 50, "Makanan"),
            ("Ayam Goreng", 15000, 20, "Makanan"),
            ("Ayam Bakar", 17000, 15, "Makanan"),
            ("Ikan Lele", 12000, 25, "Makanan"),
            ("Sayur Asem", 7000, 30, "Makanan"),
            ("Tempe Goreng", 3000, 40, "Makanan"),
            ("Tahu Goreng", 3000, 40, "Makanan"),
            ("Es Teh", 3000, 100, "Minuman"),
            ("Es Jeruk", 5000, 50, "Minuman"),
            ("Kopi", 4000, 60, "Minuman"),
            ("Kerupuk", 2000, 80, "Snack"),
            ("Sambal", 1000, 100, "Bumbu"),
        ]
        c.executemany(
            "INSERT INTO products (name, price, stock, category) VALUES (?, ?, ?, ?)",
            sample_products,
        )

    if not c.execute("SELECT * FROM settings WHERE key = 'tax_rate'").fetchone():
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("tax_rate", "10"))

    conn.commit()
    conn.close()


# --- DECORATORS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login untuk mengakses halaman ini.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Akses ditolak. Halaman ini khusus untuk admin.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated_function


# --- RUTE-RUTE APLIKASI ---


@app.route("/")
def index():
    return (
        redirect(url_for("login"))
        if "user_id" not in session
        else redirect(url_for("dashboard"))
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f'Login berhasil! Selamat datang, {user["username"]}!', "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Username atau password salah!", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah berhasil logout.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    today = date.today()
    today_sales = conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM transactions WHERE transaction_date = ?",
        (today,),
    ).fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    low_stock_count = conn.execute(
        "SELECT COUNT(*) FROM products WHERE stock < 10"
    ).fetchone()[0]
    recent_transactions = conn.execute(
        """SELECT t.id, t.transaction_date, t.total_amount, u.username FROM transactions t LEFT JOIN users u ON t.cashier_id = u.id ORDER BY t.created_at DESC LIMIT 5"""
    ).fetchall()
    conn.close()
    return render_template(
        "dashboard.html",
        today_sales=today_sales,
        total_products=total_products,
        low_stock_count=low_stock_count,
        recent_transactions=recent_transactions,
    )


@app.route("/pos")
@login_required
def pos():
    conn = get_db_connection()
    products = conn.execute(
        "SELECT * FROM products WHERE stock > 0 ORDER BY name"
    ).fetchall()
    tax_rate_setting = conn.execute(
        "SELECT value FROM settings WHERE key = 'tax_rate'"
    ).fetchone()
    tax_rate = float(tax_rate_setting["value"]) if tax_rate_setting else 10.0
    conn.close()
    
    # Buat respons dari template
    response = make_response(render_template("pos.html", products=products, tax_rate=tax_rate))
    
    # Tambahkan header untuk mencegah caching oleh browser
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response


@app.route("/products")
@login_required
def products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    conn.close()
    return render_template("products.html", products=products)


@app.route("/add_product", methods=["GET", "POST"])
@login_required
@admin_required
def add_product():
    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        category = request.form["category"]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO products (name, price, stock, category) VALUES (?, ?, ?, ?)",
            (name, price, stock, category),
        )
        conn.commit()
        conn.close()
        flash("Produk berhasil ditambahkan!", "success")
        return redirect(url_for("products"))
    return render_template("add_product.html")


@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_product(product_id):
    conn = get_db_connection()
    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        category = request.form["category"]
        conn.execute(
            "UPDATE products SET name = ?, price = ?, stock = ?, category = ? WHERE id = ?",
            (name, price, stock, category, product_id),
        )
        conn.commit()
        conn.close()
        flash("Produk berhasil diperbarui!", "success")
        return redirect(url_for("products"))
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    conn.close()
    if not product:
        flash("Produk tidak ditemukan!", "error")
        return redirect(url_for("products"))
    return render_template("edit_product.html", product=product)


@app.route("/delete_product/<int:product_id>")
@login_required
@admin_required
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Produk berhasil dihapus!", "success")
    return redirect(url_for("products"))


@app.route("/process_transaction", methods=["POST"])
@login_required
def process_transaction():
    data = request.get_json()
    if not data or "items" not in data or not data["items"]:
        return (
            jsonify(
                {"success": False, "message": "Data keranjang tidak valid atau kosong."}
            ),
            400,
        )

    conn = None
    try:
        conn = get_db_connection()
        tax_rate_setting = conn.execute(
            "SELECT value FROM settings WHERE key = 'tax_rate'"
        ).fetchone()
        tax_rate = (
            float(tax_rate_setting["value"]) / 100.0 if tax_rate_setting else 0.10
        )

        subtotal = 0
        processed_items = []

        for item in data["items"]:
            product_id = int(item["id"])
            quantity_sold = int(item["quantity"])
            if quantity_sold <= 0:
                raise ValueError(f"Kuantitas tidak valid untuk produk ID {product_id}")
            product_db = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if not product_db:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Produk ID {product_id} tidak ditemukan.",
                        }
                    ),
                    404,
                )
            if quantity_sold > product_db["stock"]:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Stok {product_db['name']} tidak cukup. Sisa: {product_db['stock']}",
                        }
                    ),
                    400,
                )

            subtotal += product_db["price"] * quantity_sold
            processed_items.append(
                {
                    "id": product_id,
                    "name": product_db["name"],
                    "quantity": quantity_sold,
                    "price": product_db["price"],
                }
            )

        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (transaction_date, total_amount, tax_amount, cashier_id) VALUES (?, ?, ?, ?)",
            (date.today(), total_amount, tax_amount, session.get("user_id")),
        )
        transaction_id = cursor.lastrowid

        for item in processed_items:
            cursor.execute(
                "INSERT INTO transaction_items (transaction_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                (transaction_id, item["id"], item["quantity"], item["price"]),
            )
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item["quantity"], item["id"]),
            )

        conn.commit()
        return jsonify(
            {
                "success": True,
                "message": "Transaksi berhasil!",
                "transaction_id": transaction_id,
                "total_amount": total_amount,
                "tax_amount": tax_amount,
                "subtotal": subtotal,
                "items": processed_items,
            }
        )

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error saat proses transaksi: {e}")
        return (
            jsonify({"success": False, "message": f"Terjadi kesalahan internal: {e}"}),
            500,
        )
    finally:
        if conn:
            conn.close()


@app.route("/reports")
@login_required
@admin_required
def reports():
    conn = get_db_connection()
    start_date = request.args.get(
        "start_date", date.today().replace(day=1).strftime("%Y-%m-%d")
    )
    end_date = request.args.get("end_date", date.today().strftime("%Y-%m-%d"))
    transactions = conn.execute(
        "SELECT t.id, t.transaction_date, t.total_amount, u.username as cashier_name FROM transactions t LEFT JOIN users u ON t.cashier_id = u.id WHERE t.transaction_date BETWEEN ? AND ? ORDER BY t.created_at DESC",
        (start_date, end_date),
    ).fetchall()
    conn.close()
    return render_template(
        "reports.html",
        transactions=transactions,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/delete_transaction/<int:transaction_id>", methods=["POST"])
@login_required
@admin_required
def delete_transaction(transaction_id):
    # Rute ini untuk "Batal Transaksi" (mengembalikan stok)
    conn = None
    try:
        conn = get_db_connection()
        items_to_restock = conn.execute(
            "SELECT product_id, quantity FROM transaction_items WHERE transaction_id = ?",
            (transaction_id,),
        ).fetchall()
        for item in items_to_restock:
            conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
        conn.execute(
            "DELETE FROM transaction_items WHERE transaction_id = ?", (transaction_id,)
        )
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        flash("Transaksi berhasil dibatalkan dan stok telah dikembalikan.", "success")
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Gagal membatalkan transaksi: {e}", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("reports"))


@app.route("/delete_transaction_permanent/<int:transaction_id>", methods=["POST"])
@login_required
@admin_required
def delete_transaction_permanent(transaction_id):
    # Rute ini untuk "Hapus Permanen" (TIDAK mengembalikan stok)
    conn = None
    try:
        conn = get_db_connection()
        conn.execute(
            "DELETE FROM transaction_items WHERE transaction_id = ?", (transaction_id,)
        )
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        flash("Transaksi telah dihapus secara permanen dari catatan.", "success")
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Gagal menghapus transaksi permanen: {e}", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("reports"))


@app.route("/users")
@login_required
@admin_required
def users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
    conn.close()
    return render_template("users.html", users=users)


@app.route("/add_user", methods=["GET", "POST"])
@login_required
@admin_required
def add_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        conn = get_db_connection()
        if conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone():
            flash("Username sudah ada!", "error")
            conn.close()
            return render_template("add_user.html")
        hashed_password = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed_password, role),
        )
        conn.commit()
        conn.close()
        flash("Pengguna berhasil ditambahkan!", "success")
        return redirect(url_for("users"))
    return render_template("add_user.html")


@app.route("/delete_user/<int:user_id>")
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("Anda tidak dapat menghapus akun Anda sendiri!", "error")
    elif user_id == 1:
        flash("Pengguna admin utama tidak dapat dihapus.", "error")
    else:
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("Pengguna berhasil dihapus.", "success")
    return redirect(url_for("users"))


@app.route("/settings", methods=["GET", "POST"])
@login_required  # DIUBAH: Sekarang semua user bisa mengakses
def settings():
    conn = get_db_connection()

    # Logika untuk menyimpan HANYA bisa dijalankan oleh admin
    if request.method == "POST":
        # Pengecekan keamanan tambahan di backend
        if session.get("role") != "admin":
            flash("Hanya admin yang dapat mengubah pengaturan.", "error")
            return redirect(url_for("settings"))

        tax_rate = request.form.get("tax_rate")
        if tax_rate is not None:
            try:
                if float(tax_rate) >= 0:
                    conn.execute(
                        "UPDATE settings SET value = ? WHERE key = 'tax_rate'",
                        (tax_rate,),
                    )
                    conn.commit()
                    flash("Pengaturan pajak berhasil diperbarui!", "success")
                else:
                    flash("Persentase pajak tidak boleh negatif.", "error")
            except ValueError:
                flash("Masukkan angka yang valid untuk pajak.", "error")

    setting = conn.execute("SELECT * FROM settings WHERE key = 'tax_rate'").fetchone()
    conn.close()
    return render_template("settings.html", setting=setting)


@app.route('/api/get_settings')
def get_settings():
    """Rute API untuk memberikan pengaturan terbaru dalam format JSON."""
    conn = get_db_connection()
    tax_rate_setting = conn.execute("SELECT value FROM settings WHERE key = 'tax_rate'").fetchone()
    conn.close()
    
    tax_rate = float(tax_rate_setting['value']) if tax_rate_setting else 10.0
    
    return jsonify({
        'tax_rate_percent': tax_rate
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5001)