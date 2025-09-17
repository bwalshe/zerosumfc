"""Simulates a game of Buckshot Roulette."""

import logging
import random
from copy import copy
from dataclasses import dataclass, replace

from zerosumfc.agents import Agent
from zerosumfc.data import (
    Action,
    Feedback,
    GameState,
    Heal,
    Hit,
    Item,
    Miss,
    Role,
    See,
    Shell,
    Shoot,
    Use,
    Used,
)
from zerosumfc.minmaxagent import MinMaxAgent
from zerosumfc.textagent import TextAgent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FullGameState:
    visible_state: GameState
    shells: list[Shell]

    @classmethod
    def new(cls, initial_health: int) -> "FullGameState":
        visible_state = GameState.new(initial_health)
        return cls(visible_state=visible_state, shells=[])

    def use_item(self, item: Item) -> tuple[Feedback | None, "FullGameState"]:
        current_player = self.visible_state.current_player
        logger.info("%s tries to use %s", current_player, item)
        taken, visible_state = self.visible_state.take_item(item)
        state = replace(self, visible_state=visible_state)
        if taken:
            match item:
                case Item.GLASS:
                    shell = self.peek_shell()
                    if shell is not None:
                        logger.info("%s seen", shell)
                        return See(shell), state
                case Item.BEER:
                    shell, state = state.pop_shell()
                    if shell is not None:
                        logger.info("%s seen", shell)
                        return See(shell), state
                case Item.CIGARETTES:
                    return Heal(1), replace(
                        state, visible_state=visible_state.heal_current_player(1)
                    )
                case Item.SAW:
                    return Used(item), _replace_visible(state, saw_active=True)

                case Item.HANDCUFFS:
                    return Used(item), _replace_visible(state,
                            handcuffs_active=True
                    )
        else:
            logger.info("No %s in %s inventory", item, current_player)
        return None, state

    def shoot(
        self, target: Role
    ) -> tuple[Feedback, "FullGameState"]:
        logger.info("%s shoots %s", self.visible_state.current_player, target)
        shell, state = self.pop_shell()
        state = replace(state, visible_state=self.visible_state.shoot(shell, target))
        if shell == Shell.LIVE:
            logger.info("It's a hit!")
            return Hit(target), state
        else:
            logger.info("It was a blank shell.")
            return Miss(), state


    def reload(self, max_shells=4) -> tuple[tuple[int, int], "FullGameState"]:
        live = random.randint(1, max_shells)
        blank = random.randint(1, max_shells)
        logger.info("Reloading with %d live shells and %d blanks", live, blank)
        shells = [Shell.LIVE] * live + [Shell.BLANK] * blank
        random.shuffle(shells)
        state = replace(self, shells=shells)
        state = _replace_visible(state, current_player=Role.PLAYER)
        return (live, blank), state

    def peek_shell(self) -> Shell:
        return self.shells[-1]

    def pop_shell(self) -> tuple[Shell, "FullGameState"]:
        shells = copy(self.shells)
        shell = shells.pop()
        return shell, replace(self, shells=shells)


def _replace_visible(state, **kwargs):
    visible_state = replace(state.visible_state, **kwargs)
    return replace(state, visible_state=visible_state)


class Game:
    """Keeps track of a game of Buckshot Roulette played between two agents."""

    def __init__(self, dealer: Agent, player: Agent, initial_health: int):
        """Initailise a game with two agents and set their initial health."""
        self._agents = {Role.DEALER: dealer, Role.PLAYER: player}
        self._state = FullGameState.new(initial_health)

    def _perform_action(self, action: Action) -> Feedback | None:
        match action:
            case Shoot(target):
                result, self._state = self._state.shoot(target)
                return result

            case Use(item):
                result, self._state = self._state.use_item(item)
                return result

    def run(self) -> Role:
        """Start the game and continue until we have a winner."""
        logger.info(self._state)
        while self._winner is None:
            if not self._state.shells:
                self._reload()
            current_player = self._state.visible_state.current_player
            shooter = self._agents[current_player]
            opponent = self._agents[current_player.opponent]
            action = shooter.get_move(self._state.visible_state)
            feedback = self._perform_action(action)
            logger.info(self._state)
            shooter.receive_feedback(feedback)
            opponent.opponent_move(action, feedback)
        return self._winner

    def _reload(self):
        counts, self._state = self._state.reload()
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
    logging.basicConfig(
        filename="buckshot.log", encoding="utf-8", level=logging.INFO
    )
    dealer = MinMaxAgent(Role.DEALER)
    player = TextAgent(Role.PLAYER)
    game = Game(dealer, player, 4)
    winner = game.run()
    if winner == Role.PLAYER:
        print("The dealer is dead. You have won.")
    else:
        print("You died. The dealer has won.")
    logger.info("Winner: %s", winner)


if __name__ == "__main__":
    main()
