"""
SSO Authentication Module
Handles OAuth2/OIDC authentication flow with Cloud Foundry SSO
"""
from functools import wraps
from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import OAuth2Error
import sso_config
import requests


# Global OAuth client (will be initialized in init_sso)
oauth = OAuth()


def init_sso(app: Flask):
    """
    Initialize SSO OAuth client with Flask app.
    Should be called during app initialization.
    """
    sso_cfg = sso_config.get_sso_config()
    if not sso_cfg:
        print("SSO not configured - SSO features will be disabled")
        return False
    
    oauth.init_app(app)
    
    # Register OAuth2 client
    oauth.register(
        name='sso',
        client_id=sso_cfg['client_id'],
        client_secret=sso_cfg['client_secret'],
        server_metadata_url=sso_cfg['server_metadata_url'],
        client_kwargs={
            'scope': 'openid profile email'
        }
    )
    
    return True


def require_sso(f):
    """
    Decorator to protect routes that require SSO authentication.
    Redirects to login if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not sso_config.is_sso_configured():
            # SSO not configured, allow access (for development)
            return f(*args, **kwargs)
        
        if 'sso_user' not in session:
            # Store the original URL to redirect back after login
            session['next_url'] = request.url
            return redirect(url_for('sso_login'))
        
        return f(*args, **kwargs)
    return decorated_function


def is_authenticated():
    """Check if user is authenticated via SSO"""
    return 'sso_user' in session


def get_current_user():
    """Get current authenticated user info"""
    return session.get('sso_user')


def sso_login():
    """Initiate SSO login flow"""
    if not sso_config.is_sso_configured():
        from flask import jsonify
        return jsonify({'error': 'SSO not configured'}), 503
    
    redirect_uri = url_for('sso_callback', _external=True)
    return oauth.sso.authorize_redirect(redirect_uri)


def sso_callback():
    """Handle OAuth2 callback from SSO"""
    if not sso_config.is_sso_configured():
        return jsonify({'error': 'SSO not configured'}), 503
    
    try:
        # Exchange authorization code for token
        token = oauth.sso.authorize_access_token()
        
        # Fetch user info
        user_info = oauth.sso.get('userinfo', token=token)
        
        if user_info:
            # Store user info in session
            session['sso_user'] = {
                'id': user_info.get('user_id') or user_info.get('sub'),
                'username': user_info.get('user_name') or user_info.get('preferred_username') or user_info.get('email'),
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'token': token
            }
            session.permanent = True
            
            # Redirect to original URL or home
            next_url = session.pop('next_url', None) or url_for('index')
            return redirect(next_url)
        else:
            return jsonify({'error': 'Failed to fetch user info'}), 500
            
    except OAuth2Error as e:
        print(f"OAuth2 error during callback: {e}")
        return jsonify({'error': f'OAuth2 error: {str(e)}'}), 400
    except Exception as e:
        print(f"Error during SSO callback: {e}")
        return jsonify({'error': f'Authentication error: {str(e)}'}), 500


def sso_logout():
    """Handle SSO logout"""
    # Clear session
    session.pop('sso_user', None)
    session.pop('next_url', None)
    
    # If SSO is configured, redirect to SSO logout endpoint
    sso_cfg = sso_config.get_sso_config()
    if sso_cfg:
        logout_url = f"{sso_cfg['auth_domain']}/logout"
        return redirect(logout_url)
    
    return redirect(url_for('index'))

