import json

from rabona_python import RabonaClient
from lighthive.datastructures import Operation
from lighthive.client import Client
from datetime import datetime

# possible train types
# 433, 442, 352, 451, 4231, shot,dribbling, passing, defending,
# headball, speed, endurance.



from config import ACCOUNTS


def create_custom_json_op(username, auto_train_type, players):
    train_json = json.dumps(
         {
             "username": username,
             "type": "train",
             "command": {"tr_var1": auto_train_type, "tr_var2": players}}
    )

    train_op = Operation('custom_json', {
        'required_auths': [],
        'required_posting_auths': [username, ],
        'id': 'rabona',
        'json': train_json,
    })
    return train_op


def main():
    r = RabonaClient()
    for account in ACCOUNTS:
        # check if we can train, first.
        userinfo = r.userinfo(user=account["username"])
        if not userinfo.get("training_possible"):
            # training is not possible, wait.
            dt_delta = datetime.fromtimestamp(
                userinfo.get("training_busy_until")) - datetime.now()
            hours_left = int(dt_delta.total_seconds() / 3600)
            print("[%s] %d hours left for the training. Waiting." % (
                account["username"],
                hours_left
            ))
        else:
            players = r.team(user=account["username"]).get("players", [])
            print(f" > Found {len(players)} players.")

            # remove the players that can't play
            players = [p["uid"] for p in players if not (
                    p["games_injured"] > 0 or p["games_blocked"] > 0
                    or p["frozen"] > 0)]

            op = create_custom_json_op(
                account["username"], account["auto_train_type"], players)
            c = Client(keys=[account["posting_key"]])
            c.broadcast(op=op)
            print("[%s] [Training: %s] Done." % (
                account["username"], account["auto_train_type"]))


if __name__ == '__main__':
    main()
