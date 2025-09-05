from copy import copy, replace
import pytest
from types import MappingProxyType

from zerosumfc.buckshotroulette import (
    PlayerStateManager,
    FullGameState,
    GameStateManager,
)
from zerosumfc.data import (
    Heal,
    Hit,
    Item,
    Miss,
    PlayerState,
    Role,
    See,
    Shell,
    Used,
)


def test_player_state_manager_init():
    initial_health = 5
    manager = PlayerStateManager(initial_health)
    state = manager.new()
    assert state.health == initial_health

    assert state.inventory == dict()


def test_player_state_manager_immutable():
    manager = PlayerStateManager(2)
    item = Item.GLASS
    original_state = manager.new()
    assert item not in original_state.inventory
    new_state = manager.add_item(original_state, item)
    assert item in new_state.inventory
    assert item not in original_state.inventory
    with pytest.raises(TypeError):
        original_state.inventory[item] = 1  # type: ignore
    with pytest.raises(TypeError):
        new_state.inventory[item] = 1  # type: ignore
    assert item not in original_state.inventory


def test_player_state_health_bounds():
    initial_health = 5
    manager = PlayerStateManager(initial_health)
    state = manager.new()
    damaged = manager.damage(state, 1)
    assert damaged.health == initial_health - 1
    assert manager.heal(damaged, 1).health == initial_health
    assert manager.damage(state, 100).health == 0
    assert manager.heal(damaged, 100).health == initial_health


def test_add_item_max_items():
    item = Item.GLASS
    other_item = Item.BEER
    manager = PlayerStateManager(1)
    state = manager.new()

    for i in range(manager.MAX_ITEMS):
        state = manager.add_item(state, item)
        assert state.inventory[item] == i + 1

    state = manager.add_item(state, other_item)
    assert state.inventory.get(other_item, 0) == 0


def test_item_available():
    manager = PlayerStateManager(1)
    item = Item.BEER
    state = manager.new()
    assert not manager.is_available(state, item)
    state = manager.add_item(state, item)
    assert manager.is_available(state, item)


def test_take_item():
    manager = PlayerStateManager(1)
    item = Item.BEER
    state = manager.new()
    taken, state = manager.take_item(state, item)
    assert not taken
    state = manager.add_item(state, item)
    taken, state = manager.take_item(state, item)
    assert taken
    taken, state = manager.take_item(state, item)
    assert not taken


def test_game_state_manager_init():
    initial_health = 5
    manager = GameStateManager(initial_health)
    state = manager.new()
    visible_state = state.visible_state
    assert visible_state.current_player == Role.PLAYER
    assert visible_state.handcuffs_active is False
    assert visible_state.saw_active is False
    assert visible_state.dealer_state.health == initial_health
    assert len(visible_state.dealer_state.inventory) == 0
    assert visible_state.player_state.health == initial_health
    assert len(visible_state.player_state.inventory) == 0
    assert len(state.shells) == 0


def set_visible_state(state: FullGameState, **kwargs):
    visible_state = state.visible_state
    visible_state = replace(visible_state, **kwargs)
    return replace(state, visible_state=visible_state)


def set_inventory(
    state: FullGameState,
    items: dict[Item, int],
    current_player: Role,
) -> FullGameState:
    player_state = PlayerState(health=1, inventory=MappingProxyType(items))
    dealer_state = copy(player_state)


    return set_visible_state(
        state,
        player_state=player_state,
        dealer_state=dealer_state,
        current_player=current_player,
    )


@pytest.mark.parametrize("role", list(Role))
def test_game_state_manager_use_item_correct_role(role):
    item = Item.HANDCUFFS
    initial_count = 2
    manager = GameStateManager(1)
    state = set_inventory(
        manager.new(), {item: initial_count}, current_player=role
    )
    result, new_state = manager.use_item(state, item)
    assert result is not None
    assert new_state.visible_state[role].inventory[item] == initial_count - 1
    assert (
        new_state.visible_state[role.opponent].inventory[item] == initial_count
    )


@pytest.mark.parametrize("shell", list(Shell))
def test_game_state_manager_use_beer(shell):
    role = Role.PLAYER
    manager = GameStateManager(1)
    state = set_inventory(manager.new(), {Item.BEER: 1}, role)
    state = replace(state, shells=[shell])
    result, new_state = manager.use_item(state, Item.BEER)
    assert result == See(shell)
    assert new_state.visible_state[role].inventory[Item.BEER] == 0


def test_game_state_manager_use_cigarettes():
    role = Role.PLAYER
    start_health = 1
    manager = GameStateManager(1)
    state = set_inventory(manager.new(), {Item.CIGARETTES: 1}, role)
    result, new_state = manager.use_item(state, Item.CIGARETTES)
    assert result == Heal(1)
    assert new_state.visible_state[role].health == start_health + 1


def test_game_state_manager_use_handcuffs():
    role = Role.PLAYER
    manager = GameStateManager(1)
    state = set_inventory(manager.new(), {Item.HANDCUFFS: 1}, role)
    result, new_state = manager.use_item(state, Item.HANDCUFFS)
    assert result == Used(Item.HANDCUFFS)
    assert new_state.visible_state.handcuffs_active


@pytest.mark.parametrize("shell", list(Shell))
def test_game_state_manager_use_glass(shell):
    role = Role.PLAYER
    manager = GameStateManager(1)
    state = set_inventory(manager.new(), {Item.GLASS: 1}, role)
    state = replace(state, shells=[shell])
    result, new_state = manager.use_item(state, Item.GLASS)
    assert result == See(shell)
    assert new_state.shells == [shell]


@pytest.mark.parametrize(
    "shooter,target,shell,damage,expected_result",
    [
        (Role.PLAYER, Role.DEALER, Shell.LIVE, 1, Hit(Role.DEALER)),
        (Role.PLAYER, Role.PLAYER, Shell.LIVE, 1, Hit(Role.PLAYER)),
        (Role.DEALER, Role.PLAYER, Shell.LIVE, 1, Hit(Role.PLAYER)),
        (Role.DEALER, Role.DEALER, Shell.LIVE, 1, Hit(Role.DEALER)),
        (Role.PLAYER, Role.DEALER, Shell.BLANK, 0, Miss()),
        (Role.PLAYER, Role.PLAYER, Shell.BLANK, 0, Miss()),
        (Role.DEALER, Role.PLAYER, Shell.BLANK, 0, Miss()),
        (Role.DEALER, Role.DEALER, Shell.BLANK, 0, Miss()),
    ],
)
def test_game_state_manager_shoot(
    shooter, target, shell, damage, expected_result
):
    start_health = 10
    manager = GameStateManager(start_health)
    state = replace(manager.new(), shells=[shell])
    visible_state = replace(state.visible_state, current_player=shooter)
    state = replace(state, visible_state=visible_state)
    result, new_state = manager.shoot(state, target)
    assert result == expected_result
    assert new_state.visible_state[target].health == start_health - damage


def test_game_state_manager_shoot_after_saw():
    start_health = 10
    manager = GameStateManager(start_health)
    state = manager.new()
    visible_state = replace(state.visible_state, saw_active=True)
    state = replace(state, visible_state=visible_state, shells=[Shell.LIVE])
    shooter = state.visible_state.current_player
    target = shooter.opponent
    _, new_state = manager.shoot(state, target)
    assert new_state.visible_state[target].health == start_health - 2


@pytest.mark.parametrize(
    "target,shell,next_player",
    [
        (Role.DEALER, Shell.LIVE, Role.DEALER),
        (Role.PLAYER, Shell.LIVE, Role.DEALER),
        (Role.DEALER, Shell.BLANK, Role.DEALER),
        (Role.PLAYER, Shell.BLANK, Role.PLAYER),
    ],
)
def test_game_state_manager_next_player(target, shell, next_player):
    manager = GameStateManager(10)
    state = manager.new()
    state = replace(state, shells=[shell] * 2)
    assert state.visible_state.current_player == Role.PLAYER
    _, new_state = manager.shoot(state, target)
    assert new_state.visible_state.current_player == next_player


@pytest.mark.parametrize("role", list(Role))
def test_game_state_manager_next_player_after_reload(role):
    manager = GameStateManager(10)
    state = set_visible_state(manager.new(), current_player=role)
    _, new_state = manager.reload(state)
    assert new_state.visible_state.current_player == Role.PLAYER
