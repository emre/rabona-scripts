# -*- coding: UTF-8 -*-

import json
import datetime
from rabona_python import RabonaClient
from lighthive.datastructures import Operation
from lighthive.client import Client
from datetime import datetime
from collections import OrderedDict

from config import ACCOUNTS

# possible train types
# 433, 442, 352, 451, 4231, shot,dribbling, passing, defending,
# headball, speed, endurance.


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
        PLAYER_TYPE_DEFENDER: ["p5", "p4", "p3", "p2", "p6", "p8"],
        PLAYER_TYPE_MIDFIELDER: ["p11", "p10", "p7"],
        PLAYER_TYPE_ATTACKER: ["p9"],
    },
    "442": {
        PLAYER_TYPE_GOAL_KEEPER: ["p1"],
        PLAYER_TYPE_DEFENDER: ["p5", "p4", "p3", "p2", "p6"],
        PLAYER_TYPE_MIDFIELDER: ["p7", "p8", "p10",],
        PLAYER_TYPE_ATTACKER: ["p11", "p9"],
    }
    # todo add other tactics
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


def get_available_players(r, username, selected_formation):
    players = r.team(user=username).get("players", [])
    print(f" > Found {len(players)} players.")

    # remove the players that can't play
    players = [p for p in players if not (
            p["games_injured"] > 0 or p["games_blocked"] > 0
            or p["frozen"] > 0)]

    # sort by OS + TP
    players_with_custom_stat = []
    for p in players:
        p.update({
            "custom_stat": (p["overall_strength"] * 0.50) +
                           (p["teamplayer"] * 0.25) +
                           (p[selected_formation] * 0.15) +
                           (p["speed"] * 0.05) +
                           (p["endurance"] * 0.05)
        })
        players_with_custom_stat.append(p)

    players = sorted(players_with_custom_stat, key=lambda x: x["custom_stat"])
    return players


def get_formation(r, user, match_id):
    lineup = r.lineup(user=user, match_id=match_id)
    if isinstance(lineup, list):
        return None
    return lineup.get("formation")


def prepare_formation(tactic, players):
    formation = []
    subs = []
    for player_type, player_numbers in LOOKUP_PER_TACTIC[tactic].items():
        target_group = [p for p in players if p["type"] == player_type]
        for player_number in player_numbers:
            try:
                picked_player = target_group.pop()
            
                print(f" >> Picked {picked_player['name']} as"
                  f" {PLAYER_TYPE_MAP[player_type]}. OS: "
                  f"{picked_player['overall_strength']}")
            except Exception as e:
                pass
            formation.append((player_number, picked_player["uid"]))

        subs += target_group

    formation = sorted(formation, key=lambda x: int(x[0].replace("p", "")))
    # fill the subs
    # get the sub gk first
    gk = [s for s in subs if s["type"] == PLAYER_TYPE_GOAL_KEEPER]
    defender_subs = [s for s in subs if s["type"] == PLAYER_TYPE_DEFENDER]
    midfielder_subs = [s for s in subs if s["type"] == PLAYER_TYPE_MIDFIELDER]
    attacker_subs = [s for s in subs if s["type"] == PLAYER_TYPE_ATTACKER]

    sub_list = []
    for positioned_subs in [gk, defender_subs, midfielder_subs, attacker_subs]:
        added_sub_per_position = 0
        for positioned_sub in positioned_subs:
            try:
                if added_sub_per_position > 1:
                    continue
                sub_list.append(positioned_sub)
                picked_player = positioned_sub
                try:
                    print(f" >> Picked Sub {picked_player['name']} as "
                      f"{PLAYER_TYPE_MAP[picked_player['type']]} OS: "
                      f"{picked_player['overall_strength']}")
                except Exception as e:
                    pass
                added_sub_per_position += 1
                if picked_player["type"] == PLAYER_TYPE_GOAL_KEEPER:
                    added_sub_per_position = 42
            except IndexError:
                continue

    sub_list.reverse()
    for i in range(12, 22):
        try:
            formation.append((f"p{i}", sub_list.pop()["uid"]))
        except IndexError:
            pass

    formation = OrderedDict(formation)
    return formation


def main():
    import logging
    r = RabonaClient(loglevel=logging.ERROR)
    for account in ACCOUNTS:
        print(f" > Analyzing next match for @{account['username']}.")
        next_match = get_next_match(r, account["username"])
        print(f" > Next match is {next_match['club_1']} "
              f"vs {next_match['club_2']}.")

        opponent_user = next_match["team_user_2"]
        if next_match["team_user_2"] == account["username"]:
            opponent_user = next_match["team_user_1"]

        formation_of_opponent = get_formation(
            r, opponent_user, next_match["match_id"]) or "433 default"
        print(f" > Opponent is @{opponent_user}.")
        if formation_of_opponent:
            print(f" > Opponent will play {formation_of_opponent}.")
        formation_of_us = get_formation(
            r, account["username"], next_match["match_id"]
        )
        if formation_of_us and str(formation_of_us) == account["formation"]:
            print(f" > Formation is already set for this match: "
                  f"{formation_of_us}.")
        else:
            # we need to set formation for that
            players = get_available_players(
                r, account["username"], account["formation"])
            formation = prepare_formation(account["formation"], players)

            op = create_custom_json_op(
                account["username"],
                next_match["match_id"],
                account["formation"],
                formation,
            )

            c = Client(keys=[account["posting_key"]], nodes=["https://hived.emre.sh"])
            c.broadcast(op=op)
            print(f" >>> Formation: {account['formation']} is set"
                  f" for {account['username']}.")
        print(f" > All operations are completed for {account['username']}.")
        print("=" * 64)


if __name__ == '__main__':
    main()
