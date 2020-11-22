import pandas as pd
from rabona_python import RabonaClient

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


def get_players(username):
    # https://api.rabona.io/team?user=emrebeyler
    rabona_client = RabonaClient()
    players = rabona_client.team(user=username)
    return players


def normalize_players(players):
    normalized_players = []
    for player in players:
        # human readable type
        player["position"] = PLAYER_TYPE_MAP.get(player["type"])
        player["OS"] = player["overall_strength"]
        player["GK"] = player["goalkeeping"]
        player["TP"] = player["teamplayer"]
        # not needed
        del player["type"]
        del player["ask_id"]
        del player["teamplayer"]
        del player["goalkeeping"]

        normalized_players.append(player)

    return normalized_players


def main(username):
    players = normalize_players(get_players(username)["players"])

    df = pd.DataFrame(players, columns=[
        "uid",
        "name",
        "position",
        "age",
        "OS",
        "GK",
        "defending",
        "passing",
        "dribbling",
        "shot",
        "headball",
        "form",
        "speed",
        "cleverness",
        "TP",
        "endurance",
        "vulnerability",
        "no_yellow_cards",
        "salary",
        "games_blocked",
        "games_injured",
        "for_sale",
        "frozen",
    ])

    print(df)

    df.to_excel(f"players_{username}.xlsx", header=True)

main("emrebeyler")