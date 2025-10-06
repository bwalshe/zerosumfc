import pytest

from zerosumfc.buckshotroulette import FullGameState, Game
from zerosumfc.data import GameState, Item, Role, PlayerState, Shell, Shoot
from zerosumfc.minmaxagent import (
    HiddenState,
    MinMaxState,
    pick_move,
    StateProb,
)


def test_hidden_state_use_shell():
    def counts(state: HiddenState):
        return state.blank_shells, state.live_shells

    state = HiddenState(1, 1)
    assert counts(state) == (1, 1)
    assert counts(state.use(Shell.LIVE)) == (1, 0)
    assert counts(state.use(Shell.BLANK)) == (0, 1)


def test_hidden_state_use_shell_reset_next():
    state = HiddenState(1, 1, Shell.BLANK)
    for shell in list(Shell):
        assert state.use(shell).next_shell is None


@pytest.mark.parametrize(
    "live, blank, shell", [(0, 1, Shell.LIVE), (1, 0, Shell.BLANK)]
)
def test_hidden_state_use_shell_empty_error(live, blank, shell):
    state = HiddenState(live_shells=live, blank_shells=blank)
    with pytest.raises(ValueError):
        state.use(shell)


@pytest.mark.parametrize(
    "live, blank, shell, expected",
    [
        (0, 0, Shell.LIVE, 0),
        (1, 0, Shell.LIVE, 1),
        (0, 1, Shell.LIVE, 0),
        (0, 0, Shell.BLANK, 0),
        (1, 0, Shell.BLANK, 0),
        (0, 1, Shell.BLANK, 1),
    ],
)
def test_hidden_state_counts(live, blank, shell, expected):
    state = HiddenState(live_shells=live, blank_shells=blank)
    assert state.count(shell) == expected


@pytest.mark.parametrize(
    "live, blank, shell, expected",
    [
        (0, 0, Shell.LIVE, 0.0),
        (1, 0, Shell.LIVE, 1.0),
        (0, 1, Shell.LIVE, 0.0),
        (1, 1, Shell.LIVE, 0.5),
        (0, 0, Shell.BLANK, 0.0),
        (1, 0, Shell.BLANK, 0.0),
        (0, 1, Shell.BLANK, 1.0),
        (1, 1, Shell.BLANK, 0.5),
    ],
)
def test_hidden_state_probabilities(live, blank, shell, expected):
    state = HiddenState(live_shells=live, blank_shells=blank)
    assert state.prob(shell) == expected


def get_prob_and_shells(state_prob: StateProb):
    return (
        state_prob.p_state,
        state_prob.state.hidden_state.live_shells,
        state_prob.state.hidden_state.blank_shells,
    )


@pytest.mark.parametrize(
    "live_count, blank_count, expected",
    [
        (1, 1, set([(0.5, 0, 1), (0.5, 1, 0)])),
        (1, 0, set([(1.0, 0, 0)])),
        (0, 1, set([(1.0, 0, 0)])),
        (0, 0, set()),
    ],
)
def test_min_max_state_shoot(live_count, blank_count, expected):
    game_state = GameState.new(10)
    state = MinMaxState(
        visible_state=game_state,
        hidden_state=HiddenState(
            live_shells=live_count, blank_shells=blank_count
        ),
    )
    actual_vals = set(
        get_prob_and_shells(sp) for sp in state.shoot(Role.PLAYER)
    )
    assert actual_vals == expected


def test_min_max_state_use_beer():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.BEER], [Item.BEER]),
        hidden_state=HiddenState(live_shells=1, blank_shells=1),
    )
    new_states = state.use_beer()
    actual_vals = set(get_prob_and_shells(s) for s in new_states)
    assert actual_vals == set([(0.5, 1, 0), (0.5, 0, 1)])


def test_min_max_state_use_glass():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.GLASS], []),
        hidden_state=HiddenState(live_shells=1, blank_shells=1),
    )
    new_states = state.use_glass()
    actual_vals = set(get_prob_and_shells(s) for s in new_states)
    assert actual_vals == set([(0.5, 1, 1)])

    next_shells = set(s.state.hidden_state.next_shell for s in new_states)
    assert next_shells == set(list(Shell))


def test_min_max_state_use_saw():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.SAW], []),
        hidden_state=HiddenState(live_shells=1, blank_shells=1),
    )
    new_states = state.use_saw()
    assert len(new_states) == 1
    assert new_states[0].state.visible_state.saw_active


def test_min_max_state_use_handcuffs():
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([Item.HANDCUFFS], []),
        hidden_state=HiddenState(live_shells=1, blank_shells=1),
    )
    new_states = state.use_handcuffs()
    assert len(new_states) == 1
    assert new_states[0].state.visible_state.handcuffs_active


@pytest.mark.parametrize("item", list(Item))
def test_min_max_state_item_inventory_updates(item: Item):
    state = MinMaxState(
        visible_state=GameState.new(1).add_all([item], [item]),
        hidden_state=HiddenState(live_shells=1, blank_shells=1),
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
        visible_state=GameState.new(1),
        hidden_state=HiddenState(live_shells=1, blank_shells=1),
    )

    with pytest.raises(ValueError):
        new_states = state.use_item(item)


@pytest.mark.parametrize(
    "player, expected_score", [(Role.PLAYER, 0.0), (Role.DEALER, 1.0)]
)
def test_pick_move_base(player, expected_score):
    game_state = GameState.new(1).set_player(player, health=0)
    state = MinMaxState(
        visible_state=game_state,
        hidden_state=HiddenState(live_shells=1, blank_shells=1),
    )

    assert pick_move(state).p_win == expected_score


@pytest.mark.parametrize("player", list(Role))
def test_picks_shoot_to_end(player: Role):
    visible_state = GameState(
        player_state=PlayerState(
            health=1,
            glass_count=1,
            beer_count=1,
            saw_count=1,
            handcuffs_count=1,
            cigarettes_count=0,
        ),
        dealer_state=PlayerState(
            health=1,
            glass_count=1,
            beer_count=1,
            saw_count=1,
            handcuffs_count=0,
            cigarettes_count=0,
        ),
        max_health=5,
        current_player=player,
        saw_active=False,
        handcuffs_active=False,
    )
    state = MinMaxState(
        visible_state=visible_state,
        hidden_state=HiddenState(live_shells=1, blank_shells=0),
    )

    assert pick_move(state).move == Shoot(player.opponent)
