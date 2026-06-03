"""
Admin authentication routes (Flask-Login).
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import UserMixin, login_user, logout_user, login_required, current_user
from extensions import login_manager

auth_bp = Blueprint('auth', __name__)


class AdminUser(UserMixin):
    """Single admin user backed by environment credentials."""

    def __init__(self, username):
        self.id = username
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    admin_username = current_app.config.get('ADMIN_USERNAME', 'admin')
    if user_id == admin_username:
        return AdminUser(admin_username)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    from flask import jsonify
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    return redirect(url_for('auth.login', next=request.url))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        expected_user = current_app.config.get('ADMIN_USERNAME', 'admin')
        expected_password = current_app.config.get('ADMIN_PASSWORD', 'admin')

        if username == expected_user and password == expected_password:
            login_user(AdminUser(username), remember=True)
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('dashboard.index'))

        flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
