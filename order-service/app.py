from flask import Flask, render_template_string, request, jsonify
import psycopg2
import psycopg2.extras
import os
import json
from datetime import datetime

app = Flask(__name__)

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
        'database': os.environ.get('ORDER_DB_NAME', os.environ.get('DB_NAME', 'order_db')),
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

def init_order_db():
    """Initialize order database tables"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    order_number VARCHAR(255) UNIQUE NOT NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
                cur.execute('''CREATE TABLE IF NOT EXISTS order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    album_id INTEGER NOT NULL,
                    album_name VARCHAR(255) NOT NULL,
                    artist VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    quantity INTEGER NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
                )''')
                conn.commit()
    except Exception as e:
        print(f"Error initializing order database: {e}")

init_order_db()

def generate_order_number():
    """Generate a unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    import random
    random_suffix = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    return f"ORD-{timestamp}-{random_suffix}"

@app.route('/api/orders', methods=['POST'])
def create_order():
    """API endpoint to create a new order"""
    try:
        data = request.get_json()
        
        if not data or 'items' not in data or 'total' not in data:
            return jsonify({'error': 'Invalid order data'}), 400
        
        session_id = data.get('session_id')
        items = data['items']
        total = data['total']
        
        if not items:
            return jsonify({'error': 'No items in order'}), 400
        
        # Create order
        order_number = generate_order_number()
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Insert order
                cur.execute('''
                    INSERT INTO orders (session_id, order_number, total_amount, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                ''', (session_id, order_number, total, 'confirmed'))
                
                order_id = cur.fetchone()[0]
                
                # Insert order items
                for item in items:
                    cur.execute('''
                        INSERT INTO order_items (order_id, album_id, album_name, artist, price, quantity)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (order_id, item['album_id'], item['album_name'], item['artist'], item['price'], item['quantity']))
                
                conn.commit()
        
        return jsonify({
            'order_id': order_id,
            'order_number': order_number,
            'status': 'confirmed',
            'total': total
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """API endpoint to get all orders"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute('''
                    SELECT o.id, o.order_number, o.total_amount, o.status, o.created_at,
                           COUNT(oi.id) as item_count
                    FROM orders o
                    LEFT JOIN order_items oi ON o.id = oi.order_id
                    GROUP BY o.id
                    ORDER BY o.created_at DESC
                ''')
                orders = cur.fetchall()
        
        return jsonify([{
            'id': order['id'],
            'order_number': order['order_number'],
            'total_amount': float(order['total_amount']),
            'status': order['status'],
            'created_at': str(order['created_at']),
            'item_count': order['item_count']
        } for order in orders]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """API endpoint to get a specific order with items"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Get order details
                cur.execute('''
                    SELECT id, order_number, total_amount, status, created_at
                    FROM orders WHERE id = %s
                ''', (order_id,))
                order = cur.fetchone()
                
                if not order:
                    return jsonify({'error': 'Order not found'}), 404
                
                # Get order items
                cur.execute('''
                    SELECT album_id, album_name, artist, price, quantity
                    FROM order_items WHERE order_id = %s
                ''', (order_id,))
                items = cur.fetchall()
        
        return jsonify({
            'id': order['id'],
            'order_number': order['order_number'],
            'total_amount': float(order['total_amount']),
            'status': order['status'],
            'created_at': str(order['created_at']),
            'items': [{
                'album_id': item['album_id'],
                'album_name': item['album_name'],
                'artist': item['artist'],
                'price': float(item['price']),
                'quantity': item['quantity']
            } for item in items]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """API endpoint to update order status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE orders SET status = %s WHERE id = %s', (new_status, order_id))
                
                if cur.rowcount == 0:
                    return jsonify({'error': 'Order not found'}), 404
                
                conn.commit()
        
        return jsonify({'message': 'Order status updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def orders_dashboard():
    """Dashboard to view all orders"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                SELECT o.id, o.order_number, o.total_amount, o.status, o.created_at,
                       COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                GROUP BY o.id
                ORDER BY o.created_at DESC
            ''')
            orders = cur.fetchall()
    
    return render_template_string(ORDERS_DASHBOARD_HTML, orders=orders)

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    """Detailed view of a specific order"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get order details
            cur.execute('''
                SELECT id, order_number, total_amount, status, created_at
                FROM orders WHERE id = %s
            ''', (order_id,))
            order = cur.fetchone()
            
            if not order:
                return "Order not found", 404
            
            # Get order items
            cur.execute('''
                SELECT album_id, album_name, artist, price, quantity
                FROM order_items WHERE order_id = %s
            ''', (order_id,))
            items = cur.fetchall()
    
    return render_template_string(ORDER_DETAIL_HTML, order=order, items=items)

# HTML Templates
ORDERS_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orders Dashboard - Metal Music Store</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #ffffff;
            color: #1a1a1a;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }

        /* Header */
        .header {
            background: #1a1a1a;
            color: white;
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.3);
            margin-bottom: 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            color: #ffffff;
            letter-spacing: -0.5px;
        }

        .dashboard-card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e1e5e9;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            color: #1a1a1a;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #e1e5e9;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 5px;
            color: #667eea;
        }

        .stat-label {
            font-size: 1rem;
            color: #666;
            font-weight: 600;
        }

        .orders-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .orders-table th,
        .orders-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e1e5e9;
            color: #1a1a1a;
        }

        .orders-table th {
            background: #f8f9fa;
            font-weight: 700;
            color: #1a1a1a;
        }

        .orders-table tr:hover {
            background: #f8f9fa;
        }

        .status-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }

        .status-pending {
            background: #fff3cd;
            color: #856404;
        }

        .status-confirmed {
            background: #d1ecf1;
            color: #0c5460;
        }

        .status-shipped {
            background: #d4edda;
            color: #155724;
        }

        .status-delivered {
            background: #c3e6cb;
            color: #155724;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }

        @media (max-width: 768px) {
            .orders-table {
                font-size: 0.9rem;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 0 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📦 Orders Dashboard</h1>
            <p>Track your brutal metal orders</p>
            <p>Manage all customer orders</p>
        </div>

        <div class="dashboard-card">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{orders|length}}</div>
                    <div class="stat-label">Total Orders</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{"%.2f"|format(orders|sum(attribute='total_amount'))}}</div>
                    <div class="stat-label">Total Revenue</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{orders|selectattr('status', 'equalto', 'pending')|list|length}}</div>
                    <div class="stat-label">Pending Orders</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{orders|selectattr('status', 'equalto', 'confirmed')|list|length}}</div>
                    <div class="stat-label">Confirmed Orders</div>
                </div>
            </div>

            {% if orders %}
            <table class="orders-table">
                <thead>
                    <tr>
                        <th>Order #</th>
                        <th>Date</th>
                        <th>Items</th>
                        <th>Total</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for order in orders %}
                    <tr>
                        <td><strong>{{order.order_number}}</strong></td>
                        <td>{{order.created_at[:10]}}</td>
                        <td>{{order.item_count}} items</td>
                        <td>${{"%.2f"|format(order.total_amount)}}</td>
                        <td>
                            <span class="status-badge status-{{order.status}}">{{order.status|title}}</span>
                        </td>
                        <td>
                            <a href="/order/{{order.id}}" class="btn">View Details</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty-state">
                <p>No orders yet.</p>
                <p>Orders will appear here once customers make purchases.</p>
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

ORDER_DETAIL_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Details - Metal Music Store</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #ffffff;
            color: #1a1a1a;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }

        /* Header */
        .header {
            background: #1a1a1a;
            color: white;
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.3);
            margin-bottom: 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            color: #ffffff;
            letter-spacing: -0.5px;
        }

        .order-card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e1e5e9;
        }

        .order-header {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
            border: 1px solid #e1e5e9;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .order-header h3 {
            color: #1a1a1a;
            margin-bottom: 15px;
            font-weight: 700;
        }

        .order-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .info-item {
            margin-bottom: 10px;
        }

        .info-label {
            font-weight: 600;
            color: #555;
        }

        .info-value {
            color: #333;
        }

        .items-section {
            margin-top: 30px;
        }

        .items-section h3 {
            color: #667eea;
            margin-bottom: 20px;
        }

        .item-list {
            list-style: none;
        }

        .item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
            border: 1px solid #e1e5e9;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        .item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }

        .item-name {
            font-weight: 600;
            color: #333;
        }

        .item-price {
            color: #667eea;
            font-weight: bold;
        }

        .item-details {
            color: #666;
            font-size: 0.9rem;
        }

        .order-total {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-top: 30px;
            text-align: center;
        }

        .total-amount {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        @media (max-width: 768px) {
            .order-info {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 0 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Order Details</h1>
            <p>Order #{{order.order_number}}</p>
        </div>

        <div class="order-card">
            <div class="order-header">
                <h3>Order Information</h3>
                <div class="order-info">
                    <div class="info-item">
                        <div class="info-label">Order Number:</div>
                        <div class="info-value">{{order.order_number}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Date:</div>
                        <div class="info-value">{{order.created_at}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Status:</div>
                        <div class="info-value">{{order.status|title}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Items:</div>
                        <div class="info-value">{{items|length}} items</div>
                    </div>
                </div>
            </div>

            <div class="items-section">
                <h3>Order Items</h3>
                <ul class="item-list">
                    {% for item in items %}
                    <li class="item">
                        <div class="item-header">
                            <div class="item-name">{{item.album_name}}</div>
                            <div class="item-price">${{"%.2f"|format(item.price * item.quantity)}}</div>
                        </div>
                        <div class="item-details">
                            by {{item.artist}} • {{item.quantity}}x ${{"%.2f"|format(item.price)}} each
                        </div>
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <div class="order-total">
                <div class="total-amount">${{"%.2f"|format(order.total_amount)}}</div>
                <div>Total Amount</div>
            </div>

            <div style="text-align: center;">
                <a href="/" class="btn">Back to Orders</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'order-service'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True) 