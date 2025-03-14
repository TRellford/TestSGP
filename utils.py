import requests
import streamlit as st
from datetime import datetime
import numpy as np
from nba_api.stats.static import teams

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
            st.error(f"❌ Error fetching games: {response.status_code} - {response.text}")
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
        return formatted_games

    except Exception as e:
        st.error(f"❌ Unexpected error fetching games: {e}")
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
            st.error(f"❌ Error fetching event ID: {response.status_code} - {response.text}")
            return None

        events_data = response.json()
        for event in events_data:
            if event["home_team"] == selected_game["home_team"] and event["away_team"] == selected_game["away_team"]:
                return event["id"]

        return None

    except Exception as e:
        st.error(f"❌ Unexpected error fetching event ID: {e}")
        return None

# Fetch Player Props for a Given Game (with Debugging Logs)
def fetch_sgp_builder(selected_game, num_props=1, min_odds=None, max_odds=None, confidence_level=None):
    try:
        props = fetch_best_props(selected_game, min_odds, max_odds, confidence_level)

        if not props:
            return {"selected_props": [], "combined_odds": None}

        props = sorted(props, key=lambda x: x["confidence_boost"], reverse=True)
        selected_props = props[:num_props]

        combined_odds = 1.0
        for prop in selected_props:
            odds = prop["odds"]
            decimal_odds = (odds / 100 + 1) if odds > 0 else (1 + 100 / abs(odds))
            combined_odds *= decimal_odds

        combined_american_odds = int((combined_odds - 1) * 100) if combined_odds > 2 else int(-100 / (combined_odds - 1))

        for prop in selected_props:
            prop["Risk Level"], prop["Risk Emoji"] = get_risk_level(prop["odds"])
            prop["Why This Pick?"] = generate_insight(prop)

        return {
            "selected_props": selected_props,
            "combined_odds": combined_american_odds
        }

    except Exception as e:
        print(f"❌ Error in fetch_sgp_builder: {str(e)}")
        return {"selected_props": [], "combined_odds": None}

def get_risk_level(odds):
    if -450 <= odds <= -300:
        return "🔵 Very Safe", "🔵"
    elif -299 <= odds <= -200:
        return "🟢 Safe", "🟢"
    elif -199 <= odds <= 100:
        return "🟡 Moderate", "🟡"
    elif 101 <= odds <= 250:
        return "🟠 High Risk", "🟠"
    else:
        return "🔴 Very High Risk", "🔴"

def generate_insight(prop):
    return (
        f"{prop['player']} has hit {prop['prop']} in {round(prop['confidence_boost'], 1)}% of recent games. "
        f"Odds: {prop['odds']}. AI suggests a {prop['Risk Level']} play."
    )
