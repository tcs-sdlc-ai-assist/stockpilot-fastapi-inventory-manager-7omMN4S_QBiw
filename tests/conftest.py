import asyncio
import logging
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base, get_db
from dependencies import hash_password
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

test_async_session = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from main import app

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    hashed = hash_password("adminpass123")
    user = User(
        username="testadmin",
        display_name="Test Admin",
        hashed_password=hashed,
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def staff_user(db_session: AsyncSession) -> User:
    hashed = hash_password("staffpass123")
    user = User(
        username="teststaff",
        display_name="Test Staff",
        hashed_password=hashed,
        role="staff",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    cookies = dict(response.cookies)
    for name, value in cookies.items():
        client.cookies.set(name, value)
    return client


@pytest_asyncio.fixture
async def staff_client(client: AsyncClient, staff_user: User) -> AsyncClient:
    response = await client.post(
        "/login",
        data={"username": "teststaff", "password": "staffpass123"},
        follow_redirects=False,
    )
    cookies = dict(response.cookies)
    for name, value in cookies.items():
        client.cookies.set(name, value)
    return client


@pytest_asyncio.fixture
async def sample_categories(db_session: AsyncSession) -> list[Category]:
    categories = [
        Category(name="Electronics", color="#3b82f6"),
        Category(name="Clothing", color="#10b981"),
        Category(name="Food & Beverage", color="#f59e0b"),
    ]
    for cat in categories:
        db_session.add(cat)
    await db_session.flush()
    for cat in categories:
        await db_session.refresh(cat)
    return categories


@pytest_asyncio.fixture
async def sample_items(
    db_session: AsyncSession,
    sample_categories: list[Category],
    admin_user: User,
) -> list[InventoryItem]:
    items = [
        InventoryItem(
            name="Laptop",
            sku="ELEC-001",
            description="A high-performance laptop",
            quantity=50,
            unit_price=999.99,
            reorder_level=10,
            category_id=sample_categories[0].id,
            created_by_id=admin_user.id,
        ),
        InventoryItem(
            name="T-Shirt",
            sku="CLO-001",
            description="Cotton t-shirt",
            quantity=5,
            unit_price=19.99,
            reorder_level=10,
            category_id=sample_categories[1].id,
            created_by_id=admin_user.id,
        ),
        InventoryItem(
            name="Coffee Beans",
            sku="FOOD-001",
            description="Premium coffee beans",
            quantity=0,
            unit_price=14.99,
            reorder_level=20,
            category_id=sample_categories[2].id,
            created_by_id=admin_user.id,
        ),
    ]
    for item in items:
        db_session.add(item)
    await db_session.flush()
    for item in items:
        await db_session.refresh(item)
    return items