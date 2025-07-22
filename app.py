from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'increff-secret'  # secret key for session
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- Models ----------------
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    product = db.relationship('Product', backref=db.backref('orders', lazy=True))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ---------------- Routes ----------------

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    products = Product.query.all()
    message = request.args.get('message')
    return render_template('index.html', products=products, message=message)

@app.route('/add', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    name = request.form['name']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    new_product = Product(name=name, quantity=quantity, price=price)
    db.session.add(new_product)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.quantity = int(request.form['quantity'])
        product.price = float(request.form['price'])
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', product=product)

@app.route('/delete/<int:id>')
def delete_product(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    product_id = int(request.form['product_id'])
    order_qty = int(request.form['order_qty'])
    product = Product.query.get_or_404(product_id)
    if product.quantity >= order_qty:
        product.quantity -= order_qty
        order = Order(product_id=product_id, quantity=order_qty)
        db.session.add(order)
        db.session.commit()
        message = f"Order placed for {order_qty} {product.name}(s)"
    else:
        message = f"❌ Not enough stock for {product.name}"
    return redirect(url_for('index', message=message))

@app.route('/orders')
def view_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    orders = Order.query.order_by(Order.timestamp.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/deliver/<int:order_id>')
def mark_delivered(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = Order.query.get_or_404(order_id)
    if order.status != 'Delivered':
        order.status = 'Delivered'
        db.session.commit()
    return redirect(url_for('view_orders'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    products = Product.query.all()
    orders = Order.query.all()
    product_names = [p.name for p in products]
    product_qtys = [p.quantity for p in products]
    delivered = sum(1 for o in orders if o.status == 'Delivered')
    pending = sum(1 for o in orders if o.status == 'Pending')
    return render_template(
        'dashboard.html',
        product_names=product_names,
        product_qtys=product_qtys,
        delivered=delivered,
        pending=pending
    )

# ---------------- Auth Routes ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ---------------- Run App ----------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
