from app import db, User, bcrypt, app

def create_admin_user():
    with app.app_context():
        # Ganti username dan password jika ingin custom
        username = "admin"
        password_plain = "admin123"

        # Enkripsi password
        hashed_password = bcrypt.generate_password_hash(password_plain).decode('utf-8')

        # Buat objek user baru
        user = User(username=username, password=hashed_password)

        # Simpan ke database
        db.session.add(user)
        db.session.commit()
        print(f"✅ User '{username}' berhasil dibuat.")

if __name__ == '__main__':
    create_admin_user()
