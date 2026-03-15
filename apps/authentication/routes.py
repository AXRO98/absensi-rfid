# -*- encoding: utf-8 -*-

from flask import render_template, redirect, request, url_for, flash, session
from flask_login import (
    current_user,
    login_user,
    logout_user,
    login_required
)
from datetime import datetime, timedelta
from apps.decorators import role_required
from flask_dance.contrib.github import github
from flask_dance.contrib.google import google

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import Users
from apps.config import Config

from apps.authentication.util import verify_pass, hash_pass
from apps.authentication.otp_send import mailer
from apps.authentication.forms import ResetPasswordForm, VerifyOTPForm, SetNewPasswordForm

# Login & Registration

OTP_STORE = {} 
USER_STORE = {}

@blueprint.route("/github")
def login_github():
    """ Github login """
    if not github.authorized:
        return redirect(url_for("github.login"))

    res = github.get("/user")
    return redirect(url_for('home_blueprint.index'))


@blueprint.route("/google")
def login_google():
    """ Google login """
    if not google.authorized:
        return redirect(url_for("google.login"))

    res = google.get("/oauth2/v1/userinfo")
    return redirect(url_for('home_blueprint.index'))

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        # read form data
        user_id  = request.form['username'] # we can have here username OR email
        password = request.form['password']

        # Locate user
        user = Users.find_by_username(user_id)

        # if user not found
        if not user:

            user = Users.find_by_email(user_id)

            if not user:
                return render_template( 'authentication/login.html',
                                        msg='Unknown User or Email',
                                        form=login_form)

        # Check the password
        if verify_pass(password, user.password):

            login_user(user)
            return redirect(url_for('home_blueprint.home'))

        # Something (user or pass) is not ok
        return render_template('authentication/login.html',
                               msg='Wrong user or password',
                               form=login_form)

    if not current_user.is_authenticated:
        return render_template('authentication/login.html',
                               form=login_form)
    return redirect(url_for('home_blueprint.home'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']

        # Check username exists
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('authentication/register.html',
                                   msg='Username already registered',
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('authentication/register.html',
                                   msg='Email already registered',
                                   success=False,
                                   form=create_account_form)

        # else we can create the user
        user = Users(**request.form)
        user.role = "admin"   # default role
        db.session.add(user)
        db.session.commit()

        # Delete user from session
        logout_user()

        return render_template('authentication/register.html',
                               msg='User created successfully.',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('authentication/register.html', form=create_account_form)


@blueprint.route("/add", methods=["POST"])
@login_required
@role_required('superadmin')
def add_user():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role") or "admin"   # default "admin" kalau kosong

    # Validasi form
    if not username or not email or not password:
        flash("Semua field wajib diisi!", "danger")
        return redirect(url_for("users_blueprint.list_users"))

    # Cek username duplikat
    if Users.query.filter_by(username=username).first():
        flash("Username sudah terdaftar!", "danger")
        return redirect(url_for("users_blueprint.list_users"))

    # Cek email duplikat
    if Users.query.filter_by(email=email).first():
        flash("Email sudah terdaftar!", "danger")
        return redirect(url_for("users_blueprint.list_users"))

    # Buat user baru (mirip register)
    new_user = Users(
        username=username,
        email=email,
        password=password,  # plain string saja
        role=role
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        flash("Add Users Success", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Gagal menambahkan user: {str(e)}", "danger")

    return redirect(url_for("users_blueprint.list_users"))

# ===== Step 1: Kirim OTP =====
@blueprint.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        otp = mailer.send_otp(email)

        # simpan OTP + waktu expired 5 menit
        OTP_STORE[email] = {
            "otp": otp,
            "expire": datetime.now() + timedelta(minutes=5)
        }

        flash(f"Kode OTP sudah dikirim ke {email}", "success")
        session['email_reset'] = email
        return redirect(url_for('authentication_blueprint.verify_otp'))

    return render_template('authentication/reset-password.html', form=form)


# ===== Step 2: Verifikasi OTP =====
@blueprint.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('email_reset')  # email yang sedang reset
    if not email:
        flash("Email tidak ditemukan. Silahkan ulangi reset password.", "danger")
        return redirect(url_for('authentication_blueprint.reset_password'))

    if request.method == "POST":
        otp_input = request.form.get("otp", "").strip()
        otp_data = OTP_STORE.get(email)

        if not otp_data:
            flash("OTP belum dikirim atau sudah kadaluarsa.", "danger")
            return redirect(url_for('authentication_blueprint.reset_password'))

        if datetime.now() > otp_data["expire"]:
            flash("OTP sudah kadaluarsa, silahkan kirim ulang.", "danger")
            OTP_STORE.pop(email, None)
            return redirect(url_for('authentication_blueprint.reset_password'))

        if otp_input == otp_data["otp"]:
            flash("OTP benar, silahkan buat password baru.", "success")
            session["otp_verified"] = True
            return redirect(url_for('authentication_blueprint.set_new_password'))
        else:
            flash("OTP salah, coba lagi.", "danger")
            return redirect(request.url)

    return render_template("authentication/verify-otp.html")

# ===== Step 3: Set Password Baru =====
@blueprint.route("/set-new-password", methods=["GET", "POST"])
def set_new_password():
    if not session.get("otp_verified"):
        flash("Silahkan verifikasi OTP terlebih dahulu.", "warning")
        return redirect(url_for("authentication_blueprint.reset_password"))

    form = SetNewPasswordForm()
    email = session.get("email_reset")

    print("Session:", session)  # cek session

    if form.validate_on_submit():
        new_password = form.password.data.strip()
        confirm_password = form.confirm_password.data.strip()
        print("Password input:", new_password, confirm_password)

        # simpan password
        USER_STORE[email] = new_password
        print("USER_STORE:", USER_STORE)

        flash(f"Password berhasil diubah untuk {email}", "success")

        session.pop("otp_verified", None)
        session.pop("email_reset", None)
        OTP_STORE.pop(email, None)

        return redirect(url_for("authentication_blueprint.login"))

    return render_template("authentication/set-new-password.html", form=form)

@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home_blueprint.home'))
  


# Errors

@blueprint.context_processor
def has_github():
    return {'has_github': bool(Config.GITHUB_ID) and bool(Config.GITHUB_SECRET)}

@blueprint.context_processor
def has_google():
    return {'has_google': bool(Config.GOOGLE_ID) and bool(Config.GOOGLE_SECRET)}

@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect('/login')
