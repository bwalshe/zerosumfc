"""A text based Buckshot Roulette agent."""

from dataclasses import dataclass
from types import MappingProxyType

from zerosumfc.agents import Agent 
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
    Shoot,
    Use,
    Used
)


class TextAgent(Agent):
    """Prints game info to a stream and queries the user for their move."""

    def __init__(self, role: Role):
        """Initialise the agent for the given role."""
        super().__init__(role)
        self._parser = ActionParser(role)
        self._last_target = None

    def reset_shells(self, live: int, blank: int):
        """Print out the number of shells that have been loaded."""
        print(
            f"The gun has been loaded with {live} live rounds and {blank} "
            "blanks."
        )

    def get_move(self, state: GameState) -> Action:
        """Prompt the user for a move & parse their response."""
        self._print_state(state)
        while True:
            command = input("What do you want to do?\n")
            match self._parser(command):
                case ParseFailure(message):
                    print(f"Failed to parse command. {message}")
                case action:
                    return action

    def receive_feedback(self, feedback: Feedback | None):
        """Print out the feedback if it is not None."""
        match feedback:
            case Hit(target):
                if target == self.role:
                    print("You shot yourself!")
                else:
                    print("You score a hit!")
            case Miss():
                print("You pull the trigger... it's a blank!.")
            case Used(item):
                print(f"You used the {item.name.lower()}")
            case Heal(amount):
                print(f"You healed {amount} point(s)")
            case See(shell):
                print(f"You see a {shell.name} shell")
            case _:
                breakpoint()
                print("You can't do that.")
        print()

    def opponent_move(self, action: Action, result: Feedback | None) -> None:
        """Update the agent on its opponent's move and the result."""
        print("Your oponent ", end="")
        match action:
            case Use(item):
                print(f"used a {item.name.lower()}")
            case Shoot(target):
                target_name = "you" if target == self.role else "themself"
                print(f"aims at {target_name} and pulls the trigger.")
        match result:
            case Hit(target):
                if target == self.role:
                    print("You've been shot!")
                else:
                    print("They shot themself!")
            case Miss():
                print("It was a blank.")
            case None:
                print("Nothing happens")
            case _:
                print(result)
        print()

    def _print_state(self, state: GameState):
        personal_state = state[self._role]
        opponent_state = state[self._role.opponent]
        print(f"Your health: {personal_state.health}")
        print(f"Opponent's health: {opponent_state.health}")
        print("Your items:")
        self._print_items(personal_state)
        print("Your opponent's items")
        self._print_items(opponent_state)

    @staticmethod
    def _print_items(state: PlayerState):
        if state.total_items == 0:
            print("Nothing.")
        else:
            for item, count in state.items():
                if count > 0:
                    print(f"{item.name} ({count})")


@dataclass
class ParseFailure:
    """If parsing has failed this will explain the reason."""

    message: str


class ActionParser:
    """A simple parser to recognise actions.

    This parser is capable of telling which role (DEALER|PLAYER) the user is
    talking about when they use relative terms like "me" or "opponent"
    """

    def __init__(self, me: Role):
        """Initialise for the given role.

        This class needs to know what role is being played so that it can
        handle relative naming.
        """
        self._me = me

    def __call__(self, input: str) -> Action | ParseFailure:
        """Attempt to parse the input using any of the availabel rules."""
        input = input.strip().upper()
        action = self.parse_item(input)
        if action is not None:
            return action
        action = self.parse_shoot(input)
        if action is not None:
            return action

        return ParseFailure("Unrecognised action.")

    def parse_item(self, text: str) -> Use | ParseFailure | None:
        """Attempt to parse the line as a USE action."""
        prefix = "USE"
        if not text.startswith(prefix):
            return None
        item = text.removeprefix(prefix).strip()
        try:
            return Use(Item[item])
        except KeyError:
            return ParseFailure(f"Unknown item '{item}'")

    def parse_shoot(self, text: str) -> Shoot | ParseFailure | None:
        """Attempt to parse the line as a SHOOT action."""
        prefix = "SHOOT"
        if not text.startswith(prefix):
            return None
        match text.removeprefix(prefix).strip():
            case "DEALER":
                return Shoot(Role.DEALER)
            case "PLAYER":
                return Shoot(Role.PLAYER)
            case "ME" | "MYSELF" | "SELF":
                return Shoot(self._me)
            case "OPPONENT" | "OTHER":
                return Shoot(self._me.opponent)
            case target:
                return ParseFailure(f"Unknown target '{target}'")
