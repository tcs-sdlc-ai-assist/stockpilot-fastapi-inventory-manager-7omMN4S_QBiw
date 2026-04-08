# Changelog

All notable changes to the StockPilot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2025-01-15

### Added

- **Session-Based Authentication**
  - Secure login and registration system using signed session cookies
  - Password hashing with bcrypt for secure credential storage
  - Session expiration and automatic cleanup
  - Login and registration pages with form validation

- **Role-Based Access Control (RBAC)**
  - Two user roles: `admin` and `user`
  - Admin-only routes protected with role-checking middleware
  - Regular users restricted to managing their own inventory items
  - Admins have full access to all resources and management features

- **Inventory CRUD with Ownership**
  - Create, read, update, and delete inventory items
  - Each item is associated with the user who created it
  - Users can only modify and delete their own items
  - Admins can view and manage all items across the system
  - Item fields include name, description, quantity, price, and category
  - Low stock threshold alerts for items below minimum quantity

- **Category Management**
  - Full CRUD operations for inventory categories
  - Admin-only category creation, editing, and deletion
  - All users can view and filter by categories
  - Default categories seeded on first run: Electronics, Furniture, Office Supplies, Food & Beverages, Clothing

- **Admin Dashboard**
  - Overview of total inventory items, categories, and users
  - Low stock items summary with quick access links
  - Recent activity feed showing latest inventory changes
  - User management panel for viewing and managing all accounts

- **User Management**
  - Admin ability to view all registered users
  - Admin ability to activate and deactivate user accounts
  - Admin ability to change user roles
  - User profile page for updating personal information and password

- **Responsive Tailwind CSS UI**
  - Mobile-first responsive design using Tailwind CSS utility classes
  - Clean, modern interface with consistent design language
  - Responsive navigation with mobile hamburger menu
  - Dark-friendly color palette with accessible contrast ratios
  - Flash message system for success, error, and info notifications
  - Jinja2 template inheritance with shared base layout

- **Vercel Deployment Support**
  - `vercel.json` configuration for serverless Python deployment
  - Environment variable configuration for production settings
  - Static file serving configuration
  - Build and routing rules for FastAPI on Vercel

- **SQLite Persistence**
  - SQLAlchemy 2.0 async engine with aiosqlite driver
  - Automatic database creation and table migration on startup
  - Lightweight file-based storage requiring no external database server
  - Database file configurable via environment variable

- **Default Admin and Category Seeding**
  - Automatic creation of default admin account on first run (admin@stockpilot.com / admin123)
  - Pre-populated default categories for immediate use
  - Seeding runs only when database is empty to avoid duplicates