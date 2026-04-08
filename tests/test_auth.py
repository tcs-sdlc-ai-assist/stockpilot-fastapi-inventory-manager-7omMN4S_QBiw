import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


@pytest.mark.asyncio
async def test_login_page_renders_for_unauthenticated_user(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "Sign in to StockPilot" in response.text
    assert "create a new account" in response.text


@pytest.mark.asyncio
async def test_login_page_has_username_and_password_fields(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


@pytest.mark.asyncio
async def test_successful_login_redirects_admin_to_dashboard(
    client: AsyncClient, admin_user: User
):
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


@pytest.mark.asyncio
async def test_successful_login_redirects_staff_to_inventory(
    client: AsyncClient, staff_user: User
):
    response = await client.post(
        "/login",
        data={"username": "teststaff", "password": "staffpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"


@pytest.mark.asyncio
async def test_successful_login_sets_session_cookie(
    client: AsyncClient, admin_user: User
):
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_login_with_invalid_password_shows_error(
    client: AsyncClient, admin_user: User
):
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_with_nonexistent_username_shows_error(client: AsyncClient):
    response = await client.post(
        "/login",
        data={"username": "nonexistentuser", "password": "somepassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_with_empty_fields_shows_error(client: AsyncClient):
    response = await client.post(
        "/login",
        data={"username": "", "password": ""},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Please enter both username and password" in response.text


@pytest.mark.asyncio
async def test_login_with_empty_username_shows_error(client: AsyncClient):
    response = await client.post(
        "/login",
        data={"username": "", "password": "somepassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Please enter both username and password" in response.text


@pytest.mark.asyncio
async def test_login_with_empty_password_shows_error(client: AsyncClient):
    response = await client.post(
        "/login",
        data={"username": "someuser", "password": ""},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Please enter both username and password" in response.text


@pytest.mark.asyncio
async def test_register_page_renders_for_unauthenticated_user(client: AsyncClient):
    response = await client.get("/register")
    assert response.status_code == 200
    assert "Create your account" in response.text


@pytest.mark.asyncio
async def test_register_page_has_required_fields(client: AsyncClient):
    response = await client.get("/register")
    assert response.status_code == 200
    assert 'name="display_name"' in response.text
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text
    assert 'name="confirm_password"' in response.text


@pytest.mark.asyncio
async def test_successful_registration_creates_staff_user(
    client: AsyncClient, db_session: AsyncSession
):
    response = await client.post(
        "/register",
        data={
            "display_name": "New User",
            "username": "newuser",
            "password": "securepass",
            "confirm_password": "securepass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"

    result = await db_session.execute(select(User).where(User.username == "newuser"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.display_name == "New User"
    assert user.role == "staff"


@pytest.mark.asyncio
async def test_successful_registration_sets_session_cookie(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Cookie User",
            "username": "cookieuser",
            "password": "securepass",
            "confirm_password": "securepass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_registration_validates_empty_display_name(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "",
            "username": "validuser",
            "password": "securepass",
            "confirm_password": "securepass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Display name is required" in response.text


@pytest.mark.asyncio
async def test_registration_validates_empty_username(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Valid Name",
            "username": "",
            "password": "securepass",
            "confirm_password": "securepass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username is required" in response.text


@pytest.mark.asyncio
async def test_registration_validates_short_password(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Valid Name",
            "username": "validuser",
            "password": "ab",
            "confirm_password": "ab",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Password must be at least 4 characters" in response.text


@pytest.mark.asyncio
async def test_registration_validates_password_mismatch(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Valid Name",
            "username": "validuser",
            "password": "securepass",
            "confirm_password": "differentpass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Passwords do not match" in response.text


@pytest.mark.asyncio
async def test_registration_validates_username_uniqueness(
    client: AsyncClient, staff_user: User
):
    response = await client.post(
        "/register",
        data={
            "display_name": "Another User",
            "username": "teststaff",
            "password": "securepass",
            "confirm_password": "securepass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username already exists" in response.text


@pytest.mark.asyncio
async def test_registration_validates_empty_password(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Valid Name",
            "username": "validuser",
            "password": "",
            "confirm_password": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Password is required" in response.text


@pytest.mark.asyncio
async def test_registration_validates_empty_confirm_password(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Valid Name",
            "username": "validuser",
            "password": "securepass",
            "confirm_password": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Please confirm your password" in response.text


@pytest.mark.asyncio
async def test_registration_validates_long_display_name(client: AsyncClient):
    long_name = "A" * 101
    response = await client.post(
        "/register",
        data={
            "display_name": long_name,
            "username": "validuser",
            "password": "securepass",
            "confirm_password": "securepass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Display name must be 100 characters or fewer" in response.text


@pytest.mark.asyncio
async def test_registration_validates_long_username(client: AsyncClient):
    long_username = "u" * 51
    response = await client.post(
        "/register",
        data={
            "display_name": "Valid Name",
            "username": long_username,
            "password": "securepass",
            "confirm_password": "securepass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username must be 50 characters or fewer" in response.text


@pytest.mark.asyncio
async def test_registration_preserves_form_data_on_error(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "My Name",
            "username": "myuser",
            "password": "ab",
            "confirm_password": "ab",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "My Name" in response.text
    assert "myuser" in response.text


@pytest.mark.asyncio
async def test_logout_clears_session_and_redirects(admin_client: AsyncClient):
    response = await admin_client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "session" in set_cookie_header


@pytest.mark.asyncio
async def test_authenticated_admin_redirected_from_login_page(
    admin_client: AsyncClient,
):
    response = await admin_client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


@pytest.mark.asyncio
async def test_authenticated_staff_redirected_from_login_page(
    staff_client: AsyncClient,
):
    response = await staff_client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"


@pytest.mark.asyncio
async def test_authenticated_admin_redirected_from_register_page(
    admin_client: AsyncClient,
):
    response = await admin_client.get("/register", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


@pytest.mark.asyncio
async def test_authenticated_staff_redirected_from_register_page(
    staff_client: AsyncClient,
):
    response = await staff_client.get("/register", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"


@pytest.mark.asyncio
async def test_login_preserves_username_on_failed_attempt(
    client: AsyncClient, admin_user: User
):
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert 'value="testadmin"' in response.text


@pytest.mark.asyncio
async def test_logout_prevents_access_to_protected_routes(
    admin_client: AsyncClient,
):
    logout_response = await admin_client.get("/logout", follow_redirects=False)
    assert logout_response.status_code == 303

    admin_client.cookies.clear()

    dashboard_response = await admin_client.get("/dashboard", follow_redirects=False)
    assert dashboard_response.status_code == 303
    assert "/login" in dashboard_response.headers.get("location", "")


@pytest.mark.asyncio
async def test_multiple_registration_errors_shown(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "",
            "username": "",
            "password": "",
            "confirm_password": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Display name is required" in response.text
    assert "Username is required" in response.text
    assert "Password is required" in response.text


@pytest.mark.asyncio
async def test_registered_user_can_login(client: AsyncClient):
    register_response = await client.post(
        "/register",
        data={
            "display_name": "Login Test User",
            "username": "logintestuser",
            "password": "testpass123",
            "confirm_password": "testpass123",
        },
        follow_redirects=False,
    )
    assert register_response.status_code == 303

    fresh_client_response = await client.post(
        "/login",
        data={"username": "logintestuser", "password": "testpass123"},
        follow_redirects=False,
    )
    assert fresh_client_response.status_code == 303
    assert fresh_client_response.headers["location"] == "/inventory/"