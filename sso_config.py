"""
SSO Configuration Module
Parses VCAP_SERVICES to extract Cloud Foundry SSO service credentials
and provides OAuth2/OIDC configuration for Authlib
"""
import os
import json
from typing import Optional, Dict


def get_sso_config() -> Optional[Dict[str, str]]:
    """
    Parse VCAP_SERVICES to extract SSO service credentials.
    Returns OAuth2 configuration dict for Authlib, or None if SSO not configured.
    """
    vcap_services = os.environ.get('VCAP_SERVICES')
    if not vcap_services:
        return None
    
    try:
        services = json.loads(vcap_services)
        
        # Look for SSO service - try multiple possible service types/names
        sso_service = None
        sso_service_types = ['p-identity', 'p-identity-sso', 'sso', 'uaa']
        
        for service_type in sso_service_types:
            if service_type in services and services[service_type]:
                sso_service = services[service_type][0]
                break
        
        # Also check user-provided services for SSO
        if not sso_service and 'user-provided' in services:
            for service in services['user-provided']:
                service_name = service.get('name', '').lower()
                if 'sso' in service_name or 'identity' in service_name:
                    sso_service = service
                    break
        
        if not sso_service:
            return None
        
        creds = sso_service.get('credentials', {})
        
        # Extract SSO credentials
        auth_domain = creds.get('auth_domain') or creds.get('issuer')
        client_id = creds.get('client_id')
        client_secret = creds.get('client_secret')
        
        if not auth_domain or not client_id or not client_secret:
            print("SSO service found but missing required credentials")
            return None
        
        # Build OAuth2 provider URLs
        # Ensure auth_domain doesn't have trailing slash
        auth_domain = auth_domain.rstrip('/')
        
        config = {
            'server_metadata_url': f'{auth_domain}/.well-known/openid-configuration',
            'client_id': client_id,
            'client_secret': client_secret,
            'authorize_url': f'{auth_domain}/oauth/authorize',
            'token_url': f'{auth_domain}/oauth/token',
            'userinfo_url': f'{auth_domain}/userinfo',
            'jwks_url': f'{auth_domain}/.well-known/jwks.json',
            'auth_domain': auth_domain
        }
        
        return config
        
    except Exception as e:
        print(f"Error parsing VCAP_SERVICES for SSO: {e}")
        return None


def is_sso_configured() -> bool:
    """Check if SSO is configured"""
    return get_sso_config() is not None


