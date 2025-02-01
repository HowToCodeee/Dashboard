import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Database configuration
db_path = os.environ.get("DATABASE_URL", "sqlite:///gesellschaften.db")
app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class Benutzer(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    benutzername = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passwort = db.Column(db.String(256), nullable=False)

class Gesellschaft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    telefon = db.Column(db.String(20), nullable=False)
    baustellen = relationship('Baustelle', backref='gesellschaft', lazy=True)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artikelnummer = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.String(255), nullable=True)
    menge = db.Column(db.Integer, nullable=False)
    einheit = db.Column(db.String(50), nullable=False)
    mindestbestand = db.Column(db.Integer, default=0)
    lieferant = db.Column(db.String(100))
    lieferant_kontakt = db.Column(db.String(200))

class Bestellung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, ForeignKey('material.id'), nullable=False)
    menge = db.Column(db.Integer, nullable=False)
    bestelldatum = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Neu')
    material = relationship('Material', backref='bestellungen')

class Baustelle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    gesellschaft_id = db.Column(db.Integer, ForeignKey('gesellschaft.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Aktiv')
    start_datum = db.Column(db.Date, nullable=False)
    end_datum = db.Column(db.Date)
    beschreibung = db.Column(db.Text)
    dokumente = relationship('BaustellenDokument', backref='baustelle', lazy=True)

class BaustellenDokument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baustelle_id = db.Column(db.Integer, ForeignKey('baustelle.id'), nullable=False)
    typ = db.Column(db.String(20), nullable=False)  # 'foto' oder 'pdf'
    dateiname = db.Column(db.String(255), nullable=False)
    upload_datum = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    beschreibung = db.Column(db.String(255))

class Termin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.String(255), nullable=True)
    datum = db.Column(db.Date, nullable=False)
    baustelle_id = db.Column(db.Integer, ForeignKey('baustelle.id'))
    baustelle = relationship('Baustelle', backref='termine')

@login_manager.user_loader
def load_user(user_id):
    return Benutzer.query.get(int(user_id))

# Create database and default users
with app.app_context():
    db.create_all()

    # Create default users if they don't exist
    default_users = [
        {
            'benutzername': 'admin',
            'email': 'admin@simplethings.de',
            'passwort': 'admin123'
        }
    ]

    for user_data in default_users:
        if not Benutzer.query.filter_by(email=user_data['email']).first():
            neuer_benutzer = Benutzer(
                benutzername=user_data['benutzername'],
                email=user_data['email'],
                passwort=generate_password_hash(user_data['passwort'])
            )
            db.session.add(neuer_benutzer)

    db.session.commit()

# Login routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        passwort = request.form['passwort']
        benutzer = Benutzer.query.filter_by(email=email).first()

        if benutzer and check_password_hash(benutzer.passwort, passwort):
            login_user(benutzer)
            flash('Erfolgreich eingeloggt!', 'success')
            return redirect(url_for('dashboard'))
        flash('Ungültige Email oder Passwort!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Erfolgreich ausgeloggt!', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/dashboard')
@login_required
def dashboard():
    heute = datetime.today().date()
    bevorstehende_termine = Termin.query.filter(Termin.datum == heute).all()
    benachrichtigungen = [
        f"Heute steht der Termin '{termin.titel}' an." for termin in bevorstehende_termine
    ]
    return render_template("dashboard.html", 
                         benachrichtigungen=benachrichtigungen,
                         benutzer=current_user)

# Gesellschaften routes
@app.route('/gesellschaften', methods=['GET', 'POST'])
@login_required
def gesellschaften():
    if request.method == 'POST':
        name = request.form['name']
        adresse = request.form['adresse']
        email = request.form['email']
        telefon = request.form['telefon']
        neue_gesellschaft = Gesellschaft(name=name, adresse=adresse, email=email, telefon=telefon)
        db.session.add(neue_gesellschaft)
        db.session.commit()
        flash("Gesellschaft erfolgreich hinzugefügt!", "success")
        return redirect(url_for('gesellschaften'))
    gesellschaften = Gesellschaft.query.all()
    return render_template('gesellschaften.html', gesellschaften=gesellschaften)

@app.route('/gesellschaften/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_gesellschaft(id):
    gesellschaft = Gesellschaft.query.get_or_404(id)
    if request.method == 'POST':
        gesellschaft.name = request.form['name']
        gesellschaft.adresse = request.form['adresse']
        gesellschaft.email = request.form['email']
        gesellschaft.telefon = request.form['telefon']
        db.session.commit()
        flash("Gesellschaft erfolgreich bearbeitet!", "success")
        return redirect(url_for('gesellschaften'))
    return render_template('edit_gesellschaft.html', gesellschaft=gesellschaft)

@app.route('/gesellschaften/delete/<int:id>', methods=['POST'])
@login_required
def delete_gesellschaft(id):
    gesellschaft = Gesellschaft.query.get_or_404(id)
    db.session.delete(gesellschaft)
    db.session.commit()
    flash("Gesellschaft erfolgreich gelöscht!", "success")
    return redirect(url_for('gesellschaften'))

# Material routes
@app.route('/material', methods=['GET', 'POST'])
@login_required
def material():
    if request.method == 'POST':
        artikelnummer = request.form['artikelnummer']
        name = request.form['name']
        beschreibung = request.form.get('beschreibung', '')
        menge = int(request.form['menge'])
        einheit = request.form['einheit']
        mindestbestand = int(request.form.get('mindestbestand', 0))
        lieferant = request.form.get('lieferant', '')
        lieferant_kontakt = request.form.get('lieferant_kontakt', '')

        neues_material = Material(
            artikelnummer=artikelnummer,
            name=name,
            beschreibung=beschreibung,
            menge=menge,
            einheit=einheit,
            mindestbestand=mindestbestand,
            lieferant=lieferant,
            lieferant_kontakt=lieferant_kontakt
        )
        db.session.add(neues_material)
        db.session.commit()
        flash("Material erfolgreich hinzugefügt!", "success")
        return redirect(url_for('material'))

    materialien = Material.query.all()
    return render_template('material.html', materialien=materialien)

@app.route('/material/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_material(id):
    material = Material.query.get_or_404(id)
    if request.method == 'POST':
        material.artikelnummer = request.form['artikelnummer']
        material.name = request.form['name']
        material.beschreibung = request.form.get('beschreibung', '')
        material.menge = int(request.form['menge'])
        material.einheit = request.form['einheit']
        material.mindestbestand = int(request.form['mindestbestand'])
        material.lieferant = request.form.get('lieferant', '')
        material.lieferant_kontakt = request.form.get('lieferant_kontakt', '')
        db.session.commit()
        flash("Material erfolgreich bearbeitet!", "success")
        return redirect(url_for('material'))
    return render_template('edit_material.html', material=material)

@app.route('/material/bestellen/<int:material_id>', methods=['GET', 'POST'])
@login_required
def bestellen(material_id):
    material = Material.query.get_or_404(material_id)
    if request.method == 'POST':
        menge = int(request.form['menge'])
        bestellung = Bestellung(
            material_id=material.id,
            menge=menge,
            status='Neu'
        )
        db.session.add(bestellung)
        db.session.commit()
        flash(f"Bestellung über {menge} {material.einheit} {material.name} wurde aufgegeben!", "success")
        return redirect(url_for('material'))
    return render_template('bestellen.html', material=material)

@app.route('/material/delete/<int:id>', methods=['POST'])
@login_required
def delete_material(id):
    material = Material.query.get_or_404(id)
    db.session.delete(material)
    db.session.commit()
    flash("Material erfolgreich gelöscht!", "success")
    return redirect(url_for('material'))

# Termine routes
@app.route('/termine', methods=['GET', 'POST'])
@login_required
def termine():
    if request.method == 'POST':
        titel = request.form['titel']
        beschreibung = request.form.get('beschreibung', '')
        datum_str = request.form['datum']
        try:
            datum = datetime.strptime(datum_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Ungültiges Datum!", "error")
            return redirect(url_for('termine'))

        neuer_termin = Termin(titel=titel, beschreibung=beschreibung, datum=datum)
        db.session.add(neuer_termin)
        db.session.commit()
        flash("Termin erfolgreich hinzugefügt!", "success")
        return redirect(url_for('termine'))

    termine = Termin.query.order_by(Termin.datum.asc()).all()
    return render_template('termine.html', termine=termine)

@app.route('/termine/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_termin(id):
    termin = Termin.query.get_or_404(id)
    if request.method == 'POST':
        termin.titel = request.form['titel']
        termin.beschreibung = request.form.get('beschreibung', '')
        termin.datum = datetime.strptime(request.form['datum'], "%Y-%m-%d").date()
        db.session.commit()
        flash("Termin erfolgreich bearbeitet!", "success")
        return redirect(url_for('termine'))
    return render_template('edit_termin.html', termin=termin)

@app.route('/termine/delete/<int:id>', methods=['POST'])
@login_required
def delete_termin(id):
    termin = Termin.query.get_or_404(id)
    db.session.delete(termin)
    db.session.commit()
    flash("Termin erfolgreich gelöscht!", "success")
    return redirect(url_for('termine'))