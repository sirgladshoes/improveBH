import requests, zipfile, io
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from replay_reader import read_replay_file
import database
from datetime import datetime
from time import time
import hashlib

import cProfile
import pstats

stats_url = "https://api.brawlhalla.com/v1/player/stats"
legends_url = "https://api.brawlhalla.com/v1/static/legends"

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
legend_lookup = {legend["legend_id"]: legend for legend in requests.get(legends_url,params={"max_results": 100}).json()["legends"]}

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
    )

@app.get("/playerData")
async def search(request:Request, bhid:str):

    data = get_general_player_data(int(bhid))
    if not database.has_player(int(bhid)):
        database.insert_tracked_player(int(bhid))
        database.insert_general_api_data(int(time()), data)

    data = get_general_player_data(int(bhid))

    return templates.TemplateResponse(
        request=request,
        name="playerData.html",
        context={"general":data, "legendLookup": legend_lookup}
    )

@app.post("/upload")
async def upload(file: UploadFile = File(...), playerName: str = ""):
    data = await file.read()
    results = {"wins": 0, "games": 0}

    #profiler = cProfile.Profile()
    #profiler.enable()

    with zipfile.ZipFile(io.BytesIO(data)) as zip_ref:
        for file in zip_ref.filelist:
            if not (not file.is_dir() and file.filename.endswith(".replay")):
                continue
            #print(file.filename, file.file_size, file.is_dir())
            file_bytes = zip_ref.read(file.filename)
            timestamp = int(datetime(*file.date_time).timestamp())
            replay_id = hashlib.sha256(file_bytes).hexdigest()
            try:
                replay_data = read_replay_file(file_bytes)

                database.insert_replay(55428652, replay_id, timestamp, replay_data)
            except:
                pass

            #print(replay_data["game_data"]["version"])
            #print(str(results["games"]) + "/12300", flush=True)

    #profiler.disable()
    #stats = pstats.Stats(profiler).sort_stats('cumulative')
    #stats.print_stats(20)
    database.commit()

    return {"message": "uploaded"}


def get_general_player_data(bhid:int):
    player_data_response = requests.get(
        stats_url,
        params={"brawlhalla_id": bhid}
    )

    player_data = {"brawlhalla_id":bhid, "name":"No Data", "wins":0, "games":0, "level":0, "legends":[], "weapons": []}

    response_data = player_data_response.json()

    for key in player_data.keys():
        if key == "legends":
            player_data[key] = generate_legend_data(response_data["legends"], legend_lookup)
        elif key == "weapons":
            player_data[key] = generate_weapon_data(response_data["legends"], legend_lookup)
        else:
            player_data[key] = response_data[key]


    game_time = 0
    for legend in player_data["legends"]:
        game_time += legend["match_time"]
    player_data["game_time"] = game_time

    return player_data


def generate_legend_data(data:list, lookup:dict) -> list:

    data.sort(key=lambda legend: legend.get("games", 0), reverse=True)


    result = []
    for legend in data:
        leg_id = legend["legend_id"]
        if leg_id in lookup.keys():
            #print(legend)
            result.append({"id":leg_id, "games":legend["games"], "wins":legend["wins"],
                "damage_dealt":legend["damage_dealt"], "damage_taken":legend["damage_taken"], 
                "kos":legend["damage_dealt"], "falls":legend["falls"], "match_time":legend["match_time"]
                           })

    return result


def generate_weapon_data(data:list, lookup:dict) -> list:
    empty_weapon_data = {"damage":0, "kos":0, "time_held":0, "games":0, "wins":0}

    result = {}

    result["Unarmed"] = empty_weapon_data.copy()
    for legend in data:
        if legend["legend_id"] in lookup:
            wep_one = lookup[legend["legend_id"]]["weapon_one"]
            wep_two = lookup[legend["legend_id"]]["weapon_two"]

            if not wep_one in result:
                result[wep_one] = empty_weapon_data.copy()
            if not wep_two in result:
                result[wep_two] = empty_weapon_data.copy()


    for legend in data:
        if legend["legend_id"] in lookup:
            wep_one = lookup[legend["legend_id"]]["weapon_one"]
            wep_two = lookup[legend["legend_id"]]["weapon_two"]

            result["Unarmed"]["damage"] += legend["damage_unarmed"]
            result[wep_one]["damage"] += legend["damage_weapon_one"]
            result[wep_two]["damage"] += legend["damage_weapon_two"]

            result["Unarmed"]["time_held"] += (legend["match_time"] - (legend["time_held_weapon_one"] + legend["time_held_weapon_two"]))
            result[wep_one]["time_held"] += legend["time_held_weapon_one"]
            result[wep_two]["time_held"] += legend["time_held_weapon_two"]

            result["Unarmed"]["kos"] += legend["ko_unarmed"]
            result[wep_one]["kos"] += legend["ko_weapon_one"]
            result[wep_two]["kos"] += legend["ko_weapon_two"]

            result["Unarmed"]["games"] += legend["games"]
            result[wep_one]["games"] += legend["games"]
            result[wep_two]["games"] += legend["games"]
 
            result["Unarmed"]["wins"] += legend["wins"]
            result[wep_one]["wins"] += legend["wins"]
            result[wep_two]["wins"] += legend["wins"]

    return [{"name":w, **result[w]} for w in result]


get_general_player_data(55428652)

player_data_response = requests.get(
    stats_url,
    params={"brawlhalla_id": 55428652}
)


print(player_data_response.json())