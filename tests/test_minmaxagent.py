import pytest

from zerosumfc.buckshotroulette import GameState
from zerosumfc.data import GameState, Role, Shell
from zerosumfc.minmaxagent import MinMaxState, pick_move, StateProb


@pytest.mark.parametrize(
    "live_count, blank_count, expected",
    [
        (1, 1, set([(0.5, 0, 1), (0.5, 1, 0)])),
        (1, 0, set([(1.0, 0, 0)])),
        (0, 1, set([(1.0, 0, 0)])),
    ],
)
def test_min_max_state_shoot(live_count, blank_count, expected):
    def get_prob_and_shells(state_prob: StateProb):
        return (
            state_prob.p_state,
            state_prob.state.live_shells,
            state_prob.state.blank_shells,
        )

    game_state = GameState.new(10)
    state = MinMaxState(
        visible_state=game_state,
        live_shells=live_count,
        blank_shells=blank_count,
    )
    actual_vals = set(get_prob_and_shells(sp) for sp in state.shoot(Role.PLAYER))
    assert actual_vals == expected

def test_min_max_state_shoot_exception():
    state = MinMaxState(visible_state=GameState.new(1), live_shells=0, blank_shells=0)
    with pytest.raises(ValueError):
        state.shoot(Role.PLAYER)

@pytest.mark.parametrize(
    "player, expected_score", [(Role.PLAYER, 0.0), (Role.DEALER, 1.0)]
)
def test_pick_move_base(player, expected_score):
    game_state = GameState.new(1).set_player(player, health=0)
    state = MinMaxState(
        visible_state=game_state, live_shells=1, blank_shells=1
    )

    assert pick_move(state).p_win == expected_score
