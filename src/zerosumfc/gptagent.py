import enum
import logging
import uuid
from openai import OpenAI
from openai.types.responses import ResponseInputParam
import pydantic

from zerosumfc.agents import Agent
from zerosumfc.data import Action, Feedback, GameState, Item, Role, Shoot, Use
from zerosumfc.textagent import (
    render_feedback,
    render_opponent_move,
    render_reload,
    render_state,
)


logger = logging.getLogger(__name__)

RULES = """You are going to play a game called Buckshot Roulette.

This is a turn-based Russian-roulette-style duel played with a 12-gauge shotgun
where two participants (the Player and the Dealer) face off against each other.

Each round the gun is loaded with a random number of blank and live shells, in
a random order, and the participants are given a {items} random items which
can help them.

The players take turns where they can either use an item, shoot themself or
shoot their opponent.

If they choose to shoot, then the target will take damage if the shell is live.

Usually live shells do 1 unit of damage, but items can change this.

If the shell is blank, then the target takes no damage.

Shooting their opponent or shooting a live shell will end the current
participant's turn and allow their opponent to act.

Using an item or shooting themself with a blank shell does not end the current
participant's turn and they can continue to take actions.

When the shotgun becomes empty, the round ends, the shotgun will be reloaded
with more random shells, and the players will be given 3 more random items,
up to a maximum of 8. It will also reset to being the Player's turn.

Your goal is to reduce your opponent's health to 0

The items that will become available are:
GLASS: This allows you to see what the currently chambered shell is
CIGARETTES: This will restore one unit of health, up to a maximum of {health}
BEER: This will eject the currently chambered shell
HANDSAW: This will cause the next shell to do 2 units of damage if it is live.
HANDCUFFS: This will cause your opponent to skip their next turn.

You are acting as the Player, the user is acting as the Dealer.

The user will describe the status of the game and any actions they take and
when it is time for you to make a move, they will ask you the question "What do
you want to do?"

You must respond with one of
 * Shoot self
 * Shoot opponent
 * Use glass
 * Use cigarettes
 * Use beer
 * Use handsaw
 * Use handcuffs

Do not respond with anything else.
"""


class GptAction(enum.Enum):
    SHOOT_SELF = enum.auto()
    SHOOT_OPPONENT = enum.auto()
    USE_GLASS = enum.auto()
    USE_CIGARETTES = enum.auto()
    USE_BEER = enum.auto()
    USE_HANDSAW = enum.auto()
    USE_HANDCUFFS = enum.auto()


class GptResponse(pydantic.BaseModel):
    action: GptAction


class GptAgent(Agent):
    COMMAND = "What do you want to do?"
    GPT_VERSION = "gpt-5"
    EFFORT = "high"

    def __init__(
        self, api_key: str, role: Role, max_health: int = 5, item_count=3
    ):
        if role == Role.DEALER:
            raise NotImplementedError(
                "GptAgent is not currently inteneded to act as the dealer"
            )
        super().__init__(role)
        self._client: OpenAI = OpenAI(api_key=api_key)
        self._rules = RULES.format(health=max_health, items=item_count)
        self.reset()
        logger.info(
            "%s initialised with system prompt: %s",
            type(self).__name__,
            self._rules,
        )
        logger.info("GPT Model: %s", self.GPT_VERSION)
        logger.info("Effort: %s", self.EFFORT)

    def reset(self):
        self._unsent_messages: ResponseInputParam = [
            {"role": "developer", "content": self._rules}
        ]
        self._previous_response_id = None

    def delete(self):
        raise NotImplementedError

    def get_move(self, state: GameState) -> Action:
        request = render_state(self._role, state) + "\n" + self.COMMAND
        self._add_event(request)
        response = self._get_response()
        logger.info("API usage: %s", response.usage)

        match response.output_parsed:
            case None:
                raise Exception(response.error)
            case action:
                return self._translate_action(action)

    def receive_feedback(self, feedback: Feedback):
        self._add_event(render_feedback(self.role, feedback))

    def opponent_move(self, action: Action, feedback: Feedback):
        self._add_event(render_opponent_move(self.role, action, feedback))

    def reset_shells(self, live: int, blank: int):
        self._add_event(render_reload(live, blank))

    def _add_event(self, event: str):
        self._unsent_messages.append({"role": "developer", "content": event})

    def _get_response(self):
        response = self._client.responses.parse(
            model=self.GPT_VERSION,
            reasoning={"effort": self.EFFORT},
            input=self._unsent_messages,
            text_format=GptResponse,
            previous_response_id=self._previous_response_id
        )
        self._previous_response_id = response.id
        self._unsent_messages = list()
        return response

    def _translate_action(self, response: GptResponse) -> Action:
        match response.action:
            case GptAction.SHOOT_SELF:
                return Shoot(self.role)
            case GptAction.SHOOT_OPPONENT:
                return Shoot(self.role.opponent)
            case GptAction.USE_BEER:
                return Use(Item.BEER)
            case GptAction.USE_CIGARETTES:
                return Use(Item.CIGARETTES)
            case GptAction.USE_GLASS:
                return Use(Item.GLASS)
            case GptAction.USE_HANDCUFFS:
                return Use(Item.HANDCUFFS)
            case GptAction.USE_HANDSAW:
                return Use(Item.SAW)
