from flask import Flask, render_template, request, redirect, url_for, flash, session, g, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(BASE_DIR, 'instance')
templates_path = os.path.join(BASE_DIR, 'templates')
static_path = os.path.join(BASE_DIR, 'static')
os.makedirs(instance_path, exist_ok=True)
os.makedirs(templates_path, exist_ok=True)
os.makedirs(os.path.join(templates_path, "user"), exist_ok=True)
os.makedirs(os.path.join(templates_path, "admin"), exist_ok=True)
os.makedirs(os.path.join(static_path, "css"), exist_ok=True)
os.makedirs(os.path.join(static_path, "js"), exist_ok=True)

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = 'change-me-to-a-secure-random-value'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------ Models ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(50))
    vehicle_details = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SOS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    lat = db.Column(db.String(50))
    lng = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

    user = db.relationship("User", backref="sos_alerts")


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(80), nullable=False)
    relationship = db.Column(db.String(80))

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    recorded = db.Column(db.Boolean, default=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender_role = db.Column(db.String(20))  # 'user' or 'agent' or 'admin'
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    route = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------ Helpers ------------------
def create_default_admin_and_user():
    admin_email = 'admin@safealerts.test'
    user_email = 'user@safealerts.test'
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name='SafeAlerts Admin',
            email=admin_email,
            password_hash=generate_password_hash('AdminPass123!'),
            is_admin=True,
            phone='08000000000'
        )
        db.session.add(admin)
    if not User.query.filter_by(email=user_email).first():
        user = User(
            name='Jane Doe',
            email=user_email,
            password_hash=generate_password_hash('UserPass123!'),
            is_admin=False,
            phone='08011112222',
            vehicle_details='Toyota Corolla - PLATE ABC123'
        )
        db.session.add(user)
        db.session.flush()
        c = Contact(user_id=user.id, name='John Husband', phone='08022223333', relationship='Friend')
        db.session.add(c)
    if not News.query.first():
        n1 = News(title='Commuter reports attempted snatch on Ikoyi-Obalende route',
                  description='A commuter reported an attempted snatch. Stay alert.',
                  route='Ikoyi-Obalende')
        db.session.add(n1)
    db.session.commit()

def write_file(path, content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

def create_initial_html():
    # CSS
    style_css = """body{margin:0;font-family:sans-serif;background:#f5f5f5;color:#333;}
.sidebar{position:fixed;left:0;top:0;width:220px;height:100%;background:#222;color:#fff;padding:1rem;}
.sidebar a{display:block;color:#fff;padding:.5rem 0;text-decoration:none;}
.sidebar a:hover{background:#444;}
.content{margin-left:240px;padding:2rem;}
.navbar{background:#333;color:#fff;padding:1rem;text-align:center;}
.btn{padding:.5rem 1rem;background:#007BFF;color:#fff;border:none;cursor:pointer;border-radius:4px;}
.btn:hover{background:#0056b3;}
.card{background:#fff;padding:1rem;border-radius:8px;margin-bottom:1rem;box-shadow:0 2px 5px rgba(0,0,0,.1);}
form input, form textarea{width:100%;padding:.5rem;margin-bottom:.5rem;}
"""
    write_file(os.path.join(static_path, "css", "style.css"), style_css)

    # JS
    main_js = """console.log('SafeAlerts POC JS Loaded');"""
    write_file(os.path.join(static_path, "js", "main.js"), main_js)

    # Base templates
    base_public = """<!DOCTYPE html><html><head><link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}"></head>
<body><div class="navbar">SafeAlerts</div>{% with messages=get_flashed_messages(with_categories=true) %}
{% for cat,msg in messages %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}{% endwith %}
<div class="content">{% block content %}{% endblock %}</div></body></html>"""
    write_file(os.path.join(templates_path, "base_public.html"), base_public)

    base_user = """<!DOCTYPE html><html><head><link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}"></head>
<body><div class="sidebar"><h2>User Panel</h2>
<a href="{{ url_for('user_dashboard') }}">Dashboard</a>
<a href="{{ url_for('sos') }}">SOS</a>
<a href="{{ url_for('contacts') }}">Contacts</a>
<a href="{{ url_for('profile') }}">Profile</a>
<a href="{{ url_for('chat') }}">Chat</a>
<a href="{{ url_for('logout') }}">Logout</a></div>
<div class="content">{% with messages=get_flashed_messages(with_categories=true) %}
{% for cat,msg in messages %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}{% endwith %}
{% block content %}{% endblock %}</div></body></html>"""
    write_file(os.path.join(templates_path, "base_user.html"), base_user)

    base_admin = """<!DOCTYPE html><html><head><link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}"></head>
<body><div class="sidebar"><h2>Admin Panel</h2>
<a href="{{ url_for('admin_dashboard') }}">Dashboard</a>
<a href="{{ url_for('admin_new_news') }}">Post News</a>
<a href="{{ url_for('logout') }}">Logout</a></div>
<div class="content">{% with messages=get_flashed_messages(with_categories=true) %}
{% for cat,msg in messages %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}{% endwith %}
{% block content %}{% endblock %}</div></body></html>"""
    write_file(os.path.join(templates_path, "base_admin.html"), base_admin)

    # Public pages
    home = """{% extends 'base_public.html' %}{% block content %}<h1>Welcome to SafeAlerts</h1>
<p>Your safety companion.</p><a href="{{ url_for('login') }}" class="btn">Login</a>{% endblock %}"""
    write_file(os.path.join(templates_path, "home.html"), home)

    login = """{% extends 'base_public.html' %}{% block content %}
<h2>Login</h2><form method="post"><input name="email" placeholder="Email"><input name="password" type="password" placeholder="Password"><button class="btn">Login</button></form>{% endblock %}"""
    write_file(os.path.join(templates_path, "login.html"), login)

    # User pages
    user_dash = """{% extends 'base_user.html' %}{% block content %}<h1>User Dashboard</h1>
<div class="card"><h3>Your Contacts</h3>{% for c in contacts %}<p>{{c.name}} ({{c.phone}})</p>{% endfor %}</div>
<div class="card"><h3>Recent Alerts</h3>{% for a in alerts %}<p>{{a.timestamp}} - Active: {{a.active}}</p>{% endfor %}</div>
<div class="card"><h3>Latest News</h3>{% for n in news %}<p>{{n.title}}</p>{% endfor %}</div>{% endblock %}"""
    write_file(os.path.join(templates_path, "user", "dashboard.html"), user_dash)

    sos = """{% extends 'base_user.html' %}{% block content %}<h2>Trigger SOS</h2>
<form method="post"><input name="lat" placeholder="Latitude"><input name="lng" placeholder="Longitude"><button class="btn">Trigger SOS</button></form>{% endblock %}"""
    write_file(os.path.join(templates_path, "user", "sos.html"), sos)

    contacts = """{% extends 'base_user.html' %}{% block content %}<h2>Contacts</h2>
<form method="post"><input name="name" placeholder="Name"><input name="phone" placeholder="Phone"><input name="relationship" placeholder="Relationship"><button class="btn">Add Contact</button></form>
<div class="card">{% for c in contacts %}<p>{{c.name}} - {{c.phone}} ({{c.relationship}})</p>{% endfor %}</div>{% endblock %}"""
    write_file(os.path.join(templates_path, "user", "contacts.html"), contacts)

    profile = """{% extends 'base_user.html' %}{% block content %}<h2>Profile</h2>
<form method="post"><input name="name" value="{{g.user.name}}"><input name="phone" value="{{g.user.phone}}"><input name="vehicle" value="{{g.user.vehicle_details}}"><button class="btn">Save</button></form>{% endblock %}"""
    write_file(os.path.join(templates_path, "user", "profile.html"), profile)

    chat = """{% extends 'base_user.html' %}{% block content %}<h2>Secure Chat</h2>
<div class="card">{% for m in msgs %}<p><b>{{m.sender_role}}:</b> {{m.message}}</p>{% endfor %}</div>
<form method="post"><input name="message" placeholder="Type message"><button class="btn">Send</button></form>{% endblock %}"""
    write_file(os.path.join(templates_path, "user", "chat.html"), chat)

    # Admin pages
    admin_dash = """{% extends 'base_admin.html' %}{% block content %}<h1>Admin Dashboard</h1>
<div class="card"><h3>Users</h3>{% for u in users %}<p>{{u.name}} - {{u.email}}</p>{% endfor %}</div>
<div class="card"><h3>News</h3>{% for n in news %}<p>{{n.title}}</p>{% endfor %}</div>{% endblock %}"""
    write_file(os.path.join(templates_path, "admin", "dashboard.html"), admin_dash)

    new_news = """{% extends 'base_admin.html' %}{% block content %}<h2>Post News</h2>
<form method="post"><input name="title" placeholder="Title"><textarea name="description" placeholder="Description"></textarea><input name="route" placeholder="Route"><button class="btn">Post</button></form>{% endblock %}"""
    write_file(os.path.join(templates_path, "admin", "new_news.html"), new_news)

# ------------------ Routes ------------------
@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

@app.route('/static/<path:filename>')
def static_from_root(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin/sos_alerts')
def admin_sos_alerts():
    if not g.user or not g.user.is_admin:
        flash("Admin access required", "danger")
        return redirect(url_for('login'))

    sos_list = SOS.query.order_by(SOS.timestamp.desc()).all()
    return render_template('admin/admin_sos_alerts.html', sos_list=sos_list)


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('user_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        # validate
        if not all([name, email, phone, password, confirm]):
            flash('All fields are required', 'warning')
            return redirect(url_for('register'))
        if password != confirm:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        # create new user
        new_user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            is_admin=False
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out', 'info')
    return redirect(url_for('home'))

@app.route('/admin')
def admin_dashboard():
    if not g.user or not g.user.is_admin:
        flash('Admin access required', 'warning')
        return redirect(url_for('login'))

    users = User.query.all()
    news = News.query.order_by(News.created_at.desc()).all()
    alerts = Alert.query.filter_by(active=True).all()
    recent_msgs = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(5).all()

    # avg contacts per user
    total_contacts = Contact.query.count()
    avg_contacts = round(total_contacts / len(users), 1) if users else 0

    return render_template(
        'admin/dashboard.html',
        users=users, news=news,
        alerts=alerts, recent_msgs=recent_msgs,
        avg_contacts=avg_contacts
    )


@app.route('/admin/news/new', methods=['GET','POST'])
def admin_new_news():
    if not g.user or not g.user.is_admin:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title')
        desc = request.form.get('description')
        route = request.form.get('route')
        news = News(title=title, description=desc, route=route)
        db.session.add(news); db.session.commit()
        flash('News posted', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/new_news.html')

@app.route('/dashboard')
def user_dashboard():
    if not g.user:
        return redirect(url_for('login'))
    contacts = Contact.query.filter_by(user_id=g.user.id).all()
    alerts = Alert.query.filter_by(user_id=g.user.id).order_by(Alert.timestamp.desc()).limit(5).all()
    news = News.query.order_by(News.created_at.desc()).limit(5).all()
    return render_template('user/dashboard.html', contacts=contacts, alerts=alerts, news=news)

@app.route('/sos', methods=['POST','GET'])
def sos():
    if not g.user:
        flash('Login required to trigger SOS', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        lat = request.form.get('lat') or None
        lng = request.form.get('lng') or None
        a = Alert(user_id=g.user.id, lat=float(lat) if lat else None, lng=float(lng) if lng else None)
        db.session.add(a); db.session.commit()
        flash('SOS triggered (POC) — alert recorded', 'danger')
        return redirect(url_for('user_dashboard'))
    return render_template('user/sos.html')

@app.route('/contacts', methods=['GET','POST'])
def contacts():
    if not g.user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form.get('name'); phone = request.form.get('phone'); rel = request.form.get('relationship')
        c = Contact(user_id=g.user.id, name=name, phone=phone, relationship=rel)
        db.session.add(c); db.session.commit()
        flash('Contact added', 'success')
        return redirect(url_for('contacts'))
    contacts = Contact.query.filter_by(user_id=g.user.id).all()
    return render_template('user/contacts.html', contacts=contacts)

@app.route('/profile', methods=['GET','POST'])
def profile():
    if not g.user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        g.user.name = request.form.get('name')
        g.user.phone = request.form.get('phone')
        g.user.vehicle_details = request.form.get('vehicle')
        db.session.commit()
        flash('Profile updated', 'success')
        return redirect(url_for('profile'))
    return render_template('user/profile.html')

@app.route('/chat', methods=['GET','POST'])
def chat():
    if not g.user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        msg = request.form.get('message')
        cm = ChatMessage(user_id=g.user.id, sender_role='user', message=msg)
        db.session.add(cm); db.session.commit()
        flash('Message sent to agents (POC)', 'success')
        return redirect(url_for('chat'))
    msgs = ChatMessage.query.filter_by(user_id=g.user.id).order_by(ChatMessage.timestamp.asc()).all()
    return render_template('user/chat.html', msgs=msgs)

# ------------------ Setup command ------------------
def setup():
    with app.app_context():  # ensure Flask context
        db.create_all()
        create_default_admin_and_user()
        create_initial_html()
        print('Database, default users, and initial HTML created at instance/app.db')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

