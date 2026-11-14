from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.service import get_store_settings


async def test_public_settings_have_fees_per_governorate_and_no_secrets(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    store = await get_store_settings(db_session)
    store.zone_a_delivery_fee = Decimal("2.500")
    store.admin_password_hash = "secret-hash"
    await db_session.flush()

    response = await client.get("/api/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["zone_a_delivery_fee"] == "2.500"
    assert body["whatsapp_international"] == "962" + body["whatsapp_number"][1:]
    fees = {row["governorate"]: (row["zone"], row["delivery_fee"]) for row in body["governorates"]}
    assert len(fees) == 12
    assert fees["amman"] == ("a", "2.500")
    assert fees["zarqa"] == ("a", "2.500")
    assert fees["irbid"] == ("b", body["zone_b_delivery_fee"])
    assert "secret-hash" not in response.text
    assert "admin_password_hash" not in body
