import click
import enum

from zerosumfc.agents import RandomAgent
from zerosumfc.buckshotroulette import Game
from zerosumfc.data import Role
from zerosumfc.minmaxagent import MinMaxAgent


class AgentType(enum.Enum):
    RANDOM = enum.auto()
    MINMAX = enum.auto()


def make_agent(agent_type: AgentType, role:Role):
    match agent_type:
        case AgentType.RANDOM:
            return RandomAgent(role)
        case AgentType.MINMAX:
            return MinMaxAgent(role)

@click.command()
@click.argument("player_agent",
              type=click.Choice(AgentType, case_sensitive=False))
@click.argument("dealer_agent",
              type=click.Choice(AgentType, case_sensitive=False))
@click.option("--rounds", type=int, default=10)
def main(player_agent, dealer_agent, rounds):
    player = make_agent(player_agent, Role.PLAYER)
    dealer = make_agent(dealer_agent, Role.DEALER)

    player_wins = 0
    dealer_wins = 0

    for i in range(rounds):
        game = Game(dealer=dealer, player=player, initial_health=5)
        print(f"Running game {i}")
        winner = game.run()
        print(f"Winner is {winner}")
        match winner:
            case Role.PLAYER:
                player_wins += 1
            case Role.DEALER:
                dealer_wins += 1

    print("Results:")
    print(f"Player: {player_wins}")
    print(f"Dealer: {dealer_wins}")


if __name__ == "__main__":
    main()
