import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.item import InventoryItem
from models.user import User


@pytest.mark.asyncio
async def test_inventory_list_redirects_unauthenticated(client: AsyncClient):
    response = await client.get("/inventory/", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_inventory_list_renders_for_authenticated_user(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/inventory/", follow_redirects=False)
    assert response.status_code == 200
    assert "Inventory" in response.text
    assert "Laptop" in response.text
    assert "T-Shirt" in response.text
    assert "Coffee Beans" in response.text


@pytest.mark.asyncio
async def test_inventory_list_renders_for_staff_user(
    staff_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await staff_client.get("/inventory/", follow_redirects=False)
    assert response.status_code == 200
    assert "Inventory" in response.text


@pytest.mark.asyncio
async def test_inventory_list_search_filters_by_name(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/inventory/?search=Laptop", follow_redirects=False)
    assert response.status_code == 200
    assert "Laptop" in response.text
    assert "Coffee Beans" not in response.text


@pytest.mark.asyncio
async def test_inventory_list_filter_by_category(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
    sample_categories: list[Category],
):
    electronics_id = sample_categories[0].id
    response = await admin_client.get(
        f"/inventory/?category={electronics_id}", follow_redirects=False
    )
    assert response.status_code == 200
    assert "Laptop" in response.text
    assert "T-Shirt" not in response.text


@pytest.mark.asyncio
async def test_inventory_list_sort_by_quantity(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/inventory/?sort=quantity", follow_redirects=False)
    assert response.status_code == 200
    text = response.text
    coffee_pos = text.find("Coffee Beans")
    tshirt_pos = text.find("T-Shirt")
    laptop_pos = text.find("Laptop")
    assert coffee_pos < tshirt_pos < laptop_pos


@pytest.mark.asyncio
async def test_inventory_list_sort_by_price(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/inventory/?sort=price", follow_redirects=False)
    assert response.status_code == 200
    text = response.text
    laptop_pos = text.find("Laptop")
    tshirt_pos = text.find("T-Shirt")
    assert laptop_pos < tshirt_pos


@pytest.mark.asyncio
async def test_inventory_list_sort_by_name(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/inventory/?sort=name", follow_redirects=False)
    assert response.status_code == 200
    text = response.text
    coffee_pos = text.find("Coffee Beans")
    laptop_pos = text.find("Laptop")
    tshirt_pos = text.find("T-Shirt")
    assert coffee_pos < laptop_pos < tshirt_pos


@pytest.mark.asyncio
async def test_inventory_add_form_renders(admin_client: AsyncClient, sample_categories: list[Category]):
    response = await admin_client.get("/inventory/add", follow_redirects=False)
    assert response.status_code == 200
    assert "Add" in response.text


@pytest.mark.asyncio
async def test_inventory_add_creates_item(
    admin_client: AsyncClient,
    sample_categories: list[Category],
    db_session: AsyncSession,
):
    category_id = sample_categories[0].id
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "New Widget",
            "sku": "WDG-999",
            "description": "A brand new widget",
            "quantity": "25",
            "unit_price": "49.99",
            "reorder_level": "5",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert "/inventory/" in location

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.sku == "WDG-999")
    )
    item = result.scalar_one_or_none()
    assert item is not None
    assert item.name == "New Widget"
    assert item.quantity == 25
    assert item.unit_price == 49.99
    assert item.reorder_level == 5


@pytest.mark.asyncio
async def test_inventory_add_without_name_returns_error(
    admin_client: AsyncClient,
    sample_categories: list[Category],
):
    category_id = sample_categories[0].id
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "",
            "sku": "WDG-ERR",
            "description": "",
            "quantity": "10",
            "unit_price": "5.00",
            "reorder_level": "2",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Name is required" in response.text


@pytest.mark.asyncio
async def test_inventory_add_without_category_returns_error(
    admin_client: AsyncClient,
):
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "No Category Item",
            "sku": "NC-001",
            "description": "",
            "quantity": "10",
            "unit_price": "5.00",
            "reorder_level": "2",
            "category_id": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Category is required" in response.text


@pytest.mark.asyncio
async def test_inventory_add_negative_quantity_returns_error(
    admin_client: AsyncClient,
    sample_categories: list[Category],
):
    category_id = sample_categories[0].id
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "Negative Qty Item",
            "sku": "NEG-001",
            "description": "",
            "quantity": "-5",
            "unit_price": "10.00",
            "reorder_level": "2",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Quantity must be zero or greater" in response.text


@pytest.mark.asyncio
async def test_inventory_add_duplicate_sku_returns_error(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
    sample_categories: list[Category],
):
    existing_sku = sample_items[0].sku
    category_id = sample_categories[0].id
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "Duplicate SKU Item",
            "sku": existing_sku,
            "description": "",
            "quantity": "10",
            "unit_price": "5.00",
            "reorder_level": "2",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "SKU already exists" in response.text


@pytest.mark.asyncio
async def test_inventory_detail_renders(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    item = sample_items[0]
    response = await admin_client.get(f"/inventory/{item.id}", follow_redirects=False)
    assert response.status_code == 200
    assert item.name in response.text
    assert item.sku in response.text


@pytest.mark.asyncio
async def test_inventory_detail_404_for_invalid_id(
    admin_client: AsyncClient,
):
    response = await admin_client.get("/inventory/99999", follow_redirects=False)
    assert response.status_code == 404
    assert "404" in response.text


@pytest.mark.asyncio
async def test_inventory_edit_form_renders_for_owner(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    item = sample_items[0]
    response = await admin_client.get(f"/inventory/{item.id}/edit", follow_redirects=False)
    assert response.status_code == 200
    assert item.name in response.text
    assert "Edit" in response.text


@pytest.mark.asyncio
async def test_inventory_edit_updates_item(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
    sample_categories: list[Category],
    db_session: AsyncSession,
):
    item = sample_items[0]
    category_id = sample_categories[1].id
    response = await admin_client.post(
        f"/inventory/{item.id}/edit",
        data={
            "name": "Updated Laptop",
            "sku": "ELEC-001-UPD",
            "description": "An updated laptop description",
            "quantity": "75",
            "unit_price": "1099.99",
            "reorder_level": "15",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert f"/inventory/{item.id}" in location

    await db_session.expire_all()
    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == item.id)
    )
    updated_item = result.scalar_one_or_none()
    assert updated_item is not None
    assert updated_item.name == "Updated Laptop"
    assert updated_item.sku == "ELEC-001-UPD"
    assert updated_item.quantity == 75
    assert updated_item.unit_price == 1099.99


@pytest.mark.asyncio
async def test_inventory_edit_404_for_invalid_id(
    admin_client: AsyncClient,
    sample_categories: list[Category],
):
    response = await admin_client.post(
        "/inventory/99999/edit",
        data={
            "name": "Ghost Item",
            "sku": "GHOST-001",
            "description": "",
            "quantity": "1",
            "unit_price": "1.00",
            "reorder_level": "0",
            "category_id": str(sample_categories[0].id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_inventory_edit_duplicate_sku_returns_error(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
    sample_categories: list[Category],
):
    item_to_edit = sample_items[0]
    other_item_sku = sample_items[1].sku
    response = await admin_client.post(
        f"/inventory/{item_to_edit.id}/edit",
        data={
            "name": "Laptop Edited",
            "sku": other_item_sku,
            "description": "",
            "quantity": "50",
            "unit_price": "999.99",
            "reorder_level": "10",
            "category_id": str(sample_categories[0].id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "SKU already exists" in response.text


@pytest.mark.asyncio
async def test_inventory_delete_removes_item(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
    db_session: AsyncSession,
):
    item = sample_items[0]
    item_id = item.id
    response = await admin_client.post(
        f"/inventory/{item_id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert "/inventory" in location

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    deleted_item = result.scalar_one_or_none()
    assert deleted_item is None


@pytest.mark.asyncio
async def test_inventory_delete_404_for_invalid_id(
    admin_client: AsyncClient,
):
    response = await admin_client.post(
        "/inventory/99999/delete",
        follow_redirects=False,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_staff_cannot_edit_other_users_item(
    staff_client: AsyncClient,
    sample_items: list[InventoryItem],
    sample_categories: list[Category],
):
    item = sample_items[0]
    response = await staff_client.get(
        f"/inventory/{item.id}/edit",
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert "/inventory" in location


@pytest.mark.asyncio
async def test_staff_cannot_delete_other_users_item(
    staff_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    item = sample_items[0]
    response = await staff_client.post(
        f"/inventory/{item.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert "/inventory" in location


@pytest.mark.asyncio
async def test_staff_can_edit_own_item(
    staff_client: AsyncClient,
    staff_user: User,
    sample_categories: list[Category],
    db_session: AsyncSession,
):
    category_id = sample_categories[0].id
    item = InventoryItem(
        name="Staff Item",
        sku="STAFF-001",
        description="Created by staff",
        quantity=10,
        unit_price=5.00,
        reorder_level=2,
        category_id=category_id,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)

    response = await staff_client.get(
        f"/inventory/{item.id}/edit",
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Staff Item" in response.text


@pytest.mark.asyncio
async def test_staff_can_delete_own_item(
    staff_client: AsyncClient,
    staff_user: User,
    sample_categories: list[Category],
    db_session: AsyncSession,
):
    category_id = sample_categories[0].id
    item = InventoryItem(
        name="Staff Delete Item",
        sku="STAFF-DEL-001",
        description="To be deleted by staff",
        quantity=3,
        unit_price=2.00,
        reorder_level=1,
        category_id=category_id,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    item_id = item.id

    response = await staff_client.post(
        f"/inventory/{item_id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    deleted = result.scalar_one_or_none()
    assert deleted is None


@pytest.mark.asyncio
async def test_admin_can_edit_any_users_item(
    admin_client: AsyncClient,
    staff_user: User,
    sample_categories: list[Category],
    db_session: AsyncSession,
):
    category_id = sample_categories[0].id
    item = InventoryItem(
        name="Staff Owned Item",
        sku="STAFF-OWN-001",
        description="Owned by staff, edited by admin",
        quantity=8,
        unit_price=12.00,
        reorder_level=3,
        category_id=category_id,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)

    response = await admin_client.get(
        f"/inventory/{item.id}/edit",
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Staff Owned Item" in response.text


@pytest.mark.asyncio
async def test_admin_can_delete_any_users_item(
    admin_client: AsyncClient,
    staff_user: User,
    sample_categories: list[Category],
    db_session: AsyncSession,
):
    category_id = sample_categories[0].id
    item = InventoryItem(
        name="Staff Item To Delete",
        sku="STAFF-ADEL-001",
        description="Owned by staff, deleted by admin",
        quantity=2,
        unit_price=7.00,
        reorder_level=1,
        category_id=category_id,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    item_id = item.id

    response = await admin_client.post(
        f"/inventory/{item_id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    deleted = result.scalar_one_or_none()
    assert deleted is None


@pytest.mark.asyncio
async def test_inventory_list_shows_out_of_stock_badge(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/inventory/", follow_redirects=False)
    assert response.status_code == 200
    assert "Out of Stock" in response.text


@pytest.mark.asyncio
async def test_inventory_list_shows_low_stock_badge(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/inventory/", follow_redirects=False)
    assert response.status_code == 200
    assert "Low Stock" in response.text


@pytest.mark.asyncio
async def test_inventory_detail_shows_stock_status(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    out_of_stock_item = sample_items[2]
    response = await admin_client.get(
        f"/inventory/{out_of_stock_item.id}", follow_redirects=False
    )
    assert response.status_code == 200
    assert "Out of Stock" in response.text

    low_stock_item = sample_items[1]
    response = await admin_client.get(
        f"/inventory/{low_stock_item.id}", follow_redirects=False
    )
    assert response.status_code == 200
    assert "Low Stock" in response.text

    in_stock_item = sample_items[0]
    response = await admin_client.get(
        f"/inventory/{in_stock_item.id}", follow_redirects=False
    )
    assert response.status_code == 200
    assert "In Stock" in response.text


@pytest.mark.asyncio
async def test_inventory_add_with_empty_sku_succeeds(
    admin_client: AsyncClient,
    sample_categories: list[Category],
    db_session: AsyncSession,
):
    category_id = sample_categories[0].id
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "No SKU Item",
            "sku": "",
            "description": "Item without SKU",
            "quantity": "10",
            "unit_price": "5.00",
            "reorder_level": "2",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.name == "No SKU Item")
    )
    item = result.scalar_one_or_none()
    assert item is not None
    assert item.sku is None


@pytest.mark.asyncio
async def test_inventory_list_empty_state(
    admin_client: AsyncClient,
):
    response = await admin_client.get("/inventory/", follow_redirects=False)
    assert response.status_code == 200
    assert "No inventory items found" in response.text


@pytest.mark.asyncio
async def test_inventory_add_invalid_unit_price_returns_error(
    admin_client: AsyncClient,
    sample_categories: list[Category],
):
    category_id = sample_categories[0].id
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "Bad Price Item",
            "sku": "BAD-PRICE",
            "description": "",
            "quantity": "10",
            "unit_price": "not-a-number",
            "reorder_level": "2",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Unit price must be a valid number" in response.text


@pytest.mark.asyncio
async def test_inventory_add_invalid_quantity_returns_error(
    admin_client: AsyncClient,
    sample_categories: list[Category],
):
    category_id = sample_categories[0].id
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "Bad Qty Item",
            "sku": "BAD-QTY",
            "description": "",
            "quantity": "abc",
            "unit_price": "10.00",
            "reorder_level": "2",
            "category_id": str(category_id),
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Quantity must be a valid integer" in response.text


@pytest.mark.asyncio
async def test_inventory_edit_form_404_for_invalid_id(
    admin_client: AsyncClient,
):
    response = await admin_client.get("/inventory/99999/edit", follow_redirects=False)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_inventory_list_search_no_results(
    admin_client: AsyncClient,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get(
        "/inventory/?search=NonExistentItemXYZ", follow_redirects=False
    )
    assert response.status_code == 200
    assert "No inventory items found" in response.text


@pytest.mark.asyncio
async def test_inventory_add_nonexistent_category_returns_error(
    admin_client: AsyncClient,
):
    response = await admin_client.post(
        "/inventory/add",
        data={
            "name": "Bad Category Item",
            "sku": "BAD-CAT",
            "description": "",
            "quantity": "10",
            "unit_price": "5.00",
            "reorder_level": "2",
            "category_id": "99999",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "category does not exist" in response.text