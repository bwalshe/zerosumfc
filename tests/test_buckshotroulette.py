from dataclasses import replace
import pytest

from zerosumfc.buckshotroulette import (
    FullGameState
)
from zerosumfc.data import (
    Heal,
    Hit,
    Item,
    Miss,
    Role,
    See,
    Shell,
    Used,
)


def set_visible_state(state: FullGameState, **kwargs):
    visible_state = state.visible_state
    visible_state = replace(visible_state, **kwargs)
    return replace(state, visible_state=visible_state)


def game_with_inventory(
    items: list[Item],
    health=1,
    current_player: Role = Role.PLAYER,
) -> FullGameState:
    state = FullGameState.new(health)
    visible_state = state.visible_state.add_all(items, items)
    visible_state = replace(visible_state, current_player=current_player)
    return replace(state, visible_state=visible_state)


@pytest.mark.parametrize("shell", list(Shell))
def test_game_state_manager_use_beer(shell):
    role = Role.PLAYER
    beer = Item.BEER
    state = game_with_inventory([beer], 1, role)
    state = replace(state, shells=[shell])
    result, new_state = state.use_item(beer)
    assert result == See(shell)
    assert new_state.visible_state[role].inventory.get(beer, 0) == 0


def test_game_state_manager_use_cigarettes():
    role = Role.PLAYER
    cigarettes = Item.CIGARETTES
    start_health = 10
    state = game_with_inventory([cigarettes], start_health, role)
    state = replace(
        state,
        visible_state=state.visible_state.set_player(
            role, health=start_health - 1
        ),
    )

    result, new_state = state.use_item(cigarettes)
    assert result == Heal(1)
    assert (
        new_state.visible_state[role].health
        == state.visible_state[role].health + 1
    )
    assert new_state.visible_state[role].inventory.get(cigarettes, 0) == 0


def test_game_state_manager_use_handcuffs():
    role = Role.PLAYER
    handcuffs = Item.HANDCUFFS
    state = game_with_inventory([handcuffs], current_player=role)
    result, new_state = state.use_item(handcuffs)
    assert result == Used(handcuffs)
    assert new_state.visible_state.handcuffs_active
    assert new_state.visible_state[role].inventory.get(handcuffs, 0) == 0


@pytest.mark.parametrize("shell", list(Shell))
def test_game_state_manager_use_glass(shell):
    role = Role.PLAYER
    glass = Item.GLASS
    state = game_with_inventory([glass], current_player=role)
    state = replace(state, shells=[shell])
    result, new_state = state.use_item(glass)
    assert result == See(shell)
    assert new_state.shells == [shell]
    assert new_state.visible_state[role].inventory.get(glass, 0) == 0


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
    state = replace(FullGameState.new(start_health), shells=[shell])
    visible_state = replace(state.visible_state, current_player=shooter)
    state = replace(state, visible_state=visible_state)
    result, new_state = state.shoot(target)
    assert result == expected_result
    assert new_state.visible_state[target].health == start_health - damage
    assert len(new_state.shells) == 0


def test_game_state_manager_shoot_after_saw():
    start_health = 10
    state = FullGameState.new(start_health)
    visible_state = replace(state.visible_state, saw_active=True)
    state = replace(state, visible_state=visible_state, shells=[Shell.LIVE])
    shooter = state.visible_state.current_player
    target = shooter.opponent
    _, new_state = state.shoot(target)
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
    state = FullGameState.new(10)
    state = replace(state, shells=[shell] * 2)
    assert state.visible_state.current_player == Role.PLAYER
    _, new_state = state.shoot(target)
    assert new_state.visible_state.current_player == next_player


@pytest.mark.parametrize("role", list(Role))
def test_game_state_manager_next_player_after_reload(role):
    state = set_visible_state(FullGameState.new(10), current_player=role)
    _, new_state = state.reload()
    assert new_state.visible_state.current_player == Role.PLAYER
