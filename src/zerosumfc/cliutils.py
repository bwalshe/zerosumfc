import enum
import logging
import os
import click
import dotenv

from zerosumfc.data import Role
from zerosumfc.agents import BlasterAgent, RandomAgent
from zerosumfc.gptagent import GptAgent
from zerosumfc.minmaxagent import MinMaxAgent

dotenv.load_dotenv()


class AgentType(enum.Enum):
    RANDOM = enum.auto()
    MINMAX = enum.auto()
    BLASTER = enum.auto()
    GPT = enum.auto()


AgentChoice = click.Choice(AgentType, case_sensitive=False)


def getLoggingLevel(default_level: int) -> int:
    env_level = os.getenv("LOG_LEVEL")
    if env_level is None:
        return default_level
    return logging.getLevelNamesMapping()[env_level]


def make_agent(agent_type: AgentType, role: Role):
    match agent_type:
        case AgentType.RANDOM:
            return RandomAgent(role)
        case AgentType.MINMAX:
            return MinMaxAgent(role)
        case AgentType.BLASTER:
            return BlasterAgent(role)
        case AgentType.GPT:
            key_env_var = "OPENAI_KEY"
            api_key = os.getenv(key_env_var)
            if api_key is None:
                raise ValueError(
                    "Canot find OpenAI API key. "
                    f"Please set {key_env_var} the environment variable."
                )
            return GptAgent(api_key, role)
