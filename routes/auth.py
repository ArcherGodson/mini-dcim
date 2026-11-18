import os
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, redirect, url_for
from models.base import db
from models.auth import ApiToken

auth_bp = Blueprint('auth', __name__)

def optional_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        env_token = os.environ.get("IPAM_API_TOKEN", "").strip()
        active_tokens = ApiToken.query.filter_by(is_active=True).all()
        if not env_token and not active_tokens:
            return f(*args, **kwargs)
        provided = ""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            provided = auth_header[7:].strip()
        elif request.headers.get("X-API-Key"):
            provided = request.headers.get("X-API-Key", "").strip()
        if not provided:
            return jsonify({"error": "API token required"}), 401
        if env_token and provided == env_token:
            return f(*args, **kwargs)
        for tok in active_tokens:
            if tok.token == provided:
                tok.last_used_at = datetime.utcnow()
                db.session.commit()
                return f(*args, **kwargs)
        return jsonify({"error": "Invalid or disabled API token"}), 403
    return decorated

@auth_bp.route('/tokens/create', methods=['POST'])
def create_token():
    name = request.form.get('name', 'API Token').strip() or 'API Token'
    db.session.add(ApiToken(name=name, token=ApiToken.generate_key(), is_active=True))
    db.session.commit()
    return redirect(url_for('dashboard.config'))

@auth_bp.route('/tokens/toggle/<int:tid>', methods=['POST'])
def toggle_token(tid):
    tok = ApiToken.query.get_or_404(tid)
    tok.is_active = not tok.is_active
    db.session.commit()
    return redirect(url_for('dashboard.config'))

@auth_bp.route('/tokens/delete/<int:tid>', methods=['GET', 'POST', 'DELETE'])
def delete_token(tid):
    tok = ApiToken.query.get_or_404(tid)
    db.session.delete(tok)
    db.session.commit()
    if request.method == 'DELETE' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'removed': [f'token-{tid}']})
    return redirect(url_for('dashboard.config'))
