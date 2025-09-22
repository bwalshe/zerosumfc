"""Agents capable of playing Buckshot Roulette."""

import random
from abc import ABC, abstractmethod

from .data import Action, Feedback, GameState, Role, Shell, Shoot, Use


class Agent(ABC):
    """An agent capable of playing Buckshot Roulette.

    The primary function of this agent is to implement the `get_move` method
    which selects a move based on the visible state of the game.
    """

    def __init__(self, role: Role):
        """Set the role which this agent is acting as."""
        self._role = role

    @property
    def role(self):
        """The role this agent is playing in the game."""
        return self._role

    @abstractmethod
    def reset_shells(self, live: int, blank: int) -> None:
        """Informs the angent how many live and blank shells have been loaded.

        Called when the shotgun is reloaded. Does not tell the agent what order
        the shells have been inserted in.
        """
        pass

    @abstractmethod
    def get_move(self, state: GameState) -> Action:
        """Ask the agent to select a move based on the visible state.

        Note that 'visible' state is just the information that is presented
        on-screen during the Buckshot Roulette game. There may be elements of
        hidden game state which the agent needss to keep track of itself.
        """
        pass

    @abstractmethod
    def receive_feedback(self, feedback: Feedback | None):
        """Tell the agent the result of a move."""
        pass

    @abstractmethod
    def opponent_move(self, action: Action, result: Feedback | None) -> None:
        """Update the agent on its opponent's move and the result."""
        pass


class RandomAgent(Agent):
    """Dumb agent that just picks a move at random."""

    def reset_shells(self, live: int, blank: int):
        """Ignored."""
        pass

    def get_move(self, state: GameState) -> Action:
        """Pick a move at random based on what is currently possible."""
        actions: list[Action] = [
            Shoot(Role.DEALER),
            Shoot(Role.PLAYER),
        ]

        for item, count in state[self.role].items():
            if count > 0:
                actions.append(Use(item))
        return random.choice(actions)

    def receive_feedback(self, feedback: Shell | None):
        """Ignored."""
        pass

    def opponent_move(self, action: Action, result: Shell | None) -> None:
        """Ignored."""
        pass
