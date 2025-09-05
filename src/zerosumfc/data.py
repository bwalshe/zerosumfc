"""Data classes used by the game and the agents to communicate."""

from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto, unique
from types import MappingProxyType


@unique
class Role(Enum):
    """Which role are we talking about from the game's perspective."""

    PLAYER = auto()
    DEALER = auto()

    @property
    def opponent(self):
        """The actor's opponent's role."""
        if self == Role.PLAYER:
            return Role.DEALER
        return Role.PLAYER


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

    target: Role


@dataclass(frozen=True)
class Use(Action):
    """Which item does the agent want to use."""

    item: Item


@dataclass(frozen=True)
class PlayerState:
    """The player's health and item counts.

    This should represent the information that a player could see looking at
    a live screen of Buckshot Roulette. Potentially there could be other,
    hidden elements of state wich the agent will need to keep track of
    themselves.
    """

    health: int
    inventory: MappingProxyType[Item, int]



@dataclass(frozen=True)
class GameState:
    """The information that is provided to an agent before they make a move.

    N.B. This information is presented relative to the agent's perspective, so
    that the agent does not need to know whether they are the dealer or the
    player.
    """

    dealer_state: PlayerState
    player_state: PlayerState
    current_player: Role
    saw_active: bool
    handcuffs_active: bool

    def __getitem__(self, role: Role) -> PlayerState:  # noqa: D105
        if role == Role.DEALER:
            return self.dealer_state
        if role == Role.PLAYER:
            return self.player_state


class Feedback(ABC):
    """Any information that could be sent to the agent after they move."""

    pass


@dataclass
class Hit(Feedback):
    """Tell the agent they scored a hit."""
    target: Role


@dataclass
class Miss(Feedback):
    pass


@dataclass(frozen=True)
class See(Feedback):
    """Tell the agent what color shell they have just seen.

    This could be a chambered shell, or one that has just been ejected. It is
    up to the agent to use context to know which is which.
    """

    shell: Shell

@dataclass(frozen=True)
class Heal(Feedback):
    amount: int

@dataclass
class Used(Feedback):
    item: Item
