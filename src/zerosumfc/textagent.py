"""A text based Buckshot Roulette agent."""

from dataclasses import dataclass

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
    Used,
)


class TextAgent(Agent):
    """Prints game info to a stream and queries the user for their move."""

    def __init__(self, role: Role):
        """Initialise the agent for the given role."""
        super().__init__(role)
        self._parser = ActionParser(role)

    def reset_shells(self, live: int, blank: int):
        """Print out the number of shells that have been loaded."""
        print(render_reload(live, blank))

    def get_move(self, state: GameState) -> Action:
        """Prompt the user for a move & parse their response."""
        print(render_state(self.role, state))
        while True:
            command = input("What do you want to do?\n")
            match self._parser(command):
                case ParseFailure(message):
                    print(f"Failed to parse command. {message}")
                case action:
                    return action

    def receive_feedback(self, feedback: Feedback | None):
        """Print out the feedback if it is not None."""
        print(render_feedback(self.role, feedback))

    def opponent_move(self, action: Action, result: Feedback | None) -> None:
        """Update the agent on its opponent's move and the result."""
        print(render_opponent_move(self.role, action, result))


def render_reload(live: int, blank: int):
    return (
        f"The gun has been loaded with {live} live rounds and {blank} blanks."
    )


def render_feedback(me: Role, feedback: Feedback | None) -> str:
    match feedback:
        case Hit(target):
            if target == me:
                return "You shot yourself!"
            else:
                return "You score a hit!"
        case Miss():
            return "You pull the trigger... it's a blank!."
        case Used(item):
            return f"You used the {item.name.lower()}"
        case Heal(amount):
            return f"You healed {amount} point(s)"
        case See(shell):
            return f"You see a {shell.name} shell"
        case _:
            return "You can't do that."


def render_opponent_move(
    me: Role, action: Action, result: Feedback | None
) -> str:
    output = "Your oponent "
    match action:
        case Use(item):
            output += f"used a {item.name.lower()}.\n"
        case Shoot(target):
            target_name = "you" if target == me else "themself"
            output += f"aims at {target_name} and pulls the trigger.\n"
    match result:
        case Hit(target):
            if target == me:
                output += "You've been shot!"
            else:
                output += "They shot themself!"
        case Miss():
            output += "It was a blank."
        case None:
            output += "Nothing happens"
        case _:
            output += str(result)
    return output


def render_state(me: Role, state: GameState) -> str:
    def render_items(state: PlayerState) -> str:
        if state.total_items == 0:
            return "Nothing."
        else:
            lines = [
                f"{item.name} ({count})"
                for item, count in state.items()
                if count > 0
            ]
            return "\n".join(lines)

    personal_state = state[me]
    opponent_state = state[me.opponent]
    output = [f"Your health: {personal_state.health}"]
    output.append(f"Opponent's health: {opponent_state.health}")
    output.append("Your items:")
    output.append(render_items(personal_state))
    output.append("Your opponent's items")
    output.append(render_items(opponent_state))
    return "\n".join(output)


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
