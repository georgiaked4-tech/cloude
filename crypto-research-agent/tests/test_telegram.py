from src.bot.telegram import is_owner


def test_only_owner_chat_is_authorized() -> None:
    assert is_owner(123456, "123456") is True
    assert is_owner("123456", " 123456 ") is True
    assert is_owner(999999, "123456") is False


def test_missing_identifiers_are_never_authorized() -> None:
    assert is_owner(None, "123456") is False
    assert is_owner(123456, "") is False
