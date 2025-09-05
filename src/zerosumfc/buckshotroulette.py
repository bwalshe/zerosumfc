"""Simulates a game of Buckshot Roulette."""

import random
from collections.abc import Sequence
from copy import copy, replace
from dataclasses import dataclass
from types import MappingProxyType

from zerosumfc.agents import Agent, RandomAgent
from zerosumfc.data import (
    Action,
    Feedback,
    GameState,
    Heal,
    Hit,
    Item,
    Miss,
    PlayerState,
    Role,
    See,
    Shell,
    Shoot,
    Use,
    Used,
)
from zerosumfc.textagent import TextAgent


@dataclass
class FullGameState:
    visible_state: GameState
    shells: list[Shell]


class PlayerStateManager:
    """Manages the state for a player.

    This class will ensure that the player's health stays within bounds and
    that they cannot have too many items.
    """

    MAX_ITEMS = 8

    def __init__(self, max_health: int):
        """Initialise with max health and no items."""
        self._max_health = max_health

    def new(self) -> PlayerState:
        return PlayerState(
            health=self._max_health, inventory=MappingProxyType(dict())
        )

    def damage(self, state: PlayerState, amount: int) -> PlayerState:
        """Reduce health bracketed above 0."""
        new_health = max(0, state.health - amount)
        return replace(state, health=new_health)

    def heal(self, state: PlayerState, amount: int) -> PlayerState:
        """Increase health, bracketed to stay <= max_health."""
        new_health = min(self._max_health, state.health + amount)
        return replace(state, health=new_health)

    @classmethod
    def add_item(cls, state: PlayerState, item: Item) -> PlayerState:
        """Add this item to the players inventory if it is not already full.

        The maximum number of items is controlled by
        PlayerStateManager.MAX_ITEMS.
        """
        new_inventory = dict(state.inventory)
        item_count = sum(state.inventory.values())
        if item_count < cls.MAX_ITEMS:
            new_inventory[item] = new_inventory.get(item, 0) + 1
        return replace(state, inventory=MappingProxyType(new_inventory))

    @classmethod
    def add_all(cls, state: PlayerState, items: Sequence[Item]) -> PlayerState:
        """Add multiple items to the inventory."""
        new_state = copy(state)
        for item in items:
            new_state = cls.add_item(new_state, item)
        return new_state

    @staticmethod
    def is_available(state: PlayerState, item: Item) -> bool:
        """Return true if the player have the item in their inventory."""
        return state.inventory.get(item, 0) > 0

    @classmethod
    def take_item(
        cls, state: PlayerState, item: Item
    ) -> tuple[bool, PlayerState]:
        """If the item count is greater than 0, use up the item."""
        if cls.is_available(state, item):
            new_inventory = dict(state.inventory)
            new_inventory[item] -= 1
            return True, replace(state, inventory=new_inventory)
        return False, state


class GameStateManager:
    def __init__(self, initial_health: int):
        self._player_state_manager = PlayerStateManager(initial_health)

    def new(self) -> FullGameState:
        visible_state = GameState(
            dealer_state=self._player_state_manager.new(),
            player_state=self._player_state_manager.new(),
            current_player=Role.PLAYER,
            saw_active=False,
            handcuffs_active=False,
        )
        return FullGameState(visible_state=visible_state, shells=[])

    def use_item(
        self, state: FullGameState, item: Item
    ) -> tuple[Feedback | None, FullGameState]:
        current_player = state.visible_state.current_player
        player_state = state.visible_state[current_player]
        taken, new_player_sate = self._player_state_manager.take_item(
            player_state, item
        )
        state = self._replace_player(state, current_player, new_player_sate)
        if taken:
            match item:
                case Item.GLASS:
                    shell = self.peek_shell(state)
                    if shell is not None:
                        return See(shell), state
                case Item.BEER:
                    shell, state = self.pop_shell(state)
                    if shell is not None:
                        return See(shell), state
                case Item.CIGARETTES:
                    player_state = replace(
                        player_state, health=player_state.health + 1
                    )
                    state = self._replace_player(
                        state, current_player, player_state
                    )
                    return Heal(1), state
                case Item.SAW:
                    return Used(item), self._replace_visible(
                        state, saw_active=True
                    )
                case Item.HANDCUFFS:
                    return Used(item), self._replace_visible(
                        state, handcuffs_active=True
                    )
        return None, state

    def shoot(
        self, state: FullGameState, target: Role
    ) -> tuple[Feedback, FullGameState]:
        shell, state = self.pop_shell(state)
        target_state = state.visible_state[target]
        damage = 2 if state.visible_state.saw_active else 1
        handcuff = state.visible_state.handcuffs_active
        state = self._replace_visible(state, handcuffs_active=False)
        current_player = state.visible_state.current_player
        if shell == Shell.LIVE:
            next_player = (
                current_player if handcuff else current_player.opponent
            )
            target_state = replace(
                target_state, health=target_state.health - damage
            )
            state = self._replace_player(state, target, target_state)
            state = self._replace_visible(state, current_player=next_player)
            return Hit(target), state
        else:
            next_player = (
                current_player
                if target == current_player or handcuff
                else current_player.opponent
            )
            state = self._replace_visible(state, current_player=next_player)
            return Miss(), state

    @classmethod
    def reload(
        cls, state: FullGameState, max_shells=4
    ) -> tuple[tuple[int, int], FullGameState]:
        live = random.randint(1, max_shells)
        blank = random.randint(1, max_shells)
        shells = [Shell.LIVE] * live + [Shell.BLANK] * blank
        random.shuffle(shells)
        state = replace(state, shells=shells)
        state = cls._replace_visible(state, current_player=Role.PLAYER)
        return (live, blank), state

    @staticmethod
    def peek_shell(state: FullGameState) -> Shell:
        return state.shells[-1]

    @staticmethod
    def pop_shell(state: FullGameState) -> tuple[Shell, FullGameState]:
        shells = copy(state.shells)
        shell = shells.pop()
        return shell, replace(state, shells=shells)

    @staticmethod
    def _replace_visible(state: FullGameState, **kwargs) -> FullGameState:
        new_visible_state = replace(state.visible_state, **kwargs)
        return replace(state, visible_state=new_visible_state)

    @classmethod
    def _replace_player(
        cls, state: FullGameState, role: Role, player_state: PlayerState
    ) -> FullGameState:
        if role == Role.DEALER:
            return cls._replace_visible(state, dealer_state=player_state)
        else:
            return cls._replace_visible(state, player_state=player_state)


class Game:
    """Keeps track of a game of Buckshot Roulette played between two agents."""

    def __init__(self, dealer: Agent, player: Agent, initial_health: int):
        """Initailise a game with two agents and set their initial health."""
        self._agents = {Role.DEALER: dealer, Role.PLAYER: player}
        self._state_manager = GameStateManager(initial_health)
        self._state = self._state_manager.new()

    def _perform_action(self, action: Action) -> Feedback | None:
        match action:
            case Shoot(target):
                result, self._state = self._state_manager.shoot(
                    self._state, target
                )
                return result

            case Use(item):
                result, self._state = self._state_manager.use_item(
                    self._state, item
                )
                return result

    def run(self) -> Role:
        """Start the game and continue until we have a winner."""
        while self._winner is None:
            if not self._state.shells:
                self._reload()
            current_player = self._state.visible_state.current_player
            shooter = self._agents[current_player]
            opponent = self._agents[current_player.opponent]
            action = shooter.get_move(self._state.visible_state)
            feedback = self._perform_action(action)
            shooter.receive_feedback(feedback)
            opponent.opponent_move(action, feedback)
        return self._winner

    def _reload(self):
        counts, self._state = self._state_manager.reload(self._state)
        for agent in self._agents.values():
            agent.reset_shells(*counts)

    @property
    def _winner(self) -> Role | None:
        if self._state.visible_state.dealer_state.health == 0:
            return Role.PLAYER
        if self._state.visible_state.player_state.health == 0:
            return Role.DEALER


def main():
    """Run a game of Buckshot Roulette between the random agent and a human."""
    dealer = RandomAgent(Role.DEALER)
    player = TextAgent(Role.PLAYER)
    game = Game(dealer, player, 4)
    winner = game.run()
    print(f"The winner is {winner}")


if __name__ == "__main__":
    main()
