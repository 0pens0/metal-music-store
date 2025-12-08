# Music Store - Microservices Architecture

A modern music store application built with a microservices architecture, featuring separate services for store management, shopping cart, and order processing.

## 🏗️ Architecture Overview

The application is split into three independent microservices:

### 1. **Store Service** (Port 5000)
- **Purpose**: Main store interface and album management
- **Features**:
  - Browse albums
  - Add new albums (admin)
  - Delete albums (admin)
  - View store statistics
  - Album catalog management
- **Database**: PostgreSQL (external database service)

### 2. **Cart Service** (Port 5002)
- **Purpose**: Shopping cart management and checkout
- **Features**:
  - Add items to cart
  - Update quantities
  - Remove items
  - Checkout process
  - Credit card payment simulation
- **Database**: PostgreSQL (separate database or schema)

### 3. **Order Service** (Port 5001)
- **Purpose**: Order processing and management
- **Features**:
  - Create orders
  - Order tracking
  - Order dashboard
  - Order history
- **Database**: PostgreSQL (separate database or schema)

### 4. **Database Service** (Port 5432)
- **Purpose**: Centralized data storage
- **Features**:
  - PostgreSQL database
  - Album and order data storage
  - Automatic schema initialization
  - Data persistence
- **Database**: PostgreSQL (`music_store`)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the project**:
   ```bash
   cd exmaple-music-store-1
   ```

2. **Start all services**:
   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - **Store**: http://localhost:5000
   - **Cart**: http://localhost:5002
   - **Orders Dashboard**: http://localhost:5001
   - **Database**: localhost:5432 (PostgreSQL)

### Manual Setup

1. **Store Service**:
   ```bash
   cd exmaple-music-store-1
   pip install -r requirements.txt
   python app.py
   ```

2. **Cart Service**:
   ```bash
   cd cart-service
   pip install -r requirements.txt
   python app.py
   ```

3. **Order Service**:
   ```bash
   cd order-service
   pip install -r requirements.txt
   python app.py
   ```

## 🔄 Service Communication

### API Endpoints

#### Store Service APIs
- `GET /api/album/{id}` - Get album details

#### Cart Service APIs
- `POST /add_to_cart` - Add item to cart
- `POST /update_quantity` - Update item quantity
- `POST /remove_item` - Remove item from cart
- `GET /checkout` - View checkout page
- `POST /process_payment` - Process payment

#### Order Service APIs
- `POST /api/orders` - Create new order
- `GET /api/orders` - Get all orders
- `GET /api/orders/{id}` - Get specific order
- `PUT /api/orders/{id}/status` - Update order status

### Service Dependencies
```
Store Service ←→ Cart Service ←→ Order Service
```

## 💳 Payment Flow

1. **Add to Cart**: User adds albums to cart from store
2. **Cart Management**: User can modify quantities or remove items
3. **Checkout**: User proceeds to checkout with cart items
4. **Payment**: Fake credit card payment simulation
5. **Order Creation**: Cart service sends order to order service
6. **Success**: User sees confirmation and cart is cleared

## 🎨 Features

### Store Service
- ✅ Modern, responsive UI with tabbed interface
- ✅ Album catalog with cover images
- ✅ Admin panel for adding albums
- ✅ Delete album functionality
- ✅ Store statistics dashboard
- ✅ File upload for album covers
- ✅ PostgreSQL database integration

### Cart Service
- ✅ Shopping cart with persistent storage
- ✅ Quantity management
- ✅ Real-time total calculation
- ✅ Professional checkout interface
- ✅ Credit card payment simulation
- ✅ Input validation and formatting

### Order Service
- ✅ Order creation and tracking
- ✅ Order dashboard with statistics
- ✅ Detailed order views
- ✅ Order status management
- ✅ Revenue tracking

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL (all services)
- **Frontend**: HTML, CSS, JavaScript
- **Containerization**: Docker & Docker Compose
- **Platforms**: Kubernetes, Cloud Foundry, Docker Compose
- **Communication**: HTTP REST APIs

## 📁 Project Structure

```
exmaple-music-store-1/
├── app.py                 # Store service
├── requirements.txt       # Store service dependencies
├── Dockerfile            # Store service container
├── docker-compose.yml    # Service orchestration
├── k8s-deployment.yaml   # Kubernetes deployment
├── VERSION               # Version tracking
├── cart-service/         # Cart microservice
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── order-service/        # Order microservice
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── database-service/     # Database service
│   ├── docker-compose.yml
│   └── init.sql
└── static/              # Static assets
    └── covers/          # Album cover images
```

## 🔧 Configuration

### Environment Variables

#### Store Service
- `CART_SERVICE_URL`: URL of cart service (default: http://localhost:5002)
- `ORDER_SERVICE_URL`: URL of order service (default: http://localhost:5001)
- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)
- `DB_NAME`: Database name (default: music_store)
- `DB_USER`: Database user (default: music_user)
- `DB_PASSWORD`: Database password (default: music_password)

#### Cart Service
- `STORE_SERVICE_URL`: URL of store service (default: http://localhost:5000)
- `ORDER_SERVICE_URL`: URL of order service (default: http://localhost:5001)
- `CART_DB_PATH`: Cart database file path (default: cart.db)

#### Order Service
- `STORE_SERVICE_URL`: URL of store service (default: http://localhost:5000)
- `ORDER_DB_PATH`: Order database file path (default: orders.db)

## 🚀 Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f k8s-database-deployment.yaml
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-cart-deployment.yaml
kubectl apply -f k8s-order-deployment.yaml
```

### Cloud Foundry

#### Prerequisites
- Cloud Foundry CLI installed
- Access to `tanzu-platfrom-demo` organization
- PostgreSQL service available in the organization

#### Setup

1. **Login to Cloud Foundry**:
   ```bash
   cf login -a <api-endpoint> -u <username> -o tanzu-platfrom-demo
   ```

2. **Create Space** (if not exists):
   ```bash
   cf create-space metal-music-store -o tanzu-platfrom-demo
   ```

3. **Target the Space**:
   ```bash
   cf target -o tanzu-platfrom-demo -s metal-music-store
   ```

4. **Create PostgreSQL Service** (if not exists):
   ```bash
   cf create-service postgresql <plan-name> postgres
   ```
   Note: Wait for the service to be created before proceeding.

5. **Deploy All Services**:
   ```bash
   cf push
   ```
   This will deploy all 4 services (store-service, cart-service, order-service, users-service) from the single `manifest.yml` file.

#### Service Routes

After deployment, services will be available at:
- **Store Service**: `https://store-service-metal-music-store.apps.tanzuplatformdemo.com`
- **Cart Service**: `https://cart-service-metal-music-store.apps.tanzuplatformdemo.com`
- **Order Service**: `https://order-service-metal-music-store.apps.tanzuplatformdemo.com`
- **Users Service**: `https://users-service-metal-music-store.apps.tanzuplatformdemo.com`

#### Notes
- All services use PostgreSQL (migrated from SQLite for Cloud Foundry compatibility)
- Each service uses a separate database within the same PostgreSQL instance
- Service URLs are configured automatically via the manifest
- Health check endpoints are available at `/health` for all services

### Individual Services
```bash
# Store Service
docker build -t music-store .
docker run -p 5000:5000 music-store

# Cart Service
docker build -t cart-service ./cart-service
docker run -p 5002:5002 cart-service

# Order Service
docker build -t order-service ./order-service
docker run -p 5001:5001 order-service
```

## 🔍 Monitoring

### Service Health Checks
- Store Service: http://localhost:5000/
- Cart Service: http://localhost:5002/
- Order Service: http://localhost:5001/

### Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs store-service
docker-compose logs cart-service
docker-compose logs order-service
```

## 🧪 Testing

### Manual Testing Flow
1. **Add Albums**: Use admin tab to add albums
2. **Browse Store**: View albums in shop tab
3. **Add to Cart**: Add albums to shopping cart
4. **Manage Cart**: Update quantities or remove items
5. **Checkout**: Proceed to payment
6. **Complete Order**: Use fake credit card details
7. **View Orders**: Check order dashboard

### Test Credit Card Details
- **Card Number**: Any 13-19 digit number
- **Expiry**: Any future date (MM/YY format)
- **CVV**: Any 3-4 digit number

## 🔒 Security Notes

- This is a demo application with simulated payments
- No real payment processing is implemented
- Session management uses simple Flask sessions
- All services use PostgreSQL (production-ready)
- Database connections support both Cloud Foundry (VCAP_SERVICES) and Kubernetes/local (environment variables)
- No authentication/authorization implemented

## 🚧 Future Enhancements

- [ ] User authentication and authorization
- [ ] Real payment gateway integration
- [ ] Email notifications
- [ ] Inventory management
- [ ] Advanced search and filtering
- [ ] User reviews and ratings
- [ ] Recommendation system
- [ ] Analytics dashboard
- [ ] API rate limiting
- [ ] Service mesh implementation

## 📝 License

This project is for educational and demonstration purposes. 