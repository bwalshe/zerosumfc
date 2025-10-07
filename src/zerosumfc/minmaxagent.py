from dataclasses import dataclass, field, replace
from functools import cache
import logging
import random

from zerosumfc.agents import Agent
from zerosumfc.data import (
    Action,
    Feedback,
    GameState,
    Hit,
    Item,
    Miss,
    Role,
    See,
    Shell,
    Shoot,
    Use,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StateProb:
    p_state: float
    state: "MinMaxState"


StateList = list[StateProb]


@dataclass(frozen=True)
class HiddenState:
    live_shells: int
    blank_shells: int
    next_shell: Shell | None = None

    def __post_init__(self):
        if self.live_shells < 0:
            raise ValueError("Live shells must be non-negative")
        if self.blank_shells < 0:
            raise ValueError("Blank shells must be non-negative")
        if self.live_shells == 0 and self.next_shell == Shell.LIVE:
            raise ValueError("The next shell cannot be live.")
        if self.blank_shells == 0 and self.next_shell == Shell.BLANK:
            raise ValueError("The next shell cannot be a blank.")

    def use(self, shell: Shell) -> "HiddenState":
        match shell:
            case Shell.LIVE:
                return replace(
                    self, live_shells=self.live_shells - 1, next_shell=None
                )
            case Shell.BLANK:
                return replace(
                    self, blank_shells=self.blank_shells - 1, next_shell=None
                )

    def count(self, shell: Shell):
        match shell:
            case Shell.LIVE:
                return self.live_shells
            case Shell.BLANK:
                return self.blank_shells

    def prob(self, shell: Shell):
        count = self.count(shell)
        if count == 0:
            return 0
        total = self.live_shells + self.blank_shells
        return count / total


@dataclass(frozen=True)
class MinMaxState:
    visible_state: GameState
    hidden_state: HiddenState

    def shoot(self, target: Role) -> StateList:
        def make_state(shell):
            return MinMaxState(
                visible_state=self.visible_state.shoot(shell, target),
                hidden_state=self.hidden_state.use(shell),
            )

        states = []

        for shell in list(Shell):
            if self.hidden_state.count(shell) > 0:
                p_shell = self.hidden_state.prob(shell)
                state = make_state(shell)
                states.append(StateProb(p_shell, state))

        return states

    def use_beer(self) -> StateList:
        new_visible_state = self._try_take(Item.BEER)

        def make_state(shell):
            new_hidden_state = self.hidden_state.use(shell)
            return replace(
                self,
                visible_state=new_visible_state,
                hidden_state=new_hidden_state,
            )

        states = []

        for shell in list(Shell):
            if self.hidden_state.count(shell) > 0:
                p_shell = self.hidden_state.prob(shell)
                state = make_state(shell)
                states.append(StateProb(p_shell, state))

        return states

    def use_cigarettes(self) -> StateList:
        new_visible_state = self._try_take(
            Item.CIGARETTES
        ).heal_current_player(1)
        return [StateProb(1.0, replace(self, visible_state=new_visible_state))]

    def use_handcuffs(self) -> StateList:
        new_visible_state = self._try_take(Item.HANDCUFFS)
        new_visible_state = replace(new_visible_state, handcuffs_active=True)
        return [StateProb(1.0, replace(self, visible_state=new_visible_state))]

    def use_glass(self) -> StateList:
        new_visible_state = self._try_take(Item.GLASS)

        def make_state(shell):
            return replace(
                self,
                visible_state=new_visible_state,
                hidden_state=replace(self.hidden_state, next_shell=shell),
            )

        states = []

        for shell in list(Shell):
            if self.hidden_state.count(shell) > 0:
                p_shell = self.hidden_state.prob(shell)
                state = make_state(shell)
                states.append(StateProb(p_shell, state))

        return states

    def use_saw(self) -> StateList:
        new_visible_state = self._try_take(Item.SAW)
        new_visible_state = replace(new_visible_state, saw_active=True)
        return [StateProb(1.0, replace(self, visible_state=new_visible_state))]

    def use_item(self, item: Item) -> StateList:
        match item:
            case Item.BEER:
                return self.use_beer()
            case Item.CIGARETTES:
                return self.use_cigarettes()
            case Item.HANDCUFFS:
                return self.use_handcuffs()
            case Item.GLASS:
                return self.use_glass()
            case Item.SAW:
                return self.use_saw()
            case _:
                raise ValueError(f"item must not be {item}")

    def perform_action(self, action: Action) -> StateList:
        match action:
            case Shoot(target):
                return self.shoot(target)
            case Use(item):
                return self.use_item(item)
            case _:
                raise ValueError(f"action cannot be {action}")

    def _try_take(self, item: Item) -> GameState:
        success, state = self.visible_state.take_item(item)
        if not success:
            raise ValueError("Agent tried to use unavailable item")
        return state


@dataclass(order=True)
class MoveOption:
    p_win: float
    move: Action | None = field(compare=False)


def p_win_sample(player, dealer, player_next, trials=1000):
    # TODO: There should be a closed form for this
    def move(p1, p2, p1_next):
        if random.choice([True, False]):
            if p1_next:
                return p1, p2 - 1, not p1_next
            else:
                return p1 - 1, p2, not p1_next
        return p1, p2, not p1_next

    def is_win(p1, p2, _):
        return p1 != 0 and p2 == 0

    def is_loss(p1, p2, _):
        return p1 == 0 and p2 != 0

    wins = 0

    max_iter = 100

    for _ in range(trials):
        state = (player, dealer, player_next)
        for _ in range(max_iter):
            state = move(*state)
            if is_win(*state):
                wins += 1
                break
            if is_loss(*state):
                break
    return wins / trials


@cache
def pick_move(state: MinMaxState) -> MoveOption:
    # logger.debug(f"pick_move() called with state: {state}")
    visible_state = state.visible_state
    hidden_state = state.hidden_state
    if visible_state.player_state.health == 0:
        #    logger.debug("Player has lost, no moves to make")
        return MoveOption(0.0, None)
    if visible_state.dealer_state.health == 0:
        #   logger.debug("Player has won, no moves to make")
        return MoveOption(1.0, None)

    if hidden_state.blank_shells == 0 and hidden_state.live_shells == 0:
        # logger.debug("No shells left estimating p_win")
        player_health = visible_state.player_state.health
        dealer_health = visible_state.player_state.health
        player_next = visible_state.current_player == Role.PLAYER
        p_win = p_win_sample(player_health, dealer_health, player_next, 1000)
        return MoveOption(
            p_win, None
        )

    options = list_moves(state)
    # logger.debug("options are %s", options)
    options = [score_move(state, move) for move in options]

    # logger.debug("Scored options are %s", options)
    best_move = None
    if visible_state.current_player == Role.PLAYER:
        #   logger.debug("Maximizing Player win probabity")
        best_move = max(options)
    else:
        #  logger.debug("Minimizing Player win probabilty")
        best_move = min(options)
    return best_move


def list_moves(state: MinMaxState) -> list[Action]:
    current_player = state.visible_state.current_player
    player_state = state.visible_state[current_player]
    max_health = state.visible_state.max_health
    if Item.CIGARETTES in player_state and player_state.health < max_health:
        return [Use(Item.CIGARETTES)]

    moves: list[Action] = [Shoot(target) for target in list(Role)]
    if Item.BEER in player_state:
        moves.append(Use(Item.BEER))
    if Item.GLASS in player_state and state.hidden_state.next_shell is None:
        moves.append(Use(Item.GLASS))
    if (
        Item.HANDCUFFS in player_state
        and not state.visible_state.handcuffs_active
    ):
        moves.append(Use(Item.HANDCUFFS))
    if Item.SAW in player_state and not state.visible_state.saw_active:
        moves.append(Use(Item.SAW))
    return moves


def score_move(state: MinMaxState, move: Action) -> MoveOption:
    states = state.perform_action(move)
    p_win = sum(s.p_state * pick_move(s.state).p_win for s in states)
    return MoveOption(p_win, move)


class MinMaxAgent(Agent):
    def __init__(self, role: Role):
        super().__init__(role)
        self._last_move = None
        self.reset_shells(0, 0)

    def reset_shells(self, live: int, blank: int) -> None:
        self._hidden_state = HiddenState(live, blank)

    def get_move(self, state: GameState) -> Action:
        logger.debug("%s starting searching for best move", self.role)
        my_state = state[self.role]
        if my_state.health < state.max_health and Item.CIGARETTES in my_state:
            logger.debug("Health is below max, using cigarettes")
            return Use(Item.CIGARETTES)

        known_state = MinMaxState(
            visible_state=state, hidden_state=self._hidden_state
        )

        logger.debug("Known state is %s", known_state)
        best_move = pick_move(known_state).move

        logger.debug("Decided that the best move is %s", best_move)
        if best_move is None:
            raise ValueError(
                f"There does not appear to be any valid move for state {state}"
            )
        self._last_move = best_move

        return best_move

    def _use_shell(self, shell):
        self._hidden_state = self._hidden_state.use(shell)

    def _set_next_shell(self, shell):
        self._hidden_state = replace(self._hidden_state, next_shell=shell)

    def receive_feedback(self, feedback: Feedback):
        match feedback:
            case Hit(_):
                self._use_shell(Shell.LIVE)
            case Miss():
                self._use_shell(Shell.BLANK)
            case See(shell):
                match self._last_move:
                    case Use(Item.BEER):
                        self._use_shell(shell)
                    case Use(Item.GLASS):
                        self._set_next_shell(shell)

    def opponent_move(self, action: Action, feedback: Feedback):
        match feedback:
            case Hit(_):
                self._use_shell(Shell.LIVE)
            case Miss():
                self._use_shell(Shell.BLANK)
            case See(shell):
                self._use_shell(shell)
