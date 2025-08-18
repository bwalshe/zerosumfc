"""Simulates a game of Buckshot Roulette."""

import random

from zerosumfc.agents import Agent, RandomAgent, StdioAgent
from zerosumfc.data import (
    Action,
    Feedback,
    GameRole,
    GameState,
    Hit,
    Item,
    PlayerState,
    RelativeRole,
    SeeShell,
    Shell,
    Shoot,
)


class Health:
    """Keeps track of the dealer and player's health stats.

    Ensures that they cannot go above the max or below zero.
    """

    def __init__(self, dealer_health, player_health, max_health):
        """Set the health for the dealer and player, along with the maximum."""
        self._state = {
            GameRole.DEALER: dealer_health,
            GameRole.PLAYER: player_health,
        }
        self._max_health = max_health

    def __getitem__(self, role: GameRole) -> int:
        """Get the health for the actor."""
        return self._state[role]

    def damage(self, target: GameRole, damage: int):
        """Deal damage to the target."""
        self._state[target] = max(0, self._state[target] - damage)

    def heal(self, target: GameRole):
        """Heal the traget."""
        self._state[target] = min(self._max_health, self._state[target] + 1)

    def as_tuple(self):
        """Convert to the tuple (dealer health, player health)."""
        return tuple(self._state[a] for a in GameRole)

    @classmethod
    def start(cls, health):
        """Create a new Health object with both actors at max health."""
        return cls(health, health, health)


class Shotgun:
    """Keeps track of the randomized shells in the game."""

    def __init__(self, num_live: int, num_blank):
        """Initialise the shotgun with the specified number of shells.

        Just specify the number of shells, the order is randomised.
        """
        self._live = num_live
        self._blanks = num_blank
        self._shells = [Shell.LIVE] * self._live + [Shell.BLANK] * self._blanks
        random.shuffle(self._shells)
        self._next_shell = None

    @property
    def initial_load(self) -> tuple[int, int]:
        """Get the number of shells that were initailly loaded in the gun."""
        return (self._live, self._blanks)

    @property
    def empty(self):
        """Is this gun empty."""
        return not self._shells

    def peek(self) -> Shell | None:
        """Check what kind of shell is currently chambered."""
        if self._shells:
            return self._shells[-1]

    def pop(self) -> Shell | None:
        """Fire/Eject the chambered shell."""
        if self._shells:
            return self._shells.pop()

    @classmethod
    def random(cls, max_shells=4):
        """Initialise a shotgun with a randomised number of shells."""
        live = random.randint(1, max_shells)
        blank = random.randint(1, max_shells)
        return cls(live, blank)


class ItemTable:
    """Dict like object to keep track of which items the actor has."""

    def __init__(self, max_capacity=8):
        """Initialise the table with 0 items."""
        self._state = {item: 0 for item in Item}
        self._max_capacity = max_capacity

    def __len__(self):
        """Total number of items in the actor's possesion."""
        return sum(self._state.values())

    def add(self, item: Item) -> bool:
        """Add an item to the table if it is below max capacity."""
        if len(self) >= self._max_capacity:
            return False
        self._state[item] += 1
        return True

    def to_dict(self) -> dict[Item, int]:
        """Convert this back to a normal dict."""
        return dict(self._state.items())

    def use_item(self, item: Item) -> bool:
        """Try to use an item.

        If the item is available, return true and decease the item's count.
        """
        if self._state[item] > 1:
            self._state[item] -= 1
            return True
        return False


class Game:
    """Keeps track of a game of Buckshot Roulette played between two agents."""

    def __init__(self, dealer: Agent, player: Agent, initial_health: int):
        """Initailise a game with two agents and set their initial health."""
        self._health = Health.start(initial_health)
        self._agents = {GameRole.DEALER: dealer, GameRole.PLAYER: player}

        self._current_actor = GameRole.PLAYER
        self._handcuff_active = False
        self._saw_active = False
        self._items = {
            GameRole.DEALER: ItemTable(),
            GameRole.PLAYER: ItemTable(),
        }
        self._reload()

    def _reload(self):
        self._shotgun = Shotgun.random()
        for agent in self._agents.values():
            agent.reset_shells(*self._shotgun.initial_load)

    def _translate(self, target: RelativeRole) -> GameRole:
        if target == RelativeRole.SELF:
            return self._current_actor
        return self._current_actor.oponent

    def _shoot(self, target: RelativeRole) -> Feedback | None:
        shell = self._shotgun.pop()
        if shell == Shell.LIVE:
            damage = 2 if self._saw_active else 1
            self._health.damage(self._translate(target), damage)
        self._saw_active = False
        if target == RelativeRole.OPPONENT or shell == Shell.LIVE:
            self._end_turn()
        if shell == Shell.LIVE:
            return Hit(target)

    def _use_item(self, item: Item) -> Feedback | None:
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

    def _perform_action(self, action: Action) -> Feedback | None:
        match action:
            case Shoot(target):
                return self._shoot(target)
            case Use(item):
                return self._use_item(item)

    def run(self) -> GameRole:
        """Start the game and continue until we have a winner."""
        while self._winner is None:
            actor = self._current_actor
            opponent = actor.oponent
            agent = self._agents[actor]
            actor_state = self._state_for_role(actor)
            opponent_state = self._state_for_role(opponent)
            state = GameState(
                personal_state=actor_state, opponent_state=opponent_state
            )
            action = agent.get_move(state)
            feedback = self._perform_action(action)
            agent.receive_feedback(feedback)

            if self._shotgun.empty:
                self._reload()
        return self._winner

    def _state_for_role(self, role: GameRole):
        return PlayerState(
            health=self._health[role], items=self._items[role].to_dict()
        )

    @property
    def _winner(self) -> GameRole | None:
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


def main():
    """Run a game of Buckshot Roulette between the random agent and a human."""
    dealer = RandomAgent()
    player = StdioAgent()
    game = Game(dealer, player, 4)
    winner = game.run()
    print(f"The winner is {winner}")


if __name__ == "__main__":
    main()
