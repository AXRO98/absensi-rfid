# -*- encoding: utf-8 -*-
"""
Copyright (c) 2025 - Create by @keyfin_suratman
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Email, DataRequired, EqualTo

# ========================
# LOGIN & REGISTRATION
# ========================

class LoginForm(FlaskForm):
    username = StringField('Username',
                         id='username_login',
                         validators=[DataRequired()])
    password = PasswordField('Password',
                             id='pwd_login',
                             validators=[DataRequired()])

class CreateAccountForm(FlaskForm):
    username = StringField('Username',
                         id='username_create',
                         validators=[DataRequired()])
    email = StringField('Email',
                      id='email_create',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             id='pwd_create',
                             validators=[DataRequired()])


# ========================
# RESET PASSWORD / OTP
# ========================

class ResetPasswordForm(FlaskForm):
    email = StringField('Email', 
                        id='email_reset', 
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Kirim OTP')


class VerifyOTPForm(FlaskForm):
    email = StringField('Email', 
                        id='email_verify', 
                        validators=[DataRequired(), Email()])
    otp = StringField('OTP', 
                      id='otp_verify', 
                      validators=[DataRequired()])
    submit = SubmitField('Verifikasi OTP')


class SetNewPasswordForm(FlaskForm):
    password = PasswordField('Password Baru', 
                             id='pwd_new', 
                             validators=[DataRequired()])
    confirm_password = PasswordField('Konfirmasi Password Baru', 
                                     id='pwd_confirm', 
                                     validators=[DataRequired(), EqualTo('password', message='Password harus sama')])
    submit = SubmitField('Simpan Password')
