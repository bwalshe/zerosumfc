from zerosumfc.buckshotroulette import PlayerStateManager
from zerosumfc.data import Item


def test_player_state_manager_init():
    initial_health = 5
    manager = PlayerStateManager(initial_health)
    assert manager.state.health == initial_health

    assert manager.state.inventory == dict()


def test_player_state_manager_immutable():
    manager = PlayerStateManager(2)
    item = Item.GLASS
    inventory_copy = manager.state.inventory
    assert item not in inventory_copy
    inventory_copy[item] = 1
    assert item not in manager.state.inventory


def test_player_state_health_bounds():
    initial_health = 5
    manager = PlayerStateManager(initial_health)
    manager.damage(1)
    assert manager.state.health == initial_health - 1
    manager.heal(1)
    assert manager.state.health == initial_health
    manager.damage(100)
    assert manager.state.health == 0
    manager.heal(100)
    assert manager.state.health == initial_health


def test_add_item():
    item = Item.GLASS
    other_item = Item.BEER
    manager = PlayerStateManager(1)
    assert manager.state.inventory.get(item, 0) == 0
    for i in range(manager.MAX_ITEMS):
        manager.add_item(item)
        assert manager.state.inventory[item] == i + 1
        assert manager.item_count == i + 1

    manager.add_item(other_item)
    assert manager.state.inventory.get(other_item, 0) == 0


def test_item_available():
    manager = PlayerStateManager(1)
    item = Item.BEER
    assert not manager.is_available(item)
    manager.add_item(item)
    assert manager.is_available(item)


def test_use_item():
    manager = PlayerStateManager(1)
    item = Item.BEER
    assert not manager.use_item(item)
    manager.add_item(item)
    assert manager.use_item(item)
    assert not manager.use_item(item)
