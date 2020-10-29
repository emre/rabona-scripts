import json
import datetime
from rabona_python import RabonaClient
from lighthive.datastructures import Operation
from lighthive.client import Client
from datetime import datetime
from collections import OrderedDict

# possible train types
# 433, 442, 352, 451, 4231, shot,dribbling, passing, defending,
# headball, speed, endurance.


ACCOUNTS = [
    {
        "username": "emrebeyler",
        "formation": "433",
        "posting_key": "<posting_key>"
    },
    {
        "username": "klopp",
        "formation": "4231",
        "posting_key": "<posting_key>"
    }
]

PLAYER_TYPE_GOAL_KEEPER = "1"
PLAYER_TYPE_DEFENDER = "2"
PLAYER_TYPE_MIDFIELDER = "3"
PLAYER_TYPE_ATTACKER = "4"

LOOKUP_PER_TACTIC = {
    "451": {
        PLAYER_TYPE_GOAL_KEEPER: ["p1"],
        PLAYER_TYPE_DEFENDER: ["p2", "p4", "p5", "p3"],
        PLAYER_TYPE_MIDFIELDER: ["p7", "p8", "p6", "p10", "p11"],
        PLAYER_TYPE_ATTACKER: ["p9"],
    },
    "433": {
        PLAYER_TYPE_GOAL_KEEPER: ["p1"],
        PLAYER_TYPE_DEFENDER: ["p2", "p4", "p5", "p3"],
        PLAYER_TYPE_MIDFIELDER: ["p8", "p6", "p10"],
        PLAYER_TYPE_ATTACKER: ["p7", "p9", "p11"],
    },
    "4231": {
        PLAYER_TYPE_GOAL_KEEPER: ["p1"],
        PLAYER_TYPE_DEFENDER: ["p5", "p4", "p3", "p2"],
        PLAYER_TYPE_MIDFIELDER: ["p8", "p6", "p11", "p10", "p7"],
        PLAYER_TYPE_ATTACKER: ["9"],
    }
}

PLAYER_TYPE_MAP = {
    PLAYER_TYPE_GOAL_KEEPER: "goal keeper",
    PLAYER_TYPE_DEFENDER: "defender",
    PLAYER_TYPE_MIDFIELDER: "midfielder",
    PLAYER_TYPE_ATTACKER: "attacker",
}


def create_custom_json_op(username, match_id, formation_type, formation):
    formation_json = json.dumps(
         {
             "username": username,
             "type": "set_formation",
             "command": {
                 "tr_var1": str(match_id),
                 "tr_var2": formation_type,
                 "tr_var3": formation,
             }}
    )

    train_op = Operation('custom_json', {
        'required_auths': [],
        'required_posting_auths': [username, ],
        'id': 'rabona',
        'json': formation_json,
    })
    return train_op


def get_next_match(r, username):
    now_as_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    resp = r.matches(user=username, start_date=now_as_str, limit=1)
    return resp.get("matches", [])[0]


def get_available_players(r, username):
    players = r.team(user=username).get("players", [])
    print(f" > Found {len(players)} players.")

    # remove the players that can't play
    players = [p for p in players if not (
            p["games_injured"] > 0 or p["games_blocked"] > 0
            or p["frozen"] > 0)]

    # sort by OS
    players = sorted(players, key=lambda x: x["overall_strength"])
    return players


def prepare_formation(tactic, players):
    formation = []
    subs = []
    for player_type, player_numbers in LOOKUP_PER_TACTIC[tactic].items():
        target_group = [p for p in players if p["type"] == player_type]
        for player_number in player_numbers:
            picked_player = target_group.pop()
            print(f" >> Picked {picked_player['name']} as"
                  f" {PLAYER_TYPE_MAP[player_type]}. OS: "
                  f"{picked_player['overall_strength']}")
            formation.append((player_number, picked_player["uid"]))

        subs += target_group

    formation = sorted(formation, key=lambda x: int(x[0].replace("p", "")))
    # fill the subs
    # get the sub gk first
    gk = [s for s in subs if s["type"] == PLAYER_TYPE_GOAL_KEEPER][0]
    formation.append(("p12", gk["uid"]))
    for i in range(13, 22):
        try:
            formation.append((f"p{i}", subs.pop()["uid"]))
        except IndexError:
            pass

    formation = OrderedDict(formation)
    print(formation)
    return formation


def main():
    import logging
    r = RabonaClient(loglevel=logging.ERROR)
    for account in ACCOUNTS:
        next_match = get_next_match(r, account["username"])
        print(f" > Next match is {next_match['club_1']} "
              f"vs {next_match['club_2']}")

        # check if there is a line-up already?
        lineup_key = 'lineup1'
        if next_match["team_user_2"] == account["username"]:
            lineup_key = 'lineup2'
        if next_match[lineup_key] == 0:
            # we need to set formation for that
            print(" > No formation is saved for that match. Let's build one.")
            players = get_available_players(r, account["username"])
            formation = prepare_formation(account["formation"], players)

            op = create_custom_json_op(
                account["username"],
                next_match["match_id"],
                account["formation"],
                formation,
            )

            c = Client(keys=[account["posting_key"]])
            c.broadcast(op=op)
            print(f" >>> Formation: {account['formation']} is set"
                  f" for {account['username']}.")
        else:
            print(" > Line up is already decided. Good luck!")


if __name__ == '__main__':
    main()