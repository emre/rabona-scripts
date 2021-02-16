import json
import logging

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


def create_custom_json_op(username, pid, heal=True):
    if heal:
        custom_json_type = "heal_for_RBN"
    else:
        custom_json_type = "unblock_for_RBN"
    train_json = json.dumps(
        {
            "username": username,
            "type": custom_json_type,
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


def auto_heal_and_unblock(team, pk):
    rbn_balance = r.userinfo(user=team).get("currency")
    logger.info("Checking \"%s\" for injured and blocked players.", team)
    players = r.team(user=team).get("players", [])
    # players[0]["games_blocked"] = 1

    injured_players = [p for p in players if int(p["games_injured"]) > 0]
    blocked_players = [p for p in players if int(p["games_blocked"]) > 0]

    if not injured_players and not blocked_players:
        logger.info(
            "\t\"%s\" doesnt have any injured or blocked players. Skipping.",
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

        max_unblock_games = round(rbn_balance) / 10000
        for p in blocked_players:
            logger.info(
                "\t%s (%s) is blocked for %s matches. Trying to unblock." % (
                    p["name"], p["uid"], p["games_blocked"]
                ))

            if p["games_blocked"] <= max_unblock_games:
                op = create_custom_json_op(team, p["uid"], heal=False)
                c = Client(keys=[pk, ])
                c.broadcast(op=op)
                logger.info("\t Transaction is broadcasted. Enjoy.")
                max_heal_games -= p["games_injured"] * 10000
            else:
                logger.info(
                    "\tNot enough RBN to unblock %s (%s) for %s matches.",
                    p["name"], p["uid"], p["games_blocked"]
                )


def main():
    for team in ACCOUNTS:
        auto_heal_and_unblock(team["username"], team["posting_key"])


main()
