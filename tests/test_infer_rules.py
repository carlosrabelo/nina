"""Unit tests for inferring rules from Gmail user labels."""

from nina.skills.email_learning.infer_rules import _user_label_names_on_message


def test_user_label_names_single() -> None:
    user_map = {"Label_1": "shop/amazon", "Label_2": "other"}
    names = _user_label_names_on_message(["INBOX", "Label_1", "UNREAD"], user_map)
    assert names == ["shop/amazon"]


def test_user_label_names_multiple_sorted() -> None:
    user_map = {"L1": "a", "L2": "b"}
    names = _user_label_names_on_message(["L2", "L1"], user_map)
    assert names == ["a", "b"]


def test_user_label_names_none() -> None:
    assert _user_label_names_on_message(["INBOX", "UNREAD"], {}) == []
