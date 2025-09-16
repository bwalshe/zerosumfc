from copy import replace
import pytest

from zerosumfc.data import GameState, Item, PlayerState, Role, Shell


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


@pytest.mark.parametrize(
    "target,shell,damage",
    [
        (Role.PLAYER, Shell.LIVE, 1),
        (Role.PLAYER, Shell.BLANK, 0),
        (Role.DEALER, Shell.LIVE, 1),
        (Role.DEALER, Shell.BLANK, 0),
    ],
)
def test_game_state_shoot_damage(target, shell, damage):
    initial_health = 5
    state = GameState.new(5)
    state = state.shoot(shell, target)
    assert state[target].health == initial_health - damage
    assert state[target.opponent].health == initial_health


@pytest.mark.parametrize("saw_active,amount", [(True, 2), (False, 1)])
def test_game_state_damage_saw(saw_active, amount):
    target = Role.PLAYER
    initial_health = 5
    state = replace(GameState.new(5), saw_active=saw_active)
    state = state.shoot(Shell.LIVE, target)
    assert state[target].health == initial_health - amount


def test_game_state_reset_modifiers():
    state: GameState = replace(
        GameState.new(1), saw_active=True, handcuffs_active=True
    )
    assert state.handcuffs_active
    assert state.saw_active
    new_state = state.reset_modifiers()
    assert not new_state.handcuffs_active
    assert not new_state.saw_active


@pytest.mark.parametrize(
    "handcuffs_active,next_player", [(False, Role.DEALER), (True, Role.PLAYER)]
)
def test_game_state_end_turn(handcuffs_active, next_player):
    state: GameState = replace(
        GameState.new(1), handcuffs_active=handcuffs_active
    )
    assert state.current_player == Role.PLAYER
    new_state = state.end_turn()
    assert new_state.current_player == next_player
    assert not new_state.handcuffs_active

def test_game_state_heal_current_player():
    current_player = Role.PLAYER
    initial_health = 5
    state = GameState.new(initial_health).set_player(current_player, health=initial_health-1)
    assert state[current_player].health == initial_health - 1
    new_state = state.heal_current_player(1)
    assert new_state[current_player].health == initial_health

