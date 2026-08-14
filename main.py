import requests
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

stats_url = "https://api.brawlhalla.com/v1/player/stats"
legends_url = "https://api.brawlhalla.com/v1/static/legends"


app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
    )

@app.get("/playerData-all")
def search(request:Request, bhid:str):
    return templates.TemplateResponse(
        request=request,
        name="playerData.html",
        context={"data":generate_player_data(bhid, "all")}
    )

@app.get("/playerData-1v1")
def display1v1(request:Request, bhid:int):
    return templates.TemplateResponse(
        request=request,
        name="playerData.html",
        context={"data":generate_player_data(bhid, "ranked_1v1")}
    )

@app.get("/playerData-3v3")
def search(request:Request, bhid:str):
    return templates.TemplateResponse(
        request=request,
        name="playerData.html",
        context={"data":generate_player_data(bhid, "ranked_3v3")}
    )


def generate_player_data(bhid:int, mode:str):
    response = requests.get(
        stats_url,
        params={"brawlhalla_id": bhid, "mode": mode}
    )

    data = {"name":"No Data", "wins":0, "games":0, "legends":[]}

   # try:
    response_data = response.json()

    for key in data.keys():
        data[key] = response_data[key]
        if key == "legends":
            data[key] = generate_legend_data(response_data[key])
            
    #except Exception as e:
    #    print("help", e)

    return data

def generate_legend_data(data:list) -> list:

    response = requests.get(legends_url,params={"max_results": 100})
    legend_data = response.json()["legends"]
    legend_lookup = {legend["legend_id"]: legend for legend in legend_data}

    result = []
    for legend in data:
        leg_id = legend["legend_id"]
        if leg_id in legend_lookup.keys():
            result.append({legend_lookup[leg_id]["legend_name"]:legend.get("level", "Unknown")})
        
    return result


generate_player_data(55428652, "all")