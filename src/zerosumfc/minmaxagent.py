from dataclasses import dataclass, field, replace
from functools import cache
import logging

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
class MinMaxState:
    visible_state: GameState
    live_shells: int
    blank_shells: int
    next_shell: Shell | None = None

    def __post_init__(self):
        if self.live_shells < 0:
            raise ValueError("Live shells must be non-negative")
        if self.blank_shells < 0:
            raise ValueError("Blank shells must be non-negative")

    def shoot(self, target: Role) -> StateList:
        live_state = (
            MinMaxState(
                visible_state=self.visible_state.shoot(Shell.LIVE, target),
                live_shells=self.live_shells - 1,
                blank_shells=self.blank_shells,
            )
            if self.live_shells > 0
            else None
        )
        blank_state = (
            MinMaxState(
                visible_state=self.visible_state.shoot(Shell.BLANK, target),
                live_shells=self.live_shells,
                blank_shells=self.blank_shells - 1,
            )
            if self.blank_shells > 0
            else None
        )
        return self._shell_state(live_state, blank_state)

    def use_beer(self) -> StateList:
        new_visible_state = self._try_take(Item.BEER)

        live_state = (
            MinMaxState(
                visible_state=new_visible_state,
                live_shells=self.live_shells - 1,
                blank_shells=self.blank_shells,
            )
            if self.live_shells > 0
            else None
        )

        blank_state = (
            MinMaxState(
                visible_state=new_visible_state,
                live_shells=self.live_shells,
                blank_shells=self.blank_shells - 1,
            )
            if self.blank_shells > 0
            else None
        )
        return self._shell_state(live_state, blank_state)

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
        live_state = (
            replace(
                self, next_shell=Shell.LIVE, visible_state=new_visible_state
            )
            if self.live_shells > 0
            else None
        )

        blank_state = (
            replace(
                self, next_shell=Shell.BLANK, visible_state=new_visible_state
            )
            if self.blank_shells > 0
            else None
        )

        return self._shell_state(live_state, blank_state)

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

    def _shell_state(self, live_state, blank_state) -> StateList:
        if self.blank_shells == 0 and self.live_shells == 0:
            raise ValueError(
                "_shell_state() should not be called "
                "when there are no shells left"
            )
        if (
            blank_state is None
            or self.next_shell == Shell.LIVE
            or self.blank_shells == 0
        ):
            return [StateProb(1.0, live_state)]
        if (
            live_state is None
            or self.next_shell == Shell.BLANK
            or self.live_shells == 0
        ):
            return [StateProb(1.0, blank_state)]

        p_live = self.live_shells / (self.live_shells + self.blank_shells)
        return [
            StateProb(p_live, live_state),
            StateProb(1 - p_live, blank_state),
        ]

    def _try_take(self, item: Item) -> GameState:
        success, state = self.visible_state.take_item(item)
        if not success:
            raise ValueError("Agent tried to use unavailable item")
        return state


@dataclass(order=True)
class MoveOption:
    p_win: float
    move: Action | None = field(compare=False)


@cache
def pick_move(state: MinMaxState) -> MoveOption:
    logger.debug(f"pick_move() called with state: {state}")
    visible_state = state.visible_state
    if visible_state.player_state.health == 0:
        logger.debug("Player has lost, no moves to make")
        return MoveOption(0.0, None)
    if visible_state.dealer_state.health == 0:
        logger.debug("Player has won, no moves to make")
        return MoveOption(1.0, None)

    if state.blank_shells == 0 and state.live_shells == 0:
        logger.debug("No shells left estimating p_win")
        p_win = visible_state.player_state.health / (
            visible_state.player_state.health
            + visible_state.dealer_state.health
        )
        return MoveOption(p_win, None)

    options = list_moves(state)
    logger.debug("options are %s", options)
    options = [score_move(state, move) for move in options]

    logger.debug("Scored options are %s", options)
    best_move = None
    if visible_state.current_player == Role.PLAYER:
        logger.debug("Maximizing Player win probabity")
        best_move = max(options)
    else:
        logger.debug("Minimizing Player win probabilty")
        best_move = min(options)
    logger.debug(
        "best move for %s at %s is %s",
        visible_state.current_player,
        state,
        best_move,
    )
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
    if Item.GLASS in player_state and state.next_shell is None:
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
        self._next_shell = None
        self.reset_shells(0, 0)

    def reset_shells(self, live: int, blank: int) -> None:
        self._live = live
        self._blank = blank

    def get_move(self, state: GameState) -> Action:
        logger.debug("Starting searching for best move")
        my_state = state[self.role]
        if my_state.health < state.max_health and Item.CIGARETTES in my_state:
            logger.debug("Health is below max, using cigarettes")
            return Use(Item.CIGARETTES)

        known_state = MinMaxState(
            visible_state=state,
            live_shells=self._live,
            blank_shells=self._blank,
            next_shell=self._next_shell,
        )
        best_move = pick_move(known_state).move

        logger.debug(
            "Decided that %s is the best move for %s", best_move, known_state
        )
        if best_move is None:
            raise ValueError(
                f"There does not appear to be any valid move for state {state}"
            )
        self._last_move = best_move
        if type(self._last_move) is Shoot:
            self._next_shell = None
        return best_move

    def receive_feedback(self, feedback: Feedback):
        match self._last_move:
            case Use(Item.BEER):
                self._update_counts(feedback)
            case Use(Item.GLASS):
                match feedback:
                    case See(shell):
                        self._next_shell = shell

    def opponent_move(self, action: Action, feedback: Feedback):
        match action:
            case Shoot(_) | Use(Item.BEER):
                self._update_counts(feedback)

    def _update_counts(self, feedback: Feedback):
        match feedback:
            case Hit(_) | See(Shell.LIVE):
                self._next_shell=None
                self._live -= 1
            case Miss() | See(Shell.BLANK):
                self._next_shell=None
                self._blank -= 1
        if self._live < 0 or self._blank < 0:
            raise ValueError(
                f"Agent thinks it has a negative shells: "
                "(live, blank) = ({self._live}, {self._blank})"
            )
