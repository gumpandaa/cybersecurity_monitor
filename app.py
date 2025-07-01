from flask import Flask, render_template, request, redirect, url_for, session, flash
from email_validator import validate_email, EmailNotValidError
import requests
from flask_sqlalchemy import SQLAlchemy
import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

app = Flask(__name__)

app.secret_key = 'rahasia-super-aman'  # ubah jadi lebih aman di produksi
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hasil.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class HasilAnalisis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    skor = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    rekomendasi = db.Column(db.Text, nullable=False)
    tanggal = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

def cek_breach(email):
    url = f"https://hackcheck.woventeams.com/api/v4/breachedaccount/{email}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return []
        else:
            return None
    except:
        return None

def hitung_skor(pelanggaran):
    skor = 100
    tahun_sekarang = datetime.datetime.now().year

    for pel in pelanggaran:
        skor -= 5  # tiap breach

        if 'password' in pel.get('DataClasses', []):
            skor -= 10
        if 'email' in pel.get('DataClasses', []):
            skor -= 5

        if pel['Name'].lower() in ['linkedin', 'facebook', 'twitter', 'gmail', 'dropbox']:
            skor -= 10

        tahun = pel.get('BreachDate', '').split('-')[0]
        if tahun.isdigit():
            selisih = tahun_sekarang - int(tahun)
            if selisih <= 2:
                skor -= 10
            elif selisih <= 5:
                skor -= 5

    return max(skor, 0)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analisis', methods=['POST'])
def analisis():
    email = request.form['email']

    try:
        valid = validate_email(email)
        email = valid.email

        pelanggaran = cek_breach(email)

        if pelanggaran is None:
            return "<h2>Gagal memeriksa breach (jaringan atau API error)</h2>"

        if pelanggaran:
            score = hitung_skor(pelanggaran)
            if score >= 90:
                status = "Sangat Aman ✅"
            elif score >= 70:
                status = "Aman ✅"
            elif score >= 50:
                status = "Waspada ⚠️"
            else:
                status = "Bahaya ❌"
            rekomendasi = [
                "Segera ganti password yang digunakan di akun-akun lama.",
                "Aktifkan verifikasi dua langkah (2FA).",
                "Gunakan password yang unik untuk setiap akun.",
            ]
        else:
            score = 100
            status = "Sangat Aman ✅"
            rekomendasi = [
                "Akun Anda tidak ditemukan di pelanggaran data.",
                "Tetap gunakan password kuat dan unik.",
                "Waspadai phishing dan scam email."
            ]

        rekom_str = "; ".join(rekomendasi)
        hasil = HasilAnalisis(
            email=email,
            skor=score,
            status=status,
            rekomendasi=rekom_str
        )
        db.session.add(hasil)
        db.session.commit()

        return render_template('hasil.html', email=email, score=score, status=status, pelanggaran=pelanggaran, rekomendasi=rekomendasi)

    except EmailNotValidError as e:
        return f"<h2>Email tidak valid: {e}</h2>"

@app.route('/data')
@login_required
def data():
    hasil_list = HasilAnalisis.query.order_by(HasilAnalisis.tanggal.desc()).all()
    return render_template('data.html', hasil_list=hasil_list)

@app.route('/statistik')
@login_required
def statistik():
    jumlah_analisis = HasilAnalisis.query.count()
    rata_rata_skor = db.session.query(db.func.avg(HasilAnalisis.skor)).scalar()
    tingkat_status = db.session.query(HasilAnalisis.status, db.func.count(HasilAnalisis.id)).group_by(HasilAnalisis.status).all()

    return render_template('statistik.html',
                           jumlah=jumlah_analisis,
                           rata_rata=round(rata_rata_skor or 0, 2),
                           distribusi=tingkat_status)

@app.route('/hapus/<int:id>', methods=['POST'])
@login_required
def hapus(id):
    hasil = HasilAnalisis.query.get_or_404(id)
    db.session.delete(hasil)
    db.session.commit()
    return "<script>location.href='/data';</script>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('data'))
        else:
            error = "Username atau password salah"
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return "<script>location.href='/';</script>"

if __name__ == '__main__':
    app.run(debug=True)
