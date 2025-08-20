# import pytest

from zerosumfc.data import Item, RelativeRole, Shoot, Use
from zerosumfc.textagent import parse_action, parse_item, parse_shoot, ParseFailure


def test_parse_item():
    for item in Item:
        assert parse_item(item.name) == Use(item)
    assert type(parse_item("notanitem")) is ParseFailure


def test_parse_shoot():
    for role in RelativeRole:
        assert parse_shoot(role.name) == Shoot(role)
    assert type(parse_shoot("nonrole")) is ParseFailure
