import click
import enum
import logging

from zerosumfc.buckshotroulette import Game
from zerosumfc.cliutils import AgentChoice, make_agent
from zerosumfc.data import Role

@click.command()
@click.argument("player_agent", type=AgentChoice)
@click.argument("dealer_agent", type=AgentChoice)
@click.option("--rounds", type=int, default=10)
@click.option("--health", type=int, default=5)
def main(player_agent, dealer_agent, rounds, health):
    player = make_agent(player_agent, Role.PLAYER)
    dealer = make_agent(dealer_agent, Role.DEALER)

    player_wins = 0
    dealer_wins = 0

    for i in range(rounds):
        game = Game(dealer=dealer, player=player, initial_health=health)
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
    logging.basicConfig(
        filename="battle.log", encoding="utf-8", level=logging.INFO
    )
    main()
