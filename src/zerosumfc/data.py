"""Data classes used by the game and the agents to communicate."""

from abc import ABC
from copy import copy
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum, auto, unique
from types import MappingProxyType
from typing import ClassVar


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

    MAX_ITEMS: ClassVar[int] = 8

    health: int
    glass_count: int = 0
    beer_count: int = 0
    saw_count: int = 0
    handcuffs_count: int = 0
    cigarettes_count: int = 0

    def damage(self, amount: int) -> "PlayerState":
        """Reduce health bracketed above 0."""
        new_health = max(0, self.health - amount)
        return replace(self, health=new_health)

    def heal(self, amount: int, max_health: int) -> "PlayerState":
        """Increase health, bracketed to stay <= max_health."""
        new_health = min(max_health, self.health + amount)
        return replace(self, health=new_health)

    def add_item(self, item: Item) -> "PlayerState":
        """Add this item to the players inventory if it is not already full.

        The maximum number of items is controlled by
        PlayerStateManager.MAX_ITEMS.
        """
        if self.total_items >= self.MAX_ITEMS:
            return self

        match item:
            case Item.GLASS:
                return replace(self, glass_count=self.glass_count + 1)
            case Item.BEER:
                return replace(self, beer_count=self.beer_count + 1)
            case Item.HANDCUFFS:
                return replace(self, handcuffs_count=self.handcuffs_count + 1)
            case Item.CIGARETTES:
                return replace(
                    self, cigarettes_count=self.cigarettes_count + 1
                )
            case Item.SAW:
                return replace(self, saw_count=self.saw_count + 1)

    def add_all(self, items: Sequence[Item]) -> "PlayerState":
        """Add multiple items to the inventory."""
        state = copy(self)
        for item in items:
            state = state.add_item(item)
        return state

    def take_item(self, item: Item) -> tuple[bool, "PlayerState"]:
        """If the item count is greater than 0, use up the item."""
        found = False
        state = self
        if item in self:
            found = True
            match item:
                case Item.GLASS:
                    state = replace(self, glass_count=self.glass_count - 1)
                case Item.BEER:
                    state = replace(self, beer_count=self.beer_count - 1)
                case Item.HANDCUFFS:
                    state = replace(
                        self, handcuffs_count=self.handcuffs_count - 1
                    )
                case Item.CIGARETTES:
                    state = replace(
                        self, cigarettes_count=self.cigarettes_count - 1
                    )
                case Item.SAW:
                    state = replace(self, saw_count=self.saw_count - 1)
        return found, state

    def __getitem__(self, item: Item) -> int:
        match item:
            case Item.GLASS:
                return self.glass_count
            case Item.BEER:
                return self.beer_count
            case Item.HANDCUFFS:
                return self.handcuffs_count
            case Item.CIGARETTES:
                return self.cigarettes_count
            case Item.SAW:
                return self.saw_count

    def items(self):
        for item in list(Item):
            yield item, self[item]

    @property
    def total_items(self) -> int:
        return sum(self[item] for item in list(Item))

    def __contains__(self, item: Item) -> bool:
        """Return true if the player have the item in their inventory."""
        return self[item] > 0


@dataclass(frozen=True)
class GameState:
    """The information that is provided to an agent before they make a move.

    N.B. This information is presented relative to the agent's perspective, so
    that the agent does not need to know whether they are the dealer or the
    player.
    """

    player_state: PlayerState
    dealer_state: PlayerState
    max_health: int
    current_player: Role = Role.PLAYER
    saw_active: bool = False
    handcuffs_active: bool = False

    def __post_init__(self):
        for health in (self.player_state.health, self.dealer_state.health):
            if health > self.max_health:
                raise ValueError(
                    f"health ({health}) exceeds maximum ({self.max_health}"
                )

    def __getitem__(self, role: Role) -> PlayerState:  # noqa: D105
        if role == Role.DEALER:
            return self.dealer_state
        if role == Role.PLAYER:
            return self.player_state

    @classmethod
    def new(cls, max_health: int) -> "GameState":
        return cls(
            player_state=PlayerState(max_health),
            dealer_state=PlayerState(max_health),
            max_health=max_health,
        )

    def reset_modifiers(self) -> "GameState":
        return replace(self, handcuffs_active=False, saw_active=False)

    def end_turn(self) -> "GameState":
        if self.handcuffs_active:
            return self.reset_modifiers()
        return replace(
            self.reset_modifiers(), current_player=self.current_player.opponent
        )

    def shoot(self, shell: Shell, target: Role) -> "GameState":
        """Reduce health bracketed above 0."""
        if shell == Shell.BLANK and target == self.current_player:
            return replace(self, saw_active=False)
        amount = 1 if shell == Shell.LIVE else 0
        if self.saw_active:
            amount *= 2
        player_state = self[target].damage(amount)
        return self._replace_player(player_state, target).end_turn()

    def heal_current_player(self, amount: int) -> "GameState":
        """Increase health, bracketed to stay <= max_health."""
        new_health = min(
            self.max_health, self[self.current_player].health + amount
        )
        new_state = replace(self[self.current_player], health=new_health)
        return self._replace_player(new_state, self.current_player)

    def take_item(self, item: Item) -> tuple[bool, "GameState"]:
        taken, player_state = self[self.current_player].take_item(item)
        return taken, self._replace_player(player_state, self.current_player)

    def add_all(
        self, player_items: Sequence[Item], dealer_items: Sequence[Item]
    ) -> "GameState":
        player_state = self.player_state.add_all(player_items)
        dealer_state = self.dealer_state.add_all(dealer_items)
        return replace(
            self, player_state=player_state, dealer_state=dealer_state
        )

    def _replace_player(
        self, player_state: PlayerState, player: Role
    ) -> "GameState":
        if player == Role.DEALER:
            return replace(self, dealer_state=player_state)
        else:
            return replace(self, player_state=player_state)

    def set_player(self, player: Role, **kwargs):
        new_player_state = replace(self[player], **kwargs)
        return self._replace_player(new_player_state, player)


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
