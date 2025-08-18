from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto, unique


@unique
class GameRole(Enum):
    """Which role are we talking about from the game's perspective."""

    PLAYER = auto()
    DEALER = auto()

    @property
    def oponent(self):
        """The actor's oponent's role."""
        if self == GameRole.PLAYER:
            return GameRole.DEALER
        return GameRole.PLAYER


@unique
class RelativeRole(Enum):
    """Which role are we talking about from the players' perspectives."""

    SELF = auto()
    OPPONENT = auto()


@unique
class Item(Enum):
    """Items which can be used to gain stats boosts."""

    GLASS = auto()
    CIGARETTES = auto()
    BEER = auto()
    SAW = auto()
    HANDCUFFS = auto()


@unique
class Shell(Enum):
    """Shells can be live or blank."""

    LIVE = auto()
    BLANK = auto()


class Action(ABC):
    """The action which the user wants to take.

    Can be either shooting or using an item
    """

    pass


@dataclass(frozen=True)
class Shoot(Action):
    """Indicates who the agent wants to shoot."""

    target: RelativeRole


@dataclass(frozen=True)
class Use(Action):
    """Which item does the agent want to use."""

    item: Item


@dataclass
class PlayerState:
    """The player's health and item counts.

    This should represent the information that a player could see looking at
    a live screen of Buckshot Roulette. Potentially there could be other,
    hidden elements of state wich the agent will need to keep track of
    themselves.
    """

    health: int
    items: dict[Item, int]


@dataclass
class GameState:
    """The information that is provided to an agent before they make a move.

    N.B. This information is presented relative to the agent's perspective, so
    that the agent does not need to know whether they are the dealer or the
    player.
    """

    personal_state: PlayerState
    opponent_state: PlayerState


class Feedback(ABC):
    """Any information that could be sent to the agent after they move."""

    pass


@dataclass
class Hit(Feedback):
    """Tell the agent they scored a hit."""

    target: RelativeRole


@dataclass
class SeeShell(Feedback):
    """Tell the agent what color shell they have just seen.

    This could be a chambered shell, or one that has just been ejected. It is
    up to the agent to use context to know which is which.
    """

    shell: Shell
