from zerosumfc.data import Role


def test_role_opponent():
    assert Role.DEALER != Role.PLAYER
    assert Role.DEALER.opponent == Role.PLAYER
    assert Role.PLAYER.opponent == Role.DEALER
