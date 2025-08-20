"""A text based Buckshot Roulette agent."""

from dataclasses import dataclass

from zerosumfc.agents import Agent, Feedback
from zerosumfc.data import (
    Action,
    GameState,
    Hit,
    Item,
    RelativeRole,
    Shoot,
    Use,
)


class TextAgent(Agent):
    """Prints game info to a stream and queries the user for their move."""

    def reset_shells(self, live: int, blank: int):
        """Print out the number of shells that have been loaded."""
        print(
            f"The gun has been loaded with {live} live rounds and {blank} blanks."
        )

    def get_move(self, state: GameState) -> Action:
        """Prompt the user for a move & parse their response."""
        self._print_state(state)
        while True:
            command = input("What do you want to do?\n")
            match parse_action(command):
                case ParseFailure(message):
                    print(f"Failed to parse command. {message}")
                case action:
                    return action

    def receive_feedback(self, feedback: Feedback | None):
        """Print out the feedback if it is not None."""
        match feedback:
            case Hit(RelativeRole.SELF):
                print("You shot yourself!")
            case Hit(RelativeRole.OPPONENT):
                print("You score a hit!")
            case None:
                print("Nothing happened")
            case _:
                print(feedback)
        print()

    def opponent_move(self, action: Action, result: Feedback | None) -> None:
        """Update the agent on its opponent's move and the result."""
        print("Your oponent ", end="")
        match action:
            case Use(item):
                print(f"used a {item.name.lower()}")
            case Shoot(target):
                target_name = (
                    "themself" if target == RelativeRole.SELF else "you"
                )
                print(f"aims at {target_name} and pulls the trigger.")
        match result:
            case Hit(RelativeRole.SELF):
                print("They shot themself!")
            case Hit(RelativeRole.OPPONENT):
                print("You've been shot!")
            case None:
                print("Nothing happens")
            case _:
                print(result)
        print()

    @classmethod
    def _print_state(cls, state: GameState):
        print(f"Your health: {state.personal_state.health}")
        print(f"Opponent's health: {state.opponent_state.health}")
        print("Your items:")
        cls._print_items(state.personal_state.items)
        print("Your opponent's items")
        cls._print_items(state.opponent_state.items)

    @staticmethod
    def _print_items(items: dict[Item, int]):
        items = {k: v for k, v in items.items() if v > 0}
        if len(items) == 0:
            print("Nothing.")
        else:
            for item, count in items.items():
                if count > 0:
                    print(f"{item.name} ({count})")


@dataclass
class ParseFailure:
    message: str


def parse_action(input: str) -> Action | ParseFailure:
    input = input.strip().upper()
    words = input.split()
    if len(words) != 2:
        return ParseFailure("Wrong number of words")

    action, subject = words

    match action:
        case "USE":
            return parse_item(subject)
        case "SHOOT":
            return parse_shoot(subject)
        case _:
            return ParseFailure(f"Unknown action '{action}'")


def parse_item(item_name: str) -> Use | ParseFailure:
    try:
        return Use(Item[item_name])
    except KeyError:
        return ParseFailure(f"Unknown item '{item_name}'")


def parse_shoot(target_name: str) -> Shoot | ParseFailure:
    try:
        return Shoot(RelativeRole[target_name])
    except KeyError:
        return ParseFailure(f"Unknown target '{target_name}'")


def test_parse_action():
    assert type(parse_action("shoot")) is ParseFailure
    assert type(parse_action("use glass again")) is ParseFailure
    assert parse_action("shoot oponent") == Shoot(RelativeRole.OPPONENT)
    assert parse_action("use glass") == Use(Item.GLASS)
