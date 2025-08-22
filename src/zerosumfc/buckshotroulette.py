"""Simulates a game of Buckshot Roulette."""

import random
from collections.abc import Sequence

from zerosumfc.agents import Agent, RandomAgent
from zerosumfc.data import (
    Action,
    Feedback,
    GameState,
    Hit,
    Item,
    PlayerState,
    Role,
    SeeShell,
    Shell,
    Shoot,
    Use,
)
from zerosumfc.textagent import TextAgent


class PlayerStateManager:
    """Manages the state for a player.

    This class will ensure that the player's health stays within bounds and
    that they cannot have too many items.
    """

    MAX_ITEMS = 8

    def __init__(self, max_health: int):
        """Initialise with max health and no items."""
        self._health = max_health
        self._max_health = max_health

        self._inventory = dict()

    def damage(self, amount: int) -> None:
        """Reduce health bracketed above 0."""
        self._health = max(0, self._health - amount)

    def heal(self, amount: int) -> None:
        """Increase health, bracketed to stay <= max_health."""
        self._health = min(self._max_health, self._health + amount)

    @property
    def item_count(self):
        """The total number of items in the player's inventory."""
        return sum(self._inventory.values())

    def add_item(self, item: Item):
        """Add this item to the players inventory if it is not already full.

        The maximum number of items is controlled by
        PlayerStateManager.MAX_ITEMS.
        """
        if self.item_count < PlayerStateManager.MAX_ITEMS:
            self._inventory[item] = self._inventory.get(item, 0) + 1

    def add_all(self, items: Sequence[Item]):
        """Add multiple items to the inventory."""
        for item in items:
            self.add_item(item)

    def is_available(self, item: Item) -> bool:
        """Return true if the player have the item in their inventory."""
        return self._inventory.get(item, 0) > 0

    def use_item(self, item: Item) -> bool:
        """If the item count is greater than 0, use up the item."""
        if self.is_available(item):
            self._inventory[item] -= 1
            return True
        return False

    @property
    def state(self):
        """Get the publicly visible player state."""
        return PlayerState(
            health=self._health, inventory=dict(self._inventory)
        )


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


class Game:
    """Keeps track of a game of Buckshot Roulette played between two agents."""

    def __init__(self, dealer: Agent, player: Agent, initial_health: int):
        """Initailise a game with two agents and set their initial health."""
        self._agents = {Role.DEALER: dealer, Role.PLAYER: player}
        self._player_state = {
            Role.DEALER: PlayerStateManager(initial_health),
            Role.PLAYER: PlayerStateManager(initial_health),
        }
        self._current_role = Role.PLAYER
        self._handcuff_active = False
        self._saw_active = False
        self._reload()

    def _reload(self):
        self._shotgun = Shotgun.random()
        for role, agent in self._agents.items():
            agent.reset_shells(*self._shotgun.initial_load)
            new_items = [random.choice(list(Item)) for _ in range(3)]
            self._player_state[role].add_all(new_items)
        self._current_role = Role.PLAYER

    def _shoot(self, target: Role) -> Feedback | None:
        shell = self._shotgun.pop()
        target_state = self._player_state[target]
        if shell == Shell.LIVE:
            damage = 2 if self._saw_active else 1
            target_state.damage(damage)
        self._saw_active = False
        if target != self._current_role or shell == Shell.LIVE:
            self._end_turn()
        if shell == Shell.LIVE:
            return Hit(target)

    def _use_item(self, item: Item) -> Feedback | None:
        state_manager = self._player_state[self._current_role]
        if state_manager.use_item(item):
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
                    state_manager.heal(1)
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

    def run(self) -> Role:
        """Start the game and continue until we have a winner."""
        while self._winner is None:
            actor = self._current_role
            opponent = actor.oponent
            agent = self._agents[actor]
            dealer_state = self._player_state[Role.DEALER].state
            player_state = self._player_state[Role.PLAYER].state
            state = GameState(
                dealer_state=dealer_state, player_state=player_state
            )
            action = agent.get_move(state)
            feedback = self._perform_action(action)
            agent.receive_feedback(feedback)
            self._agents[opponent].opponent_move(action, feedback)
            if self._shotgun.empty:
                self._reload()
        return self._winner

    @property
    def _winner(self) -> Role | None:
        if self._player_state[Role.DEALER].state.health == 0:
            return Role.PLAYER
        if self._player_state[Role.PLAYER].state.health == 0:
            return Role.DEALER

    def _end_turn(self):
        if self._handcuff_active:
            self._handcuff_active = False
            return
        if self._current_role == Role.PLAYER:
            self._current_role = Role.DEALER
        else:
            self._current_role = Role.PLAYER


def main():
    """Run a game of Buckshot Roulette between the random agent and a human."""
    dealer = RandomAgent(Role.DEALER)
    player = TextAgent(Role.PLAYER)
    game = Game(dealer, player, 4)
    winner = game.run()
    print(f"The winner is {winner}")


if __name__ == "__main__":
    main()
