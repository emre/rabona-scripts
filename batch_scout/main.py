import argparse
import json
import time

from lighthive.client import Client
from lighthive.datastructures import Operation
from rabona_python import RabonaClient

rabona_client = RabonaClient()

PLAYER_TYPE_GOAL_KEEPER = "1"
PLAYER_TYPE_DEFENDER = "2"
PLAYER_TYPE_MIDFIELDER = "3"
PLAYER_TYPE_ATTACKER = "4"

PLAYER_TYPE_MAP = {
    PLAYER_TYPE_GOAL_KEEPER: "goal keeper",
    PLAYER_TYPE_DEFENDER: "defender",
    PLAYER_TYPE_MIDFIELDER: "midfielder",
    PLAYER_TYPE_ATTACKER: "attacker",
}


def create_custom_json_op(username):
    scout_json = json.dumps(
        {
            "username": username,
            "type": "scout_players",
            "command": {"tr_var1": username}
        }
    )

    train_op = Operation('custom_json', {
        'required_auths': [],
        'required_posting_auths': [username, ],
        'id': 'rabona',
        'json': scout_json,
    })
    return train_op


def get_signable_player(trx_id):
    signable_players = rabona_client.signable_player(trx=trx_id)
    if not signable_players.get("players", []):
        time.sleep(3)
        return get_signable_player(trx_id)

    return signable_players.get("players")[0]


def scout(total, username, pkey):
    lighthive_client = Client(keys=[pkey, ])
    print('> Will scout %s players for %s.' % (total, username))
    for i in range(total):
        op = create_custom_json_op(username)
        trx_id = lighthive_client.broadcast_sync(op).get("id")
        time.sleep(3)
        signable_player = get_signable_player(trx_id)
        if signable_player.get("overall_strength") > 60:
            print("> Scouted: %s. Type: %s, OS: %s, TP: %s" % (
                signable_player.get("name"),
                PLAYER_TYPE_MAP.get(signable_player.get("type")),
                signable_player.get("overall_strength"),
                signable_player.get("teamplayer"),
            ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch scout tool')
    parser.add_argument('username', metavar='U', type=str,
                        help='Your team\'s username')
    parser.add_argument('count', metavar='N', type=int,
                        help='How many players do you want to scout?')
    parser.add_argument('posting_key', metavar='P', type=str,
                        help='Private posting key')
    args = parser.parse_args()
    scout(args.count, args.username, args.posting_key)
