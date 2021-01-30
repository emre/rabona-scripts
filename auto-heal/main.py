import logging
import json
from lighthive.client import Client
from lighthive.datastructures import Operation

from rabona_python import RabonaClient

from config import ACCOUNTS

logger = logging.getLogger("Auto heal")
logger.setLevel(logging.DEBUG)
logFormatter = logging.Formatter(
    '%(asctime)s %(name)s %(levelname)s: %(message)s')
consoleHandler = logging.StreamHandler()
fileHandler = logging.FileHandler("autoheal.log")
consoleHandler.setFormatter(logFormatter)
fileHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)
logger.addHandler(fileHandler)

r = RabonaClient()


def create_custom_json_op(username, pid):
    train_json = json.dumps(
         {
             "username": username,
             "type": "heal_for_RBN",
             "command": {"tr_var1": pid}
         }
    )

    train_op = Operation('custom_json', {
        'required_auths': [],
        'required_posting_auths': [username, ],
        'id': 'rabona',
        'json': train_json,
    })
    return train_op


def auto_heal(team, pk):

    rbn_balance = r.userinfo(user=team).get("currency")
    logger.info("Checking \"%s\" for injured players.", team)
    players = r.team(user=team).get("players", [])
    injured_players = [p for p in players if int(p["games_injured"]) > 0]

    if not injured_players:
        logger.info(
            "\t\"%s\" doesnt have any injured players. Skipping.",
            team,
        )
        return
    else:
        logger.info("\tAvailable RBN: %s", round(rbn_balance))
        max_heal_games = round(rbn_balance) / 10000
        for p in injured_players:
            logger.info(
                "\t%s (%s) is injured for %s matches. Trying to heal." % (
                    p["name"], p["uid"], p["games_injured"]
                ))

            if p["games_injured"] <= max_heal_games:
                op = create_custom_json_op(team, p["uid"])
                c = Client(keys=[pk, ])
                c.broadcast(op=op)
                logger.info("\t Transaction is broadcasted. Enjoy.")
                max_heal_games -= p["games_injured"] * 10000
            else:
                logger.info(
                    "\tNot enough RBN to heal %s (%s) for %s matches.",
                    p["name"], p["uid"], p["games_injured"]
                )


def main():
    for team in ACCOUNTS:
        auto_heal(team["username"], team["posting_key"])


main()