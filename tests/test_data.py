from zerosumfc.data import Role


def test_role_opponent():
    assert Role.DEALER != Role.PLAYER
    assert Role.DEALER.oponent == Role.PLAYER
    assert Role.PLAYER.oponent == Role.DEALER
