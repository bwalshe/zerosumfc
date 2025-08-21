# import pytest

from zerosumfc.data import Item, Role, Shoot, Use
from zerosumfc.textagent import ActionParser, ParseFailure


def test_parse_item():
    parser = ActionParser(Role.DEALER)
    for item in Item:
        assert parser.parse_item(f"USE {item.name}") == Use(item)

    assert parser.parse_item("TIE SHOE") is None

    assert type(parser.parse_item("USE notanitem")) is ParseFailure
    assert type(parser.parse_item("USE")) is ParseFailure


def test_parse_shoot_nonrelative():
    parser = ActionParser(Role.DEALER)
    for role in Role:
        assert parser.parse_shoot(f"SHOOT {role.name}") == Shoot(role)

    assert parser.parse_shoot("TIE SHOE") is None

    assert type(parser.parse_shoot("SHOOT GUN")) is ParseFailure
    assert type(parser.parse_shoot("SHOOT")) is ParseFailure


def test_parse_shoot_relaive():
    for role in list(Role):
        parser = ActionParser(role)
        for word in ["ME", "MYSELF", "SELF"]:
            assert parser.parse_shoot(f"SHOOT {word}") == Shoot(role)
        for word in ["OPPONENT", "OTHER"]:
            assert parser.parse_shoot(f"SHOOT {word}") == Shoot(role.oponent)


def test_parse_action():
    parser = ActionParser(Role.DEALER)
    assert parser("SHOOT DEALER") == Shoot(Role.DEALER)
    assert parser("USE GLASS") == Use(Item.GLASS)
    assert type(parser("TIE SHOE")) is ParseFailure
    assert type(parser("USE GLASS AGAIN")) is ParseFailure
