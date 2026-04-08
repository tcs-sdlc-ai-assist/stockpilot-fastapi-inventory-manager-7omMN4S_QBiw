# StockPilot

**StockPilot** is a lightweight inventory management system built with Python, FastAPI, and Jinja2 templates. It provides a clean web interface for tracking products, managing stock levels, handling suppliers, and monitoring inventory movements — all with role-based access control for admin and staff users.

---

## Features

- **Dashboard** — Real-time overview of total products, low-stock alerts, recent activity, and inventory value
- **Product Management** — Full CRUD for products with categories, SKU tracking, and image support
- **Category Management** — Organize products into categories with descriptions
- **Supplier Management** — Track supplier contact info, addresses, and associated products
- **Stock Movements** — Record stock-in, stock-out, adjustments, and transfers with full audit trail
- **Low Stock Alerts** — Automatic alerts when product quantities fall below reorder thresholds
- **User Management** — Admin-controlled user accounts with role-based permissions
- **Role-Based Access Control** — Admin and Staff roles with granular permission enforcement
- **Search & Filter** — Search products by name/SKU, filter by category or supplier
- **Responsive UI** — Tailwind CSS-powered interface that works on desktop and mobile
- **Authentication** — Secure login/logout with session-based authentication and password hashing

---

## Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Backend      | Python 3.12, FastAPI                |
| Templates    | Jinja2                              |
| Styling      | Tailwind CSS (CDN)                  |
| Database     | SQLite (via SQLAlchemy 2.0 async)   |
| ORM          | SQLAlchemy 2.0 (async)              |
| Auth         | bcrypt, itsdangerous (sessions)     |
| Validation   | Pydantic v2                         |
| Server       | Uvicorn                             |
| Deployment   | Vercel (serverless)                 |

---

## Project Structure

```
stockpilot/
├── main.py                     # FastAPI application entry point
├── config.py                   # Application settings (Pydantic BaseSettings)
├── database.py                 # SQLAlchemy async engine, session, and Base
├── requirements.txt            # Python dependencies
├── vercel.json                 # Vercel deployment configuration
├── .env.example                # Example environment variables
├── README.md                   # Project documentation (this file)
│
├── models/
│   ├── __init__.py             # Re-exports all models
│   ├── user.py                 # User model (admin/staff roles)
│   ├── category.py             # Category model
│   ├── product.py              # Product model with stock tracking
│   ├── supplier.py             # Supplier model
│   └── stock_movement.py       # Stock movement audit log model
│
├── schemas/
│   ├── __init__.py             # Re-exports all schemas
│   ├── user.py                 # User request/response schemas
│   ├── category.py             # Category schemas
│   ├── product.py              # Product schemas
│   ├── supplier.py             # Supplier schemas
│   └── stock_movement.py       # Stock movement schemas
│
├── routes/
│   ├── __init__.py             # Re-exports all routers
│   ├── auth.py                 # Login/logout routes
│   ├── dashboard.py            # Dashboard route
│   ├── products.py             # Product CRUD routes
│   ├── categories.py           # Category CRUD routes
│   ├── suppliers.py            # Supplier CRUD routes
│   ├── stock_movements.py      # Stock movement routes
│   └── users.py                # User management routes (admin only)
│
├── dependencies.py             # Shared dependencies (auth, DB session)
├── seed.py                     # Database seeder for default admin user
│
├── templates/
│   ├── base.html               # Base layout with navigation
│   ├── login.html              # Login page
│   ├── dashboard.html          # Dashboard page
│   ├── products/
│   │   ├── list.html           # Product listing
│   │   ├── create.html         # Create product form
│   │   ├── edit.html           # Edit product form
│   │   └── detail.html         # Product detail view
│   ├── categories/
│   │   ├── list.html           # Category listing
│   │   ├── create.html         # Create category form
│   │   └── edit.html           # Edit category form
│   ├── suppliers/
│   │   ├── list.html           # Supplier listing
│   │   ├── create.html         # Create supplier form
│   │   ├── edit.html           # Edit supplier form
│   │   └── detail.html         # Supplier detail view
│   ├── stock_movements/
│   │   ├── list.html           # Movement history
│   │   └── create.html         # Record new movement
│   └── users/
│       ├── list.html           # User listing (admin)
│       ├── create.html         # Create user form (admin)
│       └── edit.html           # Edit user form (admin)
│
├── static/
│   └── css/
│       └── custom.css          # Minimal custom styles (if needed)
│
└── tests/
    ├── conftest.py             # Shared test fixtures
    ├── test_auth.py            # Authentication tests
    ├── test_products.py        # Product route tests
    ├── test_categories.py      # Category route tests
    ├── test_suppliers.py       # Supplier route tests
    ├── test_stock_movements.py # Stock movement tests
    └── test_users.py           # User management tests
```

---

## Setup Instructions

### Prerequisites

- Python 3.12+
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/stockpilot.git
cd stockpilot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
APP_NAME=StockPilot
SECRET_KEY=your-super-secret-key-change-this-in-production
DATABASE_URL=sqlite+aiosqlite:///./stockpilot.db
DEBUG=true
DEFAULT_ADMIN_EMAIL=admin@stockpilot.com
DEFAULT_ADMIN_PASSWORD=admin123
```

### 5. Seed the Database

The database tables are created automatically on first run. To create the default admin user:

```bash
python seed.py
```

### 6. Run Locally

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser and navigate to **http://localhost:8000**

---

## Vercel Deployment

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Deploy

```bash
vercel --prod
```

The `vercel.json` configuration routes all traffic through the FastAPI application. Ensure your environment variables are configured in the Vercel dashboard.

### 3. Set Environment Variables in Vercel

Go to your Vercel project → **Settings** → **Environment Variables** and add:

| Variable                 | Value                                      |
|--------------------------|--------------------------------------------|
| `SECRET_KEY`             | A strong random string (64+ characters)    |
| `DATABASE_URL`           | Your production database URL               |
| `DEBUG`                  | `false`                                    |
| `DEFAULT_ADMIN_EMAIL`    | `admin@stockpilot.com`                     |
| `DEFAULT_ADMIN_PASSWORD` | A strong password for the default admin    |

> **Note:** For production, use a hosted database (e.g., PostgreSQL on Supabase, Neon, or Railway) instead of SQLite.

---

## Environment Variables Reference

| Variable                 | Required | Default                              | Description                              |
|--------------------------|----------|--------------------------------------|------------------------------------------|
| `APP_NAME`               | No       | `StockPilot`                         | Application display name                 |
| `SECRET_KEY`             | **Yes**  | —                                    | Secret key for session signing           |
| `DATABASE_URL`           | No       | `sqlite+aiosqlite:///./stockpilot.db`| Async SQLAlchemy database URL            |
| `DEBUG`                  | No       | `false`                              | Enable debug mode                        |
| `DEFAULT_ADMIN_EMAIL`    | No       | `admin@stockpilot.com`               | Default admin account email              |
| `DEFAULT_ADMIN_PASSWORD` | No       | `admin123`                           | Default admin account password           |

---

## Default Admin Credentials

| Field    | Value                   |
|----------|-------------------------|
| Email    | `admin@stockpilot.com`  |
| Password | `admin123`              |

> ⚠️ **Change the default admin password immediately after first login in production.**

---

## Usage Guide

### Admin Role

Admins have full access to all features:

- **Dashboard** — View inventory overview, low-stock alerts, and recent activity
- **Products** — Create, edit, delete, and view all products
- **Categories** — Manage product categories
- **Suppliers** — Manage supplier records
- **Stock Movements** — Record and view all stock movements (in, out, adjustments)
- **Users** — Create, edit, and deactivate user accounts; assign roles

### Staff Role

Staff members have limited access:

- **Dashboard** — View inventory overview and alerts
- **Products** — View products and record stock movements
- **Categories** — View categories
- **Suppliers** — View supplier information
- **Stock Movements** — Record stock-in and stock-out movements

---

## API Route Map

### Authentication

| Method | Path           | Description          | Access  |
|--------|----------------|----------------------|---------|
| GET    | `/login`       | Login page           | Public  |
| POST   | `/login`       | Process login        | Public  |
| GET    | `/logout`      | Logout and redirect  | Auth    |

### Dashboard

| Method | Path           | Description          | Access  |
|--------|----------------|----------------------|---------|
| GET    | `/`            | Dashboard            | Auth    |
| GET    | `/dashboard`   | Dashboard            | Auth    |

### Products

| Method | Path                    | Description          | Access  |
|--------|-------------------------|----------------------|---------|
| GET    | `/products`             | List all products    | Auth    |
| GET    | `/products/create`      | Create product form  | Admin   |
| POST   | `/products/create`      | Save new product     | Admin   |
| GET    | `/products/{id}`        | Product detail       | Auth    |
| GET    | `/products/{id}/edit`   | Edit product form    | Admin   |
| POST   | `/products/{id}/edit`   | Update product       | Admin   |
| POST   | `/products/{id}/delete` | Delete product       | Admin   |

### Categories

| Method | Path                       | Description           | Access  |
|--------|----------------------------|-----------------------|---------|
| GET    | `/categories`              | List all categories   | Auth    |
| GET    | `/categories/create`       | Create category form  | Admin   |
| POST   | `/categories/create`       | Save new category     | Admin   |
| GET    | `/categories/{id}/edit`    | Edit category form    | Admin   |
| POST   | `/categories/{id}/edit`    | Update category       | Admin   |
| POST   | `/categories/{id}/delete`  | Delete category       | Admin   |

### Suppliers

| Method | Path                      | Description           | Access  |
|--------|---------------------------|-----------------------|---------|
| GET    | `/suppliers`              | List all suppliers    | Auth    |
| GET    | `/suppliers/create`       | Create supplier form  | Admin   |
| POST   | `/suppliers/create`       | Save new supplier     | Admin   |
| GET    | `/suppliers/{id}`         | Supplier detail       | Auth    |
| GET    | `/suppliers/{id}/edit`    | Edit supplier form    | Admin   |
| POST   | `/suppliers/{id}/edit`    | Update supplier       | Admin   |
| POST   | `/suppliers/{id}/delete`  | Delete supplier       | Admin   |

### Stock Movements

| Method | Path                        | Description              | Access  |
|--------|-----------------------------|--------------------------|---------|
| GET    | `/stock-movements`          | List all movements       | Auth    |
| GET    | `/stock-movements/create`   | Record movement form     | Auth    |
| POST   | `/stock-movements/create`   | Save new movement        | Auth    |

### Users (Admin Only)

| Method | Path                  | Description          | Access  |
|--------|-----------------------|----------------------|---------|
| GET    | `/users`              | List all users       | Admin   |
| GET    | `/users/create`       | Create user form     | Admin   |
| POST   | `/users/create`       | Save new user        | Admin   |
| GET    | `/users/{id}/edit`    | Edit user form       | Admin   |
| POST   | `/users/{id}/edit`    | Update user          | Admin   |
| POST   | `/users/{id}/delete`  | Deactivate user      | Admin   |

---

## Running Tests

```bash
pytest tests/ -v
```

For async test support:

```bash
pytest tests/ -v --asyncio-mode=auto
```

---

## License

**Private** — All rights reserved. This software is proprietary and confidential. Unauthorized copying, distribution, or modification is strictly prohibited.