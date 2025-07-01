def authorization_from_token(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}"
    }
