import requests

def get_available_games():
    """Fetch available NBA games for SGP selection."""
    response = requests.get("https://api-nba.com/games")
    if response.status_code == 200:
        return response.json().get('games', [])
    return []

def get_player_props(game_id):
    """Fetch player props for a given game."""
    response = requests.get(f"https://api-fanduel.com/player_props?game_id={game_id}")
    if response.status_code == 200:
        return response.json().get('props', [])
    return []

def calculate_parlay_odds(selected_props):
    """Calculate the final parlay odds."""
    total_odds = 1.0
    for prop in selected_props:
        prop_odds = prop['odds']
        total_odds *= (1 + (prop_odds / 100) if prop_odds > 0 else 1 + (100 / abs(prop_odds)))
    return round(total_odds, 2)
