from functools import wraps
from flask import session, redirect, url_for, jsonify
from authlib.integrations.flask_client import OAuth
import os

oauth = OAuth()

def init_auth(app):
    oauth.init_app(app)
    
    oauth.register(
        'auth0',
        client_id=os.environ.get('AUTH0_CLIENT_ID'),
        client_secret=os.environ.get('AUTH0_CLIENT_SECRET'),
        client_kwargs={
            'scope': 'openid profile email',
        },
        server_metadata_url=f'https://{os.environ.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
    )
    
    return oauth

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

def get_user():
    return session.get('user')
