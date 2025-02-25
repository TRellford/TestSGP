import requests
import streamlit as st

# API Configuration
ODDS_API_KEY = st.secrets["odds_api_key"]
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"

def get_nba_games(date):
    """Fetch NBA games from Balldontlie API."""
    url = f"{BALL_DONT_LIE_API_URL}/games"
    headers = {"Authorization": st.secrets["balldontlie_api_key"]}
    params = {"dates[]": date.strftime("%Y-%m-%d")}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        st.error(f"❌ Error fetching games: {response.status_code}")
        return []
    
    games_data = response.json().get("data", [])
    formatted_games = [{
        "home_team": game["home_team"]["full_name"],
        "away_team": game["visitor_team"]["full_name"],
        "game_id": game["id"]
    } for game in games_data]
    return formatted_games

def fetch_best_props(selected_game):
    """Fetch best player props from The Odds API."""
    response = requests.get(
        f"{ODDS_API_URL}",
        params={"apiKey": ODDS_API_KEY, "regions": "us", "markets": "player_points,player_assists,player_rebounds"}
    )
    
    if response.status_code != 200:
        st.error(f"❌ Error fetching props: {response.status_code}")
        return []
    
    odds_data = response.json()
    props = []
    for game in odds_data:
        if game["home_team"] == selected_game["home_team"] and game["away_team"] == selected_game["away_team"]:
            for bookmaker in game.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        props.append({
                            "player": outcome["name"],
                            "type": market["key"].replace("player_", "").capitalize(),
                            "odds": outcome["price"]
                        })
    return props

def fetch_sgp_builder(selected_game, num_props=1, multi_game=False):
    """Generate optimized SGP using AI-based filtering and confidence scores."""
    props = fetch_best_props(selected_game) if not multi_game else []
    if not props:
        return "No valid props found."
    
    # Sorting props by AI confidence score (example logic, replace with actual model)
    sorted_props = sorted(props, key=lambda x: x["odds"], reverse=True)[:num_props]
    
    combined_odds = 1.0
    for prop in sorted_props:
        decimal_odds = (prop["odds"] / 100 + 1) if prop["odds"] > 0 else (1 + 100 / abs(prop["odds"]))
        combined_odds *= decimal_odds
    
    american_odds = int((combined_odds - 1) * 100) if combined_odds > 2 else int(-100 / (combined_odds - 1))
    
    return {
        "selected_props": sorted_props,
        "combined_odds": american_odds
    }
