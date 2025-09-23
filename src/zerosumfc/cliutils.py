import enum
import click

from zerosumfc.data import Role
from zerosumfc.agents import RandomAgent
from zerosumfc.minmaxagent import MinMaxAgent


class AgentType(enum.Enum):
    RANDOM = enum.auto()
    MINMAX = enum.auto()


AgentChoice = click.Choice(AgentType, case_sensitive=False)


def make_agent(agent_type: AgentType, role:Role):
    match agent_type:
        case AgentType.RANDOM:
            return RandomAgent(role)
        case AgentType.MINMAX:
            return MinMaxAgent(role)

