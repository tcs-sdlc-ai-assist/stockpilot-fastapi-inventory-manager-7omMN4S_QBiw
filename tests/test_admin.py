import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.item import InventoryItem
from models.user import User


pytestmark = pytest.mark.asyncio


class TestDashboardAccess:
    """Tests that the dashboard is accessible by admin only and staff is redirected."""

    async def test_admin_can_access_dashboard(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    async def test_admin_can_access_dashboard_trailing_slash(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/", follow_redirects=False)
        assert response.status_code == 200

    async def test_staff_redirected_from_dashboard(self, staff_client: AsyncClient):
        response = await staff_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory/"

    async def test_unauthenticated_redirected_from_dashboard(self, client: AsyncClient):
        response = await client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

    async def test_dashboard_displays_correct_stat_counts(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
        admin_user: User,
    ):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        html = response.text

        assert "Total Items" in html
        assert "Total Categories" in html
        assert "Total Users" in html

    async def test_dashboard_shows_low_stock_items(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
    ):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        html = response.text

        assert "Low Stock Alerts" in html
        assert "T-Shirt" in html
        assert "Coffee Beans" in html


class TestCategoryManagement:
    """Tests for category CRUD operations (admin only)."""

    async def test_admin_can_view_categories(self, admin_client: AsyncClient):
        response = await admin_client.get("/categories/", follow_redirects=False)
        assert response.status_code == 200
        assert "Category Management" in response.text

    async def test_staff_cannot_view_categories(self, staff_client: AsyncClient):
        response = await staff_client.get("/categories/", follow_redirects=False)
        assert response.status_code == 303

    async def test_unauthenticated_cannot_view_categories(self, client: AsyncClient):
        response = await client.get("/categories/", follow_redirects=False)
        assert response.status_code == 303

    async def test_admin_can_add_category(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/categories/add",
            data={"name": "Test Category", "color": "#ff5733"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/categories/"

    async def test_add_category_appears_in_list(self, admin_client: AsyncClient):
        await admin_client.post(
            "/categories/add",
            data={"name": "New Category", "color": "#abcdef"},
            follow_redirects=False,
        )
        response = await admin_client.get("/categories/", follow_redirects=False)
        assert response.status_code == 200
        assert "New Category" in response.text

    async def test_add_category_empty_name_rejected(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/categories/add",
            data={"name": "", "color": "#ff5733"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_add_category_name_too_long_rejected(self, admin_client: AsyncClient):
        long_name = "A" * 51
        response = await admin_client.post(
            "/categories/add",
            data={"name": long_name, "color": "#ff5733"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_add_duplicate_category_rejected(self, admin_client: AsyncClient):
        await admin_client.post(
            "/categories/add",
            data={"name": "Duplicate Cat", "color": "#ff5733"},
            follow_redirects=False,
        )
        response = await admin_client.post(
            "/categories/add",
            data={"name": "Duplicate Cat", "color": "#ff5733"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_add_category_invalid_color_defaults(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/categories/add",
            data={"name": "Color Test Cat", "color": "invalid"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_admin_can_delete_empty_category(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ):
        category = Category(name="Deletable Category", color="#123456")
        db_session.add(category)
        await db_session.flush()
        await db_session.refresh(category)
        cat_id = category.id

        response = await admin_client.post(
            f"/categories/{cat_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/categories/"

    async def test_delete_category_blocked_when_items_exist(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
    ):
        electronics_id = sample_categories[0].id
        response = await admin_client.post(
            f"/categories/{electronics_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_delete_nonexistent_category(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/categories/99999/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_staff_cannot_add_category(self, staff_client: AsyncClient):
        response = await staff_client.post(
            "/categories/add",
            data={"name": "Staff Category", "color": "#ff5733"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_staff_cannot_delete_category(
        self,
        staff_client: AsyncClient,
        sample_categories: list[Category],
    ):
        response = await staff_client.post(
            f"/categories/{sample_categories[0].id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestUserManagement:
    """Tests for user management CRUD (admin only)."""

    async def test_admin_can_view_users(self, admin_client: AsyncClient):
        response = await admin_client.get("/users/", follow_redirects=False)
        assert response.status_code == 200
        assert "User Management" in response.text

    async def test_staff_cannot_view_users(self, staff_client: AsyncClient):
        response = await staff_client.get("/users/", follow_redirects=False)
        assert response.status_code == 303

    async def test_unauthenticated_cannot_view_users(self, client: AsyncClient):
        response = await client.get("/users/", follow_redirects=False)
        assert response.status_code == 303

    async def test_admin_can_create_user(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "New User",
                "username": "newuser",
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/users/"

    async def test_created_user_appears_in_list(self, admin_client: AsyncClient):
        await admin_client.post(
            "/users/create",
            data={
                "display_name": "Listed User",
                "username": "listeduser",
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        response = await admin_client.get("/users/", follow_redirects=False)
        assert response.status_code == 200
        assert "Listed User" in response.text

    async def test_create_admin_user(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "New Admin",
                "username": "newadmin",
                "password": "password123",
                "role": "admin",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_create_user_empty_display_name_rejected(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "",
                "username": "noname",
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "required" in response.text.lower() or "error" in response.text.lower()

    async def test_create_user_empty_username_rejected(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "No Username",
                "username": "",
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_create_user_empty_password_rejected(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "No Password",
                "username": "nopassword",
                "password": "",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_create_user_short_password_rejected(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "Short Pass",
                "username": "shortpass",
                "password": "ab",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_create_user_invalid_role_rejected(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "Bad Role",
                "username": "badrole",
                "password": "password123",
                "role": "superadmin",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_create_user_duplicate_username_rejected(
        self,
        admin_client: AsyncClient,
        staff_user: User,
    ):
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "Duplicate",
                "username": staff_user.username,
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "already exists" in response.text.lower() or "error" in response.text.lower()

    async def test_create_user_display_name_too_long_rejected(self, admin_client: AsyncClient):
        long_name = "A" * 101
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": long_name,
                "username": "longname",
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_create_user_username_too_long_rejected(self, admin_client: AsyncClient):
        long_username = "u" * 51
        response = await admin_client.post(
            "/users/create",
            data={
                "display_name": "Long Username",
                "username": long_username,
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_admin_can_delete_user(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from dependencies import hash_password

        user_to_delete = User(
            username="deleteme",
            display_name="Delete Me",
            hashed_password=hash_password("password123"),
            role="staff",
        )
        db_session.add(user_to_delete)
        await db_session.flush()
        await db_session.refresh(user_to_delete)
        user_id = user_to_delete.id

        response = await admin_client.post(
            f"/users/{user_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/users/"

    async def test_cannot_delete_default_admin(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from config import settings
        from dependencies import hash_password

        result = await db_session.execute(
            select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
        )
        default_admin = result.scalar_one_or_none()

        if default_admin is None:
            default_admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                display_name=settings.DEFAULT_ADMIN_DISPLAY_NAME,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            db_session.add(default_admin)
            await db_session.flush()
            await db_session.refresh(default_admin)

        response = await admin_client.post(
            f"/users/{default_admin.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_cannot_delete_self(
        self,
        admin_client: AsyncClient,
        admin_user: User,
    ):
        response = await admin_client.post(
            f"/users/{admin_user.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_delete_nonexistent_user(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/users/99999/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_staff_cannot_create_user(self, staff_client: AsyncClient):
        response = await staff_client.post(
            "/users/create",
            data={
                "display_name": "Staff Created",
                "username": "staffcreated",
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_staff_cannot_delete_user(
        self,
        staff_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from dependencies import hash_password

        user = User(
            username="targetuser",
            display_name="Target User",
            hashed_password=hash_password("password123"),
            role="staff",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        response = await staff_client.post(
            f"/users/{user.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestRoleBasedRouteGuards:
    """Tests that role-based route guards redirect correctly."""

    async def test_unauthenticated_redirected_from_inventory(self, client: AsyncClient):
        response = await client.get("/inventory/", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

    async def test_unauthenticated_redirected_from_inventory_add(self, client: AsyncClient):
        response = await client.get("/inventory/add", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

    async def test_staff_can_access_inventory(self, staff_client: AsyncClient):
        response = await staff_client.get("/inventory/", follow_redirects=False)
        assert response.status_code == 200

    async def test_admin_can_access_inventory(self, admin_client: AsyncClient):
        response = await admin_client.get("/inventory/", follow_redirects=False)
        assert response.status_code == 200

    async def test_staff_redirected_from_categories(self, staff_client: AsyncClient):
        response = await staff_client.get("/categories/", follow_redirects=False)
        assert response.status_code == 303

    async def test_staff_redirected_from_users(self, staff_client: AsyncClient):
        response = await staff_client.get("/users/", follow_redirects=False)
        assert response.status_code == 303

    async def test_admin_login_redirects_to_dashboard(self, client: AsyncClient, admin_user: User):
        response = await client.post(
            "/login",
            data={"username": "testadmin", "password": "adminpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    async def test_staff_login_redirects_to_inventory(self, client: AsyncClient, staff_user: User):
        response = await client.post(
            "/login",
            data={"username": "teststaff", "password": "staffpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory/"

    async def test_logged_in_admin_redirected_from_login_page(self, admin_client: AsyncClient):
        response = await admin_client.get("/login", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    async def test_logged_in_staff_redirected_from_login_page(self, staff_client: AsyncClient):
        response = await staff_client.get("/login", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory/"

    async def test_logged_in_admin_redirected_from_register_page(self, admin_client: AsyncClient):
        response = await admin_client.get("/register", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    async def test_logged_in_staff_redirected_from_register_page(self, staff_client: AsyncClient):
        response = await staff_client.get("/register", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory/"