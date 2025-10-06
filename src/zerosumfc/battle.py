from datetime import datetime
import logging
import pathlib
import click

from zerosumfc.buckshotroulette import Game
from zerosumfc.cliutils import AgentChoice, getLoggingLevel, make_agent
from zerosumfc.data import Role


logger = logging.getLogger(__name__)


def print_and_log(msg: str):
    logger.info(msg)
    print(msg)


@click.command()
@click.argument("player_agent", type=AgentChoice)
@click.argument("dealer_agent", type=AgentChoice)
@click.option("--rounds", type=int, default=10)
@click.option("--health", type=int, default=5)
def main(player_agent, dealer_agent, rounds, health):
    player_name = player_agent.name
    dealer_name = dealer_agent.name

    timestamp = datetime.now().strftime("%Y.%m.%d-%H%M%S")

    log_dir = pathlib.Path("./logs")
    log_dir.mkdir(exist_ok=True)
    logfile = f"{player_name}_vs_{dealer_name}_{timestamp}.log"
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        filename=log_dir / logfile,
        encoding="utf-8",
        level=getLoggingLevel(logging.INFO),
    )
    print_and_log(
        f"Evaluating player: {player_agent} vs dealer: {dealer_agent}"
    )
    logger.info(f"{rounds} rounds with initial health {health}")
    player = make_agent(player_agent, Role.PLAYER)
    dealer = make_agent(dealer_agent, Role.DEALER)

    player_wins = 0
    dealer_wins = 0

    for i in range(rounds):
        game = Game(dealer=dealer, player=player, initial_health=health)
        print_and_log(f"Running game {i}")
        winner = game.run()
        print_and_log(f"Winner is {winner}")
        match winner:
            case Role.PLAYER:
                player_wins += 1
            case Role.DEALER:
                dealer_wins += 1

    logger.info(
        f"Evaluation finished. Player won {player_wins} rounds and "
        f"dealer won {dealer_wins} rounds"
    )
    print("Results:")
    print(f"Player: {player_wins}")
    print(f"Dealer: {dealer_wins}")


if __name__ == "__main__":
    main()
