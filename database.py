import sqlite3
import json
import time

con = sqlite3.connect("data.db")
cur = con.cursor()

def create_table(table:str):
    cur.execute("CREATE TABLE " + table)

def check_tables():
    tables = cur.execute("SELECT name from sqlite_master")
    print(tables.fetchall())

def has_player(bhID:int)->bool:
    unformated_ids = cur.execute("SELECT bhID FROM trackedPlayers WHERE bhID="+str(bhID)).fetchall()
    ids = [n[0] for n in unformated_ids]
    return (bhID in ids)

def insert_tracked_player(bhID: int):
    cur.execute("INSERT INTO trackedPlayers VALUES ("+str(bhID)+")")
    con.commit()


def update_names(bhID:int, timestamp:int , name:str):
    unformated_names = cur.execute("SELECT name FROM playerNames WHERE bhID="+str(bhID)).fetchall()
    names = [n[0] for n in unformated_names]
    if not (name in names):
        cur.execute("INSERT INTO playerNames VALUES (?, ?, ?)", (bhID, timestamp, name))

def insert_replay(replay_id, timestamp, replay_data):
    player_data = replay_data["players"]
    is_online = replay_data["game_data"]["isOnline"]
    gamemode = replay_data["game_data"].get("playlistName", None)

    cur.execute("INSERT INTO replays VALUES (?, ?, ?, ?)", (replay_id, timestamp, bool(is_online), gamemode))

    for player in player_data:
        player_id = player_data[player].get("playerID", False)
        if player_id:
          update_names(player_id, timestamp, player)

        cur.execute("INSERT INTO replayPlayers VALUES (?, ?, ?, ?, ?)", 
            (replay_id, player, json.dumps(player_data[player]["legends"]), player_data[player].get("placement", None), player_data[player].get("deaths", None)))

def commit():
    con.commit()

def fetch_general_player_data(bhID:int):
    result = []
    data = cur.execute("SELECT * FROM playerSnapshots WHERE bhID="+str(bhID)+" ORDER BY timestamp DESC").fetchall()
    names = cur.execute("SELECT * FROM playerNames WHERE bhID="+str(bhID)+" ORDER BY timestamp DESC").fetchall()
    for p in data:
        subDic = {}
        subDic["bhID"] = p[0] 
        subDic["timestamp"] = p[1] 
        subDic["gameTime"] = p[2] 
        subDic["level"] = p[3] 
        subDic["games"] = p[4]
        subDic["wins"] = p[5]
        n = 0
        while n<len(names)-1 and names[n][1] > p[1]:
            n+=1
        subDic["name"] = names[n][2]
        result.append(subDic)

    return result

def fetch_legend_data(bhID:int):
    pass

def insert_general_api_data(timestamp, data:dict):
    print("whats goin on here")
    bhID = data["brawlhalla_id"]
    update_names(bhID, timestamp, data["name"])

    cur.execute("INSERT INTO playerSnapshots VALUES (?, ?, ?, ?, ?, ?)", (bhID, timestamp, data["game_time"], data["level"], data["games"], data["wins"]))
    for legend in data["legends"]:
        cur.execute("INSERT INTO legendSnapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            (bhID, timestamp, legend["id"], legend["games"], legend["wins"], legend["damage_dealt"], legend["damage_taken"], legend["kos"], legend["falls"], legend["match_time"]))
    for weapon in data["weapons"]:
        cur.execute("INSERT INTO weaponSnapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
            (bhID, timestamp, weapon["name"], weapon["games"], weapon["wins"], weapon["damage"], weapon["kos"], weapon["time_held"]))


    con.commit()

def insert_ranked_api_data(timestamp, data:dict):
    bhID = data["brawlhalla_id"]
    cur.execute("INSERT INTO rankedPlayerSnapshots VALUES (?, ?, ?, ?, ?, ?, ?)", 
                (bhID, timestamp, data["games"], data["wins"], data["rating"], data["tier"], data["global_rank"]))
    for legend in data["legends"]:
        cur.execute("INSERT INTO rankedLegendSnapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
            (bhID, timestamp, legend["legend_id"], legend["games"], legend["wins"], legend["rating"], legend["tier"]))
    con.commit()

def get_test():
    test = cur.execute("SELECT * FROM playerSnapshots WHERE bhID=55428652")
    print(test.fetchall())

def init_tables():
    create_table("trackedPlayers(bhID INTEGER UNIQUE)")

    create_table("replays(replayID TEXT UNIQUE, timestamp INTEGER, isOnline BOOLEAN, gameModeName TEXT)")
    create_table("replayPlayers(replayID TEXT, playerName TEXT, legends, wonGame BOOLEAN, deaths INTEGER)")
    create_table("playerNames(bhID INTEGER, timestamp INTEGER, name TEXT)")

    create_table("playerSnapshots(bhID INTEGER, timestamp INTEGER, gameTime INTEGER, level INTEGER, games INTEGER, wins INTEGER)")
    create_table("legendSnapshots(bhID INTEGER, timestamp INTEGER, legID INTEGER, games INTEGER, wins INTEGER, damageDealt INTEGER, damageTaken INTEGER, kos INTEGER, falls INTEGER, matchtime INTEGER)")
    create_table("weaponSnapshots(bhID INTEGER, timestamp INTEGER, weapon TEXT, games INTEGER, wins INTEGER, damageDealt INTEGER, kos INTEGER, timeHeld INTEGER)")

    create_table("rankedPlayerSnapshots(bhID INTEGER, timestamp INTEGER, games INTEGER, wins INTEGER, rating INTEGER, tier TEXT, globalRank INTEGER)")
    create_table("rankedLegendSnapshots(bhID INTEGER, timestamp INTEGER, legID INTEGER, games INTEGER, wins INTEGER, rating INTEGER, tier TEXT)")

#init_tables()

id = 55428652
#insert_general_api_data(id, 20, main.get_general_player_data(id))
#insert_replay(id, "hash_id", replay_reader.test_replay())
#get_test()
#test = cur.execute("SELECT * FROM replayPlayers")
#print(test.fetchall())
#test = cur.execute("SELECT * FROM playerNames")
#print(test.fetchall())
#get_test()
#con.close() 