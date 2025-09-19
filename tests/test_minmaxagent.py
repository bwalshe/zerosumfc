import pytest

from zerosumfc.data import GameState, Item, Role, Shell
from zerosumfc.minmaxagent import MinMaxState, pick_move, StateProb


def get_prob_and_shells(state_prob: StateProb):
    return (
        state_prob.p_state,
        state_prob.state.live_shells,
        state_prob.state.blank_shells,
    )


@pytest.mark.parametrize(
    "live_count, blank_count, expected",
    [
        (1, 1, set([(0.5, 0, 1), (0.5, 1, 0)])),
        (1, 0, set([(1.0, 0, 0)])),
        (0, 1, set([(1.0, 0, 0)])),
    ],
)
def test_min_max_state_shoot(live_count, blank_count, expected):
    game_state = GameState.new(10)
    state = MinMaxState(
        visible_state=game_state,
        live_shells=live_count,
        blank_shells=blank_count,
    )
    actual_vals = set(
        get_prob_and_shells(sp) for sp in state.shoot(Role.PLAYER)
    )
    assert actual_vals == expected


def test_min_max_state_shoot_exception():
    state = MinMaxState(
        visible_state=GameState.new(1), live_shells=0, blank_shells=0
    )
    with pytest.raises(ValueError):
        state.shoot(Role.PLAYER)


def test_min_max_state_use_beer():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.BEER], [Item.BEER]),
        live_shells=1,
        blank_shells=1,
    )
    new_states = state.use_beer()
    actual_vals = set(get_prob_and_shells(s) for s in new_states)
    assert actual_vals == set([(0.5, 1, 0), (0.5, 0, 1)])


def test_min_max_state_use_glass():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.GLASS], []),
        live_shells=1,
        blank_shells=1,
    )
    new_states = state.use_glass()
    actual_vals = set(get_prob_and_shells(s) for s in new_states)
    assert actual_vals == set([(0.5, 1, 1), (0.5, 1, 1)])

    next_shells = set(s.state.next_shell for s in new_states)
    assert next_shells == set(list(Shell))

def test_min_max_state_use_saw():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.SAW],[]),
        live_shells=1,
        blank_shells=1,
    )
    new_states = state.use_saw()
    assert len(new_states) == 1
    assert new_states[0].state.visible_state.saw_active


def test_min_max_state_use_handcuffs():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.HANDCUFFS],[]),
        live_shells=1,
        blank_shells=1,
    )
    new_states = state.use_handcuffs()
    assert len(new_states) == 1
    assert new_states[0].state.visible_state.handcuffs_active


@pytest.mark.parametrize("item", list(Item))
def test_min_max_state_item_inventory_updates(item: Item):
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([item], [item]),
        live_shells=1,
        blank_shells=1,
    )
    player = state.visible_state.current_player
    opponent = player.opponent

    new_states = state.use_item(item)

    for s in new_states:
        assert s.state.visible_state[player][item] == 0
        assert s.state.visible_state[opponent][item] == 1


@pytest.mark.parametrize("item", list(Item))
def test_min_max_state_use_unavilable_item_error(item: Item):
    state = MinMaxState(
        visible_state=GameState.new(1), live_shells=1, blank_shells=1
    )

    with pytest.raises(ValueError):
        new_states = state.use_item(item)


@pytest.mark.parametrize(
    "player, expected_score", [(Role.PLAYER, 0.0), (Role.DEALER, 1.0)]
)
def test_pick_move_base(player, expected_score):
    game_state = GameState.new(1).set_player(player, health=0)
    state = MinMaxState(
        visible_state=game_state, live_shells=1, blank_shells=1
    )

    assert pick_move(state).p_win == expected_score
