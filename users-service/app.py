from flask import Flask, request, jsonify, session
import psycopg2
import psycopg2.extras
import os
import hashlib
import secrets
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'users-secret-key-here'

def get_db_config():
    """Get database configuration from VCAP_SERVICES (Cloud Foundry) or environment variables"""
    vcap_services = os.environ.get('VCAP_SERVICES')
    if vcap_services:
        # Parse Cloud Foundry service binding
        services = json.loads(vcap_services)
        # Try different PostgreSQL service names
        postgres_service = None
        for service_type in ['postgresql', 'postgres', 'elephantsql', 'user-provided']:
            if service_type in services and services[service_type]:
                postgres_service = services[service_type][0]
                break
        
        if postgres_service:
            creds = postgres_service.get('credentials', {})
            # Handle different credential structures
            host = creds.get('primary_host') or creds.get('hostname') or creds.get('host')
            if not host and creds.get('hosts'):
                host = creds.get('hosts')[0]
            database = creds.get('db') or creds.get('name') or creds.get('database')
            user = creds.get('user') or creds.get('username')
            password = creds.get('password')
            port = creds.get('port', 5432)
            return {
                'host': host,
                'port': port,
                'database': database,
                'user': user,
                'password': password
            }
    
    # Fall back to environment variables (Kubernetes/local)
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ.get('USERS_DB_NAME', os.environ.get('DB_NAME', 'users_db')),
        'user': os.environ.get('DB_USER', 'music_user'),
        'password': os.environ.get('DB_PASSWORD', 'music_password')
    }

def get_db_connection():
    """Get database connection"""
    config = get_db_config()
    return psycopg2.connect(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        user=config['user'],
        password=config['password']
    )

def init_users_db():
    """Initialize the users database with default admin user"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
                cur.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    token VARCHAR(255) PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )''')
                
                # Check if admin user exists, if not create it
                cur.execute('SELECT id FROM users WHERE username = %s', ('admin',))
                admin_exists = cur.fetchone()
                if not admin_exists:
                    # Create admin user with password 'admin'
                    admin_password_hash = hashlib.sha256('admin'.encode()).hexdigest()
                    cur.execute('INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)', 
                             ('admin', admin_password_hash, 'admin'))
                    print("Created default admin user: admin/admin")
                
                conn.commit()
    except Exception as e:
        print(f"Error initializing users database: {e}")

init_users_db()

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return hash_password(password) == password_hash

def generate_session_token():
    """Generate a random session token"""
    return secrets.token_hex(32)

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400
    
    username = data['username']
    password = data['password']
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT id, username, password_hash, role FROM users WHERE username = %s', 
                        (username,))
            user = cur.fetchone()
    
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    user_id = user['id']
    db_username = user['username']
    password_hash = user['password_hash']
    role = user['role']
    
    if not verify_password(password, password_hash):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Generate session token
    session_token = generate_session_token()
    
    # Store session in database (in production, use Redis or similar)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO sessions (token, user_id) VALUES (%s, %s)', (session_token, user_id))
            conn.commit()
    
    return jsonify({
        'success': True,
        'token': session_token,
        'user': {
            'id': user_id,
            'username': db_username,
            'role': role
        }
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    data = request.get_json()
    
    if not data or 'token' not in data:
        return jsonify({'error': 'Token is required'}), 400
    
    token = data['token']
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM sessions WHERE token = %s', (token,))
            conn.commit()
    
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/verify', methods=['POST'])
def verify_token():
    """Verify if a session token is valid"""
    data = request.get_json()
    
    if not data or 'token' not in data:
        return jsonify({'error': 'Token is required'}), 400
    
    token = data['token']
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                SELECT s.user_id, u.username, u.role 
                FROM sessions s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.token = %s
            ''', (token,))
            session_data = cur.fetchone()
    
    if not session_data:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    user_id = session_data['user_id']
    username = session_data['username']
    role = session_data['role']
    
    return jsonify({
        'valid': True,
        'user': {
            'id': user_id,
            'username': username,
            'role': role
        }
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (admin only)"""
    data = request.get_json() if request.is_json else {}
    token = data.get('token') or request.args.get('token')
    
    if not token:
        return jsonify({'error': 'Token is required'}), 401
    
    # Verify token and check if user is admin
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                SELECT s.user_id, u.username, u.role 
                FROM sessions s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.token = %s
            ''', (token,))
            session_data = cur.fetchone()
    
    if not session_data:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    user_id = session_data['user_id']
    username = session_data['username']
    role = session_data['role']
    
    if role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get all users
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT id, username, role, created_at FROM users')
            users = cur.fetchall()
    
    return jsonify({
        'users': [
            {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'created_at': str(user['created_at'])
            }
            for user in users
        ]
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'users-service'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True) 