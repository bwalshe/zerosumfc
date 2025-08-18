"""Agents capable of playing Buckshot Roulette"""

import random
from abc import ABC, abstractmethod

from .data import Action, Feedback, GameState, RelativeRole, Shoot, Use


class Agent(ABC):
    """An agent capable of playing Buckshot Roulette.

    The primary function of this agent is to implement the `get_move` method
    which selects a move based on the visible state of the game.
    """

    @abstractmethod
    def reset_shells(self, live: int, blank: int):
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


class RandomAgent(Agent):
    """Dumb agent that just picks a move at random."""

    def reset_shells(self, live: int, blank: int):
        """Ignored."""
        pass

    def get_move(self, state: GameState) -> Action:
        """Pick a move at random based on what is currently possible."""
        actions: list[Action] = [
            Shoot(RelativeRole.OPPONENT),
            Shoot(RelativeRole.SELF),
        ]
        for item, count in state.personal_state.items.items():
            if count > 0:
                actions.append(Use(item))
        return random.choice(actions)

    def receive_feedback(self, feedback: Feedback | None):
        """Ignored."""
        pass


class StdioAgent(Agent):
    """Prints game info to a stream and queries the user for their move."""

    def reset_shells(self, live: int, blank: int):
        """Print out the number of shells that have been loaded."""
        print(
            f"The gun has been loaded with {live} rounds and {blank} blanks."
        )

    def get_move(self, state: GameState) -> Action:
        """Prompt the user for a move & parse their response."""
        StdioAgent._print_state(state)
        print("You shoot the dealer")
        return Shoot(RelativeRole.OPPONENT)

    def receive_feedback(self, feedback: Feedback | None):
        """Print out the feedback if it is not None."""
        if feedback is not None:
            print(feedback)

    @staticmethod
    def _print_state(state: GameState):
        print(f"Your health: {state.personal_state.health}")
        print(f"Opponent's health: {state.opponent_state.health}")
        print("Your items:")
        for item, count in state.personal_state.items.items():
            if count > 0:
                print(f"{item.name} ({count})")
