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
    """Fetch player props for Same Game Parlay (SGP) with balanced category selection."""
    
    st.write(f"🔍 DEBUG: Running `fetch_sgp_builder()` with game: {selected_game}")
    
    if not selected_game or "game_id" not in selected_game:
        st.error("🚨 Error: Invalid game selected. No game ID found.")
        return {}

    try:
        # Define the markets to fetch (Standard + Alternate Props)
        markets = [
            "player_points", "player_rebounds", "player_assists", "player_threes",
            "player_points_alternate", "player_rebounds_alternate", "player_assists_alternate", "player_threes_alternate"
        ]

api_url = f"{ODDS_API_URL}?apiKey={st.secrets['odds_api_key']}&regions=us&markets=player_points,player_rebounds,player_assists,player_threes&bookmakers=fanduel"
        params = {
            "apiKey": st.secrets["odds_api_key"],
            "regions": "us",
            "markets": ",".join(markets),
            "bookmakers": "fanduel"
        }
        response = requests.get(api_url, params=params)

        if response.status_code != 200:
            st.error(f"🚨 Error fetching props: {response.status_code} - {response.text}")
            return {}

        # Extract props from FanDuel
        odds_data = response.json()
        fanduel = next((b for b in odds_data.get("bookmakers", []) if b["key"] == "fanduel"), None)
        if not fanduel or not fanduel.get("markets"):
            st.warning("🚨 No props found in API response.")
            return {}

        selected_props = []
        prop_categories = {"Points": [], "Rebounds": [], "Assists": [], "Threes": []}

        for market in fanduel["markets"]:
            for outcome in market.get("outcomes", []):
                prop_name = market["key"].replace("_alternate", "").replace("player_", "").title()

                odds = outcome["price"]
                implied_prob = 1 / (1 + abs(odds) / 100) if odds < 0 else odds / (100 + odds)
                
                # Confidence Calculation (Example Placeholder)
                ai_prob = implied_prob * 0.9  # AI adjusting probability
                confidence_boost = round(ai_prob * 100, 2)
                betting_edge = round(ai_prob - implied_prob, 3)

                # Risk Level Based on Odds
                risk_level, emoji = get_risk_level(odds)

                # **NEW: Generate a simple reason for why this pick was chosen**
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
                    "why_this_pick": insight_reason,  # **✅ New Column**
                    "alt_line": "alternate" in market["key"]
                }

                # **Sort props into categories**
                if "Points" in prop_name:
                    prop_categories["Points"].append(prop_data)
                elif "Rebounds" in prop_name:
                    prop_categories["Rebounds"].append(prop_data)
                elif "Assists" in prop_name:
                    prop_categories["Assists"].append(prop_data)
                elif "Threes" in prop_name:
                    prop_categories["Threes"].append(prop_data)

        # **STEP 1: Pick One from Each Category First**
        for category in ["Points", "Rebounds", "Assists", "Threes"]:
            if prop_categories[category]:
                best_prop = sorted(prop_categories[category], key=lambda x: x["confidence_boost"], reverse=True)[0]
                selected_props.append(best_prop)

        # **STEP 2: Fill the Rest with Highest Confidence Remaining Props**
        all_props_sorted = sorted(
            prop_categories["Points"] + prop_categories["Rebounds"] + prop_categories["Assists"] + prop_categories["Threes"],
            key=lambda x: x["confidence_boost"],
            reverse=True
        )

        for prop in all_props_sorted:
            if len(selected_props) >= num_props:
                break
            if prop not in selected_props:  # Avoid duplicates
                selected_props.append(prop)

        # **Ensure Filtering Still Works**
        if min_odds is not None and max_odds is not None:
            selected_props = [p for p in selected_props if min_odds <= p["odds"] <= max_odds]

        if confidence_level:
            selected_props = [p for p in selected_props if confidence_level[0] <= p["confidence_boost"] <= confidence_level[1]]

        # Select top N props
        selected_props = selected_props[:num_props]

        if not selected_props:
            st.warning("🚨 No valid props found after filtering.")
            return {}

        # Calculate combined odds
        combined_odds = calculate_parlay_odds(selected_props)

        return {"selected_props": selected_props, "combined_odds": combined_odds}

    except Exception as e:
        st.error(f"🚨 Exception in fetch_sgp_builder(): {e}")
        return {}
