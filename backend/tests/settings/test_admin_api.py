import pytest
from httpx import AsyncClient

URL = "/api/admin/settings"
FIELDS = {
    "zone_a_delivery_fee",
    "zone_b_delivery_fee",
    "whatsapp_number",
    "instagram_url",
    "facebook_url",
}


async def test_both_endpoints_need_login(client: AsyncClient) -> None:
    assert (await client.get(URL)).status_code == 401
    assert (await client.patch(URL, json={"zone_a_delivery_fee": "1.000"})).status_code == 401


async def test_get_returns_the_editable_settings_and_no_password(
    admin_client: AsyncClient,
) -> None:
    response = await admin_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == FIELDS
    assert body["zone_a_delivery_fee"] == "2.000"
    assert body["zone_b_delivery_fee"] == "3.000"
    assert "password" not in response.text.lower()
    assert "hash" not in response.text.lower()


async def test_patch_each_field(admin_client: AsyncClient) -> None:
    response = await admin_client.patch(
        URL,
        json={
            "zone_a_delivery_fee": "2.500",
            "zone_b_delivery_fee": "4",
            "whatsapp_number": "0781234567",
            "instagram_url": "https://www.instagram.com/new_account",
            "facebook_url": "https://facebook.com/new",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "zone_a_delivery_fee": "2.500",
        "zone_b_delivery_fee": "4.000",
        "whatsapp_number": "0781234567",
        "instagram_url": "https://www.instagram.com/new_account",
        "facebook_url": "https://facebook.com/new",
    }
    assert (await admin_client.get(URL)).json() == response.json()


async def test_partial_patch_leaves_the_other_fields(admin_client: AsyncClient) -> None:
    before = (await admin_client.get(URL)).json()

    response = await admin_client.patch(URL, json={"zone_b_delivery_fee": "3.500"})

    assert response.status_code == 200
    assert response.json() == {**before, "zone_b_delivery_fee": "3.500"}


async def test_changed_fee_shows_in_public_settings(
    admin_client: AsyncClient, other_device: AsyncClient
) -> None:
    await admin_client.patch(URL, json={"zone_a_delivery_fee": "1.250"})

    body = (await other_device.get("/api/settings")).json()

    assert body["zone_a_delivery_fee"] == "1.250"
    assert {r["governorate"]: r["delivery_fee"] for r in body["governorates"]}["amman"] == "1.250"


@pytest.mark.parametrize("typed", ["078 123 4567", "078-123-4567", "٠٧٨ ١٢٣ ٤٥٦٧"])
async def test_whatsapp_number_is_normalized(admin_client: AsyncClient, typed: str) -> None:
    response = await admin_client.patch(URL, json={"whatsapp_number": typed})

    assert response.status_code == 200
    assert response.json()["whatsapp_number"] == "0781234567"
    public = (await admin_client.get("/api/settings")).json()
    assert public["whatsapp_international"] == "962781234567"


async def test_links_can_be_cleared(admin_client: AsyncClient) -> None:
    response = await admin_client.patch(URL, json={"instagram_url": None, "facebook_url": ""})

    assert response.status_code == 200
    assert response.json()["instagram_url"] is None
    assert response.json()["facebook_url"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"zone_a_delivery_fee": "-1.000"},
        {"zone_a_delivery_fee": "1.2345"},
        {"zone_b_delivery_fee": "12345678.000"},
        {"zone_b_delivery_fee": "abc"},
        {"whatsapp_number": "0761234567"},
        {"whatsapp_number": "079123"},
        {"instagram_url": "http://instagram.com/x"},
        {"instagram_url": "https://evil.com/instagram.com"},
        {"instagram_url": "https://notinstagram.com/x"},
        {"facebook_url": "https://instagram.com/x"},
        {"facebook_url": "https://facebook.com/" + "a" * 500},
        {"facebook_url": "https://facebook.com/a b"},
        {"facebook_url": "https://facebook.com/a\x00b"},
        {"zone_a_delivery_fee": None},
        {"zone_b_delivery_fee": None},
        {"whatsapp_number": None},
        {"admin_password_hash": "x"},
        {"password": "x"},
        {"unknown": 1},
    ],
)
async def test_invalid_values_are_422(
    admin_client: AsyncClient, payload: dict[str, object]
) -> None:
    before = (await admin_client.get(URL)).json()

    response = await admin_client.patch(URL, json=payload)

    assert response.status_code == 422
    assert (await admin_client.get(URL)).json() == before
