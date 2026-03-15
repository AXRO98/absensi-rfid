from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from apps import db
from flask_login import login_required, current_user
from apps.decorators import role_required
from apps.authentication.models import Users, hash_pass

users_blueprint = Blueprint('users_blueprint', __name__, url_prefix='/users')

@users_blueprint.route('/')
@login_required
@role_required('superadmin')
def list_users():
    try:
        users = Users.query.order_by(Users.id.asc()).all()
    except Exception as e:
        # kalau query error, tampilkan error page
        abort(500, description=f"Database error: {str(e)}")

    return render_template("users_settings/list_user.html", users=users)

@users_blueprint.route("/update/<int:user_id>", methods=["POST"])
@login_required
@role_required('superadmin')
def update_user(user_id):
    user = Users.query.get_or_404(user_id)

    user.username = request.form.get("username")
    user.email = request.form.get("email")
    user.role = request.form.get("role")

    new_password = request.form.get("password")
    if new_password:
        user.password = hash_pass(new_password)

    db.session.commit()
    flash("User updated successfully!", "success")
    return redirect(url_for("users_blueprint.list_users"))

@users_blueprint.route("/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required('superadmin')
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for("users_blueprint.list_users"))
    print("Deleted user:", user.id, user.username)


@users_blueprint.route('/whatsapp-bot-settings')
@login_required
@role_required('superadmin')
def whatsapp_bot_settings():
    return render_template("users_settings/whatsapp_settings.html")

@users_blueprint.route('/whatsapp-bot')
@login_required
@role_required('superadmin')
def whatsapp_bot():
    #return render_template("users_settings/whatsapp_bot.html")
    return render_template("users_settings/whatsapp_bot_fonnte/add_device.html")