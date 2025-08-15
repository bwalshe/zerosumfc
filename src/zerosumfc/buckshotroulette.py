from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto, unique
import random
from typing import Optional


@unique
class GameRole(Enum):
    PLAYER = auto()
    DEALER = auto()

    @property
    def oponent(self):
        if self == GameRole.PLAYER:
            return GameRole.DEALER
        return GameRole.PLAYER


@unique 
class RelativeRole(Enum):
    SELF = auto()
    OPPONENT = auto()

@unique
class Item(Enum):
    GLASS = auto()
    CIGARETTES = auto()
    BEER = auto()
    SAW = auto()
    HANDCUFFS = auto()


@unique
class Shell(Enum):
    LIVE = auto()
    BLANK = auto()


class Action(ABC):
    pass


@dataclass(frozen=True)
class Shoot(Action):
    target: RelativeRole


@dataclass(frozen=True)
class Use(Action):
    item: Item


@dataclass
class PlayerState:
    health: int
    items: dict[Item, int]


@dataclass
class GameState:
    personal_state: PlayerState
    opponent_state: PlayerState



class Feedback(ABC):
    pass

@dataclass
class Hit(Feedback):
    target: RelativeRole

@dataclass 
class SeeShell(Feedback):
    shell: Shell



class Agent(ABC):

    @abstractmethod
    def reset_shells(self, live:int, blank: int):
        pass

    @abstractmethod
    def get_move(self, state: GameState) -> Action:
        pass

    @abstractmethod
    def receive_feedback(self, feedback: Optional[Feedback]):
        pass


class Health:

    def __init__(self, dealer_health, player_health, max_health):
        self._state = {
            GameRole.DEALER: dealer_health,
            GameRole.PLAYER: player_health,
        }
        self._max_health = max_health

    def __getitem__(self, role: GameRole) -> int:
        return self._state[role]

    def damage(self, target: GameRole, damage: int):
        self._state[target] =  max(0, self._state[target] - damage)

    def heal(self, target: GameRole):
        self._state[target] = min(self._max_health, self._state[target] + 1)


    def as_tuple(self):
        return tuple(self._state[a] for a in GameRole)

    @classmethod
    def start(cls, health):
        return cls(health, health, health)



class Shotgun:
    def __init__(self, num_live: int, num_blank):
        self._live = num_live
        self._blanks = num_blank 
        self._shells = [Shell.LIVE] * self._live + [Shell.BLANK] * self._blanks
        random.shuffle(self._shells)
        self._next_shell = None

    @property
    def initial_load(self) -> tuple[int, int]:
        return (self._live, self._blanks)

    @property
    def empty(self):
        return not self._shells

    def peek(self) -> Shell | None:
        if self._shells:
            return self._shells[-1]

    def pop(self) -> Shell | None:
        if self._shells:
            return self._shells.pop()

    @classmethod
    def random(cls, max_shells=4):
        live = random.randint(1, max_shells)
        blank = random.randint(1, max_shells)
        return cls(live, blank)


class ItemTable:
    def __init__(self):
        self._state = {item:0 for item in Item}

    def add(self, item:Item):
        self._state[item] += 1
    
    def to_dict(self) -> dict[Item, int]:
        return dict(self._state.items())

    def use_item(self, item: Item) -> bool:
        if self._state[item] > 1:
            self._state[item] -= 1
            return True
        return False


class Game:
    def __init__(self, dealer: Agent, player: Agent, initial_health: int):
        self._health = Health.start(initial_health)
        self._agents = {
            GameRole.DEALER: dealer,
            GameRole.PLAYER: player
        }

        self._current_actor = GameRole.PLAYER
        self._handcuff_active = False
        self._saw_active = False
        self._items = {
            GameRole.DEALER: ItemTable(),
            GameRole.PLAYER: ItemTable()
        }
        self.reload()

    def reload(self):
        self._shotgun = Shotgun.random()
        for agent in self._agents.values():
            agent.reset_shells(*self._shotgun.initial_load)


    @property
    def initial_shells(self) -> tuple[int, int]:
        return self._shotgun.initial_load

    @property
    def player_health(self) -> int:
        return self._health[GameRole.PLAYER]

    @property
    def dealer_health(self) -> int:
        return self._health[GameRole.DEALER]

    def _translate(self, target: RelativeRole) -> GameRole:
        if target == RelativeRole.SELF:
            return self._current_actor
        return self._current_actor.oponent

    def shoot(self, target: RelativeRole) -> Feedback | None:
        shell = self._shotgun.pop()
        if shell == Shell.LIVE:
            damage = 2 if self._saw_active else 1
            self._health.damage(self._translate(target), damage)
        self._saw_active = False
        if target == RelativeRole.OPPONENT or shell == Shell.LIVE:
            self._end_turn()
        if shell == Shell.LIVE:
            return Hit(target)

    def use_item(self, item: Item) -> Feedback | None:
        if self._items[self._current_actor].use_item(item):
            match item:
                case Item.GLASS:
                    shell = self._shotgun.peek()
                    if shell is not None:
                        return SeeShell(shell) 
                case Item.BEER:
                    shell = self._shotgun.pop()
                    if shell is not None:
                        return SeeShell(shell)
                case Item.CIGARETTES:
                    self._health.heal(self._current_actor)
                case Item.SAW:
                    self._saw_active = True
                case Item.HANDCUFFS:
                    self._handcuff_active = True

    def perform_action(self, action: Action) -> Feedback | None:
        match action:
            case Shoot(target):
                return self.shoot(target)
            case Use(item):
                return self.use_item(item)

    def run(self) -> GameRole:
        while self.winner is None:
            actor = self._current_actor
            opponent = actor.oponent
            agent = self._agents[actor]
            actor_state = self._state_for_role(actor)
            opponent_state = self._state_for_role(opponent)
            state = GameState(
                personal_state=actor_state, 
                opponent_state=opponent_state)
            action = agent.get_move(state)
            feedback = self.perform_action(action)
            agent.receive_feedback(feedback)

            if self._shotgun.empty:
                self.reload()
        return self.winner


    def _state_for_role(self, role: GameRole):
            return PlayerState(
                health=self._health[role],
                items=self._items[role].to_dict()
            )

    @property
    def winner(self) -> GameRole | None:
        if self._health[GameRole.DEALER] == 0:
            return GameRole.PLAYER
        if self._health[GameRole.PLAYER] == 0:
            return GameRole.DEALER


    def _end_turn(self):
        if self._handcuff_active:
            self._handcuff_active = False
            return
        if self._current_actor == GameRole.PLAYER:
            self._current_actor = GameRole.DEALER
        else:
            self._current_actor = GameRole.PLAYER


