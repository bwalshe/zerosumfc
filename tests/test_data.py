from copy import replace
import pytest

from zerosumfc.data import (
    GameState,
    Item,
    PlayerState,
    Role,
)


def test_role_opponent():
    assert Role.DEALER != Role.PLAYER
    assert Role.DEALER.opponent == Role.PLAYER
    assert Role.PLAYER.opponent == Role.DEALER


def test_player_state_immutable():
    item = Item.GLASS
    original_state = PlayerState(2)
    assert item not in original_state.inventory
    new_state = original_state.add_item(item)
    assert item in new_state.inventory
    assert item not in original_state.inventory
    with pytest.raises(TypeError):
        original_state.inventory[item] = 1  # type: ignore
    with pytest.raises(TypeError):
        new_state.inventory[item] = 1  # type: ignore
    assert item not in original_state.inventory


def test_player_state_health_bounds():
    initial_health = 5
    state = PlayerState(initial_health)
    damaged = state.damage(1)
    assert damaged.health == initial_health - 1
    assert damaged.heal(1, initial_health).health == initial_health
    assert state.damage(100).health == 0
    assert damaged.heal(100, initial_health).health == initial_health


def test_player_state_add_item_max_items():
    item = Item.GLASS
    other_item = Item.BEER
    state = PlayerState(1)

    for i in range(PlayerState.MAX_ITEMS):
        state = state.add_item(item)
        assert state.inventory[item] == i + 1

    state = state.add_item(other_item)
    assert state.inventory.get(other_item, 0) == 0


def test_player_state_contains():
    item = Item.BEER
    state = PlayerState(1)
    assert item not in state
    state = state.add_item(item)
    assert item in state


def test_player_state_take_item():
    state = PlayerState(1)
    item = Item.BEER
    taken, state = state.take_item(item)
    assert not taken
    state = state.add_item(item)
    taken, state = state.take_item(item)
    assert taken
    taken, state = state.take_item(item)
    assert not taken


def test_game_state_manager_init():
    initial_health = 5
    state = GameState.new(initial_health)
    assert state.current_player == Role.PLAYER
    assert state.handcuffs_active is False
    assert state.saw_active is False
    assert state.dealer_state.health == initial_health
    assert len(state.dealer_state.inventory) == 0
    assert state.player_state.health == initial_health
    assert len(state.player_state.inventory) == 0


def test_game_state_manager_add_items():
    player_item = Item.BEER
    dealer_item = Item.CIGARETTES

    state = GameState.new(1)
    state = state.add_all([player_item], [dealer_item])
    assert state.player_state.inventory == {player_item: 1}
    assert state.dealer_state.inventory == {dealer_item: 1}


@pytest.mark.parametrize("role", list(Role))
def test_game_state_take_item_correct_role(role):
    item = Item.HANDCUFFS
    initial_count = 2
    state = GameState.new(1).add_all(
        [item] * initial_count, [item] * initial_count
    )
    state = replace(state, current_player=role)
    result, new_state = state.take_item(item)
    assert result is not None
    assert new_state[role].inventory[item] == initial_count - 1
    assert new_state[role.opponent].inventory[item] == initial_count


@pytest.mark.parametrize("role", list(Role))
def test_game_state_damage(role):
    initial_health = 5
    state = GameState.new(5)
    state = state.damage(role, 1)
    assert state[role].health == initial_health - 1
    assert state[role.opponent].health == initial_health


