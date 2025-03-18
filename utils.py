import requests
import streamlit as st
from datetime import datetime, timedelta
import time
import numpy as np

# API Configuration
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
EVENT_ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"

# Cache for API calls to minimize requests
CACHE = {}
CACHE_EXPIRATION = timedelta(minutes=15)

def get_nba_games():
    """Fetch NBA games for today from Balldontlie API, with caching."""
    today = datetime.today().strftime("%Y-%m-%d")
    if "games" in CACHE and time.time() - CACHE["games"]["timestamp"] < CACHE_EXPIRATION.total_seconds():
        return CACHE["games"]["data"]

    try:
        url = f"{BALL_DONT_LIE_API_URL}/games"
        headers = {"Authorization": st.secrets["balldontlie_api_key"]}
        params = {"dates[]": today}

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return []

        games_data = response.json().get("data", [])
        formatted_games = [
            {
                "home_team": game["home_team"]["full_name"],
                "away_team": game["visitor_team"]["full_name"],
                "game_id": game["id"],
                "date": game["date"]
            }
            for game in games_data
        ]
        CACHE["games"] = {"data": formatted_games, "timestamp": time.time()}
        return formatted_games
    except Exception:
        return []

def get_event_id(selected_game):
    """Retrieve the event ID for a given NBA game with caching."""
    if "event_id" in CACHE and selected_game["game_id"] in CACHE["event_id"]:
        return CACHE["event_id"][selected_game["game_id"]]

    try:
        response = requests.get(
            ODDS_API_URL,
            params={
                "apiKey": st.secrets["odds_api_key"],
                "regions": "us",
                "markets": "h2h",
                "bookmakers": "fanduel",
            }
        )
        if response.status_code != 200:
            return None

        events_data = response.json()
        for event in events_data:
            if event["home_team"] == selected_game["home_team"] and event["away_team"] == selected_game["away_team"]:
                CACHE.setdefault("event_id", {})[selected_game["game_id"]] = event["id"]
                return event["id"]
        return None
    except Exception:
        return None

def calculate_parlay_odds(selected_props):
    """Calculate combined odds for the SGP based on individual prop odds."""
    combined_odds = 1.0
    for prop in selected_props:
        odds = prop["odds"]
        decimal_odds = (1 + (odds / 100)) if odds > 0 else (1 + (100 / abs(odds)))
        combined_odds *= decimal_odds

    final_american_odds = int((combined_odds - 1) * 100) if combined_odds > 2 else int(-100 / (combined_odds - 1))
    return final_american_odds

def get_risk_level(odds):
    """Assign risk level and emoji based on betting odds."""
    if -450 <= odds <= -300:
        return "Very Safe", "🔵"
    elif -299 <= odds <= -200:
        return "Safe", "🟢"
    elif -199 <= odds <= 100:
        return "Moderate Risk", "🟡"
    elif 101 <= odds <= 250:
        return "High Risk", "🟠"
    else:
        return "Very High Risk", "🔴"

def fetch_sgp_builder(selected_game, num_props=1, min_odds=None, max_odds=None, confidence_level=None):
    """Fetch player props for Same Game Parlay (SGP) with caching and optimized requests."""
    if not selected_game or "game_id" not in selected_game:
        return {}

    event_id = get_event_id(selected_game)
    if not event_id:
        return {}

    cache_key = f"props_{event_id}"
    if cache_key in CACHE and time.time() - CACHE[cache_key]["timestamp"] < CACHE_EXPIRATION.total_seconds():
        return CACHE[cache_key]["data"]

    try:
        markets = [
            "player_points", "player_rebounds", "player_assists", "player_threes",
            "player_points_alternate", "player_rebounds_alternate", "player_assists_alternate", "player_threes_alternate",
            "player_points_rebounds", "player_points_assists", "player_rebounds_assists", "player_points_rebounds_assists",
            "player_points_rebounds_alternate", "player_points_assists_alternate", "player_rebounds_assists_alternate",
            "player_points_rebounds_assists_alternate"
        ]

        api_url = EVENT_ODDS_API_URL.format(event_id=event_id)
        params = {
            "apiKey": st.secrets["odds_api_key"],
            "regions": "us",
            "markets": ",".join(markets),
            "bookmakers": "fanduel"
        }
        response = requests.get(api_url, params=params)

        if response.status_code != 200:
            return {}

        odds_data = response.json()
        fanduel = next((b for b in odds_data.get("bookmakers", []) if b["key"] == "fanduel"), None)
        if not fanduel or not fanduel.get("markets"):
            return {}

        selected_props = []
        all_props = []
        for market in fanduel["markets"]:
            for outcome in market.get("outcomes", []):
                odds = outcome["price"]
                implied_prob = 1 / (1 + abs(odds) / 100) if odds < 0 else odds / (100 + odds)
                ai_prob = implied_prob * 0.9
                confidence_boost = round(ai_prob * 100, 2)
                betting_edge = round(ai_prob - implied_prob, 3)
                risk_level, emoji = get_risk_level(odds)

                prop_data = {
                    "player": outcome["name"],
                    "prop": market["key"].replace("_alternate", "").replace("player_", "").title(),
                    "odds": odds,
                    "implied_prob": round(implied_prob, 3),
                    "ai_prob": round(ai_prob, 3),
                    "confidence_boost": confidence_boost,
                    "betting_edge": betting_edge,
                    "risk_level": f"{emoji} {risk_level}",
                    "alt_line": "alternate" in market["key"]
                }
                all_props.append(prop_data)

        all_props = sorted(all_props, key=lambda x: x["confidence_boost"], reverse=True)

        if min_odds is not None and max_odds is not None:
            all_props = [p for p in all_props if min_odds <= p["odds"] <= max_odds]

        if confidence_level:
            all_props = [p for p in all_props if confidence_level[0] <= p["confidence_boost"] <= confidence_level[1]]

        selected_props = all_props[:num_props]

        if not selected_props:
            return {}

        combined_odds = calculate_parlay_odds(selected_props)

        CACHE[cache_key] = {"data": {"selected_props": selected_props, "combined_odds": combined_odds}, "timestamp": time.time()}
        return {"selected_props": selected_props, "combined_odds": combined_odds}

    except Exception:
        return {}
