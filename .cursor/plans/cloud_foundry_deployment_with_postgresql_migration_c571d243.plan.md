---
name: Cloud Foundry Deployment with PostgreSQL Migration
overview: Add Cloud Foundry deployment support with single multi-app manifest, migrate SQLite services to PostgreSQL, fork to 0pens0 GitHub, create CF space, and enable single-command deployment.
todos: []
---

# Cloud Foundry Deployment with PostgreSQL Migration

## Overview

Add Cloud Foundry platform deployment support with a single multi-app manifest that deploys all services with one `cf push`. Migrate SQLite services to PostgreSQL, fork repository to 0pens0 GitHub, and create a Cloud Foundry space for deployment.

## Requirements

- Fork repository to `0pens0/metal-music-store` on GitHub
- Create CF space `metal-music-store` in `tanzu-platfrom-demo` org
- Single `manifest.yml` at root for all services (multi-app manifest)
- Migrate cart, order, and users services from SQLite to PostgreSQL
- Use existing PostgreSQL service in the org
- Support both Kubernetes and Cloud Foundry deployments
- Single `cf push` command deploys all services

## Implementation Steps

### 1. Fork Repository to 0pens0 GitHub

- Fork `NiranEC77/metal-music-store` to `0pens0/metal-music-store`
- Update git remote to point to forked repository

### 2. Create Cloud Foundry Space

- Create space `metal-music-store` in org `tanzu-platfrom-demo`
- Verify PostgreSQL service is available in the org

### 3. Create Single Multi-App Manifest

Create `manifest.yml` at root with all 4 services:

- `store-service` - Main Flask app
- `cart-service` - Cart management
- `order-service` - Order processing  
- `users-service` - User authentication

Each app definition includes:

- Name, buildpack (python), memory/disk
- Routes (using app names)
- Environment variables for inter-service URLs
- Service bindings to PostgreSQL
- Health check endpoints

### 4. Migrate SQLite to PostgreSQL

Update cart, order, and users services:

- Replace SQLite with PostgreSQL connections
- Parse VCAP_SERVICES for Cloud Foundry
- Fall back to env vars for Kubernetes/local
- Update database schemas and initialization
- Each service uses separate database or schema

**Files to modify:**

- `cart-service/app.py` - Replace sqlite3 with psycopg2
- `order-service/app.py` - Replace sqlite3 with psycopg2
- `users-service/app.py` - Replace sqlite3 with psycopg2
- Add `psycopg2` to requirements.txt for each service

### 5. Update Port Binding

All Flask apps must read `PORT` env var (CF provides this):

- `app.py` (store service)
- `cart-service/app.py`
- `order-service/app.py`
- `users-service/app.py`

### 6. Add VCAP_SERVICES Support

Update database connection logic:

- Check for `VCAP_SERVICES` (Cloud Foundry)
- Parse PostgreSQL credentials from JSON
- Fall back to environment variables (Kubernetes)

**Files to modify:**

- `app.py` - Store service DB connection
- `cart-service/app.py` - Cart service DB connection
- `order-service/app.py` - Order service DB connection
- `users-service/app.py` - Users service DB connection

### 7. Update Inter-Service Communication

Configure service URLs based on deployment target:

- Cloud Foundry: Use route URLs (from manifest routes)
- Kubernetes: Use service names (existing)

**Files to modify:**

- `app.py` - CART_SERVICE_URL, ORDER_SERVICE_URL, USERS_SERVICE_URL
- `cart-service/app.py` - STORE_SERVICE_URL, ORDER_SERVICE_URL
- `order-service/app.py` - STORE_SERVICE_URL

### 8. Add Health Check Endpoints

Ensure all services have `/health` endpoints for CF health checks.

### 9. Update Documentation

Add Cloud Foundry deployment section to README with:

- Prerequisites
- Space creation
- Deployment steps
- Service binding info

## File Structure

```
metal-music-store/
├── manifest.yml                    # NEW: Single multi-app CF manifest
├── app.py                          # MODIFY: Port, VCAP_SERVICES, route URLs
├── requirements.txt                # MODIFY: Add psycopg2 if needed
├── cart-service/
│   ├── app.py                      # MODIFY: SQLite→PostgreSQL, port, routes
│   └── requirements.txt            # MODIFY: Add psycopg2
├── order-service/
│   ├── app.py                      # MODIFY: SQLite→PostgreSQL, port, routes
│   └── requirements.txt            # MODIFY: Add psycopg2
├── users-service/
│   ├── app.py                      # MODIFY: SQLite→PostgreSQL, port
│   └── requirements.txt            # MODIFY: Add psycopg2
└── README.md                       # MODIFY: Add CF deployment section
```

## Key Code Patterns

### Port Binding

```python
import os
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
```

### VCAP_SERVICES Parsing

```python
import json
import os

def get_db_config():
    vcap_services = os.environ.get('VCAP_SERVICES')
    if vcap_services:
        services = json.loads(vcap_services)
        # Extract PostgreSQL from service bindings
        postgres = services.get('postgresql', [{}])[0]
        creds = postgres.get('credentials', {})
        return {
            'host': creds.get('hostname'),
            'port': creds.get('port'),
            'database': creds.get('name'),
            'user': creds.get('username'),
            'password': creds.get('password')
        }
    else:
        # Kubernetes/local fallback
        return {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ.get('DB_NAME'),
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD')
        }
```

### Route URL Detection

```python
# In manifest.yml, routes are set per app
# Environment variables can be set in manifest or detected at runtime
if os.environ.get('CF_INSTANCE_INDEX'):
    # Running on Cloud Foundry - use route from env or construct
    base_url = os.environ.get('CF_INSTANCE_ADDR', '')
    cart_url = os.environ.get('CART_SERVICE_URL', f'https://cart-service.{base_domain}')
else:
    # Kubernetes - use service names
    cart_url = os.environ.get('CART_SERVICE_URL', 'http://cart-service:5002')
```

## Deployment Workflow

1. Fork repository to 0pens0 GitHub
2. Create CF space: `cf create-space metal-music-store -o tanzu-platfrom-demo`
3. Target space: `cf target -o tanzu-platfrom-demo -s metal-music-store`
4. Verify PostgreSQL service available
5. Deploy: `cf push` (from root directory)
6. All 4 services deploy together from single manifest

## Testing

- Verify all services start successfully
- Check service bindings to PostgreSQL
- Test inter-service communication via routes
- Verify Kubernetes deployment still works
- Test database operations on all services

## Notes

- Kubernetes manifests remain unchanged
- PostgreSQL migration is required for Cloud Foundry (no SQLite support)
- Single manifest simplifies deployment
- All services share same PostgreSQL instance (different databases/schemas)