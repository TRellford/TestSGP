import requests
import streamlit as st
from datetime import datetime
import numpy as np
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelogs

# API Configuration
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"

# Fetch NBA Games
def get_nba_games(date):
    """Fetch NBA games from Balldontlie API."""
    try:
        url = f"{BALL_DONT_LIE_API_URL}/games"
        headers = {"Authorization": st.secrets["balldontlie_api_key"]}
        params = {"dates[]": date.strftime("%Y-%m-%d")}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            st.error(f"❌ Error fetching games: {response.status_code}")
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

# Fetch SGP Bets
def fetch_sgp_builder(selected_game, num_props=1, min_odds=None, max_odds=None, confidence_level=None):
    """Generate optimized Same Game Parlay (SGP)."""

    response = requests.get(
        f"{ODDS_API_URL}",
        params={"apiKey": st.secrets["odds_api_key"], "regions": "us", "markets": "player_points,player_assists,player_rebounds"}
    )

    if response.status_code != 200:
        st.error(f"❌ Error fetching props: {response.status_code}")
        return []

    odds_data = response.json()
    best_props = []

    for game in odds_data:
        if game["home_team"] == selected_game["home_team"] and game["away_team"] == selected_game["away_team"]:
            for bookmaker in game.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        price = outcome["price"]
                        player_name = outcome["name"]
                        prop_type = market["key"].replace("player_", "").capitalize()

                        # Convert sportsbook odds to implied probability
                        sportsbook_implied_prob = 1 / (1 + (price / 100 if price > 0 else 100 / abs(price)))

                        # AI Model Probabilities (Placeholder)
                        ai_probability = 0.65

                        # Betting edge calculation
                        betting_edge = (ai_probability - sportsbook_implied_prob) / sportsbook_implied_prob if sportsbook_implied_prob > 0 else 0
                        confidence_boost = min(max(betting_edge * 50 + 50, 0), 100)

                        # Filter by Confidence Score
                        if confidence_level:
                            confidence_mapping = {"High": 80, "Medium": 60, "Low": 40}
                            if confidence_boost < confidence_mapping[confidence_level]:
                                continue

                        # Filter by Odds Range
                        if min_odds is not None and max_odds is not None:
                            if not (min_odds <= price <= max_odds):
                                continue

                        best_props.append({
                            "player": player_name,
                            "prop": prop_type,
                            "odds": price,
                            "implied_prob": sportsbook_implied_prob,
                            "ai_prob": ai_probability,
                            "confidence_boost": confidence_boost,
                            "betting_edge": betting_edge
                        })

    if not best_props:
        return "No valid props found for this game."

    # Select top N props
    selected_props = sorted(best_props, key=lambda x: x["confidence_boost"], reverse=True)[:num_props]

    # Calculate Combined Odds
    combined_odds = 1.0
    for prop in selected_props:
        decimal_odds = (prop["odds"] / 100 + 1) if prop["odds"] > 0 else (1 + 100 / abs(prop["odds"]))
        combined_odds *= decimal_odds

    american_odds = int((combined_odds - 1) * 100) if combined_odds > 2 else int(-100 / (combined_odds - 1))

    return {
        "selected_props": selected_props,
        "combined_odds": american_odds
    }
