from zerosumfc.data import GameRole


def test_role_opponent():
    assert GameRole.DEALER != GameRole.PLAYER
    assert GameRole.DEALER.oponent == GameRole.PLAYER
    assert GameRole.PLAYER.oponent == GameRole.DEALER
