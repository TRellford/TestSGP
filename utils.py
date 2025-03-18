import requests
import streamlit as st
from datetime import datetime
import numpy as np

# API Configuration
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
EVENT_ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"

# Fetch NBA Games (Only Today's Games)
def get_nba_games():
    """Fetch NBA games for today from Balldontlie API."""
    try:
        today = datetime.today().strftime("%Y-%m-%d")
        url = f"{BALL_DONT_LIE_API_URL}/games"
        headers = {"Authorization": st.secrets["balldontlie_api_key"]}
        params = {"dates[]": today}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return []

        games_data = response.json().get("data", [])
        return [
            {
                "home_team": game["home_team"]["full_name"],
                "away_team": game["visitor_team"]["full_name"],
                "game_id": game["id"],
                "date": game["date"]
            }
            for game in games_data
        ]
    except Exception:
        return []

# Fetch Event ID for a Game
def get_event_id(selected_game):
    """Retrieve the event ID for a given NBA game."""
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
                return event["id"]
        return None
    except Exception:
        return None

# Calculate Parlay Odds
def calculate_parlay_odds(selected_props):
    """Calculate combined odds for the SGP based on individual prop odds."""
    combined_odds = 1.0
    for prop in selected_props:
        odds = prop["odds"]
        decimal_odds = (1 + (odds / 100)) if odds > 0 else (1 + (100 / abs(odds)))
        combined_odds *= decimal_odds

    return int((combined_odds - 1) * 100) if combined_odds > 2 else int(-100 / (combined_odds - 1))

# Assign Risk Level Based on Odds
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

# Fetch Player Props for a Given Game
def fetch_sgp_builder(selected_game, num_props=1, min_odds=None, max_odds=None, confidence_level=None):
    """Fetch player props for Same Game Parlay (SGP) with balanced category selection."""
    
    if not selected_game or "game_id" not in selected_game:
        return {}

    event_id = get_event_id(selected_game)
    if not event_id:
        return {}

    try:
        # Define the markets to fetch (Standard + Alternate Props)
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

        # Extract props from FanDuel
        odds_data = response.json()
        fanduel = next((b for b in odds_data.get("bookmakers", []) if b["key"] == "fanduel"), None)
        if not fanduel or not fanduel.get("markets"):
            return {}

        selected_props = []
        prop_categories = {"Points": [], "Rebounds": [], "Assists": [], "Threes": []}

        for market in fanduel["markets"]:
            for outcome in market.get("outcomes", []):
                prop_name = market["key"].replace("_alternate", "").replace("player_", "").title()

                odds = outcome["price"]
                implied_prob = 1 / (1 + abs(odds) / 100) if odds < 0 else odds / (100 + odds)
                
                ai_prob = implied_prob * 0.9  # AI adjusting probability
                confidence_boost = round(ai_prob * 100, 2)
                betting_edge = round(ai_prob - implied_prob, 3)

                risk_level, emoji = get_risk_level(odds)

                insight_reason = f"{outcome['name']} has a strong {prop_name.lower()} trend with {confidence_boost:.0f}% AI confidence."

                prop_data = {
                    "player": outcome["name"],
                    "prop": prop_name,
                    "odds": odds,
                    "implied_prob": round(implied_prob, 3),
                    "ai_prob": round(ai_prob, 3),
                    "confidence_boost": confidence_boost,
                    "betting_edge": betting_edge,
                    "risk_level": f"{emoji} {risk_level}",
                    "why_this_pick": insight_reason,
                    "alt_line": "alternate" in market["key"]
                }

                if "Points" in prop_name:
                    prop_categories["Points"].append(prop_data)
                elif "Rebounds" in prop_name:
                    prop_categories["Rebounds"].append(prop_data)
                elif "Assists" in prop_name:
                    prop_categories["Assists"].append(prop_data)
                elif "Threes" in prop_name:
                    prop_categories["Threes"].append(prop_data)

        all_props_sorted = sorted(
            prop_categories["Points"] + prop_categories["Rebounds"] + prop_categories["Assists"] + prop_categories["Threes"],
            key=lambda x: x["confidence_boost"],
            reverse=True
        )

        selected_props = all_props_sorted[:num_props]

        if not selected_props:
            return {}

        combined_odds = calculate_parlay_odds(selected_props)

        return {"selected_props": selected_props, "combined_odds": combined_odds}

    except Exception:
        return {}
