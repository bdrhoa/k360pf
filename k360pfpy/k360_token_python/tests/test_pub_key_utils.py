from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_fetch_public_key_success(monkeypatch):
    monkeypatch.setenv("KOUNT_CLIENT_ID", "dummy_id")
    monkeypatch.setattr(pk_utils.token_manager, "get_access_token", lambda: "dummy_token")

    public_key_data = {
        "publicKey": "dGVzdA==",  # base64 of 'test'
        "validUntil": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    with aioresponses() as mock:
        mock.get(
            pk_utils.PUBLIC_KEY_URL_TEMPLATE.format("dummy_id"),
            payload=public_key_data,
            status=200
        )

        await pk_utils.fetch_public_key()

    assert pk_utils.public_key_manager.get_public_key() == public_key_data["publicKey"]