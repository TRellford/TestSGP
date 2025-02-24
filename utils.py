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
        st.write("🔍 **DEBUG: API Response for Games:**", games)  # Prints the full API response
        
        # Check if 'games' is a list or dict
        if isinstance(games, list):  
            return [{"id": game.get("id", "MISSING_ID"), "name": f"{game.get('home_team', 'Unknown')} vs {game.get('away_team', 'Unknown')}"} for game in games]
        else:
            st.error("⚠️ API returned unexpected structure: Expected a list but got a dictionary.")
            st.write("🔍 **Full API Response:**", games)
    
    else:
        st.error(f"⚠️ API Request Failed: {response.status_code} - {response.text}")
    
    return []

def get_player_props(game_id):
    """Fetch player props for a given game using The Odds API."""
    url = f"{ODDS_API_URL}?apiKey={ODDS_API_KEY}&regions=us&markets=player_points,player_assists,player_rebounds"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        odds_data = response.json()
        st.write("API Response for Props:", odds_data)  # Debugging output

        props = []
        for game in odds_data:
            if "id" in game and game["id"] == game_id:  # Ensure "id" exists
                for bookmaker in game.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        for outcome in market.get("outcomes", []):
                            props.append({
                                "id": outcome.get("name", "N/A"),  # Avoid KeyError
                                "player": outcome.get("name", "Unknown"),
                                "type": market["key"].replace("player_", "").capitalize(),
                                "odds": outcome.get("price", "N/A")  # Avoid missing odds
                            })

        return props if props else [{"error": "No player props found"}]

    return [{"error": f"API Request Failed: {response.status_code}, {response.text}"}]

def calculate_parlay_odds(selected_props):
    """Calculate the final parlay odds."""
    total_odds = 1.0
    for prop in selected_props:
        prop_odds = prop['odds']
        total_odds *= (1 + (prop_odds / 100) if prop_odds > 0 else 1 + (100 / abs(prop_odds)))
    return round(total_odds, 2)# Debugging output
