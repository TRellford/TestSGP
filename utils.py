import requests
import streamlit as st

# Retrieve API key from Streamlit secrets
ODDS_API_KEY = st.secrets["odds_api_key"]
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"

def get_available_games():
    """Fetch available NBA games for SGP selection."""
    response = requests.get(f"{ODDS_API_URL}/?apiKey={ODDS_API_KEY}&regions=us&markets=spreads,totals")
    if response.status_code == 200:
        games = response.json()
        return [{"id": game["id"], "name": f"{game['home_team']} vs {game['away_team']}"} for game in games]
    return []

def get_player_props(game_id):
    """Fetch player props for a given game using The Odds API."""
    url = f"{ODDS_API_URL}?apiKey={ODDS_API_KEY}&regions=us&markets=player_points,player_assists,player_rebounds"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        odds_data = response.json()
        props = []

        for game in odds_data:
            if game["id"] == game_id:  # Ensure we're pulling data for the selected game
                for bookmaker in game.get("bookmakers", []):  # Corrected key
                    for market in bookmaker.get("markets", []):
                        for outcome in market.get("outcomes", []):
                            props.append({
                                "id": outcome["name"],
                                "player": outcome["name"],
                                "type": market["key"].replace("player_", "").capitalize(),
                                "odds": outcome["price"]
                            })

        return props if props else [{"error": "No player props found"}]  # Debugging output

    return [{"error": f"API Request Failed: {response.status_code}, {response.text}"}]
    
def calculate_parlay_odds(selected_props):
    """Calculate the final parlay odds."""
    total_odds = 1.0
    for prop in selected_props:
        prop_odds = prop['odds']
        total_odds *= (1 + (prop_odds / 100) if prop_odds > 0 else 1 + (100 / abs(prop_odds)))
    return round(total_odds, 2)# Debugging output
