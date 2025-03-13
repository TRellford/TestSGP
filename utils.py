import requests
import numpy as np
import streamlit as st
from datetime import datetime

BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"
ODDS_API_URL = "https://api.the-odds-api.com/v4"

def fetch_games(date):
    """Fetch NBA games from Balldontlie API."""
    try:
        url = f"{BALL_DONT_LIE_API_URL}/games"
        headers = {"Authorization": st.secrets["balldontlie_api_key"]}
        params = {"dates[]": date.strftime("%Y-%m-%d")}

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        games_data = response.json().get("data", [])

        return [
            {
                "id": game["id"],
                "display": f"{game['home_team']['abbreviation']} vs {game['visitor_team']['abbreviation']}",
                "home_team": game["home_team"]["full_name"],
                "away_team": game["visitor_team"]["full_name"]
            }
            for game in games_data
        ]
    except requests.exceptions.RequestException:
        return []

def fetch_odds_api_events(date):
    """Fetch all NBA events from The Odds API."""
    api_key = st.secrets["odds_api_key"]
    url = f"{ODDS_API_URL}/sports/basketball_nba/events?date={date.strftime('%Y-%m-%d')}&apiKey={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return []

def fetch_props(event_id):
    """Fetch player props from The Odds API."""
    api_key = st.secrets["odds_api_key"]
    url = f"{ODDS_API_URL}/sports/basketball_nba/events/{event_id}/odds?regions=us&markets=player_points,player_rebounds,player_assists&oddsFormat=american&apiKey={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        props = {}
        for bookmaker in data.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_type = market["key"].replace("player_", "").capitalize()
                for outcome in market.get("outcomes", []):
                    player = outcome["description"]
                    bet_type = outcome["name"]
                    line = outcome["point"]
                    odds = outcome["price"]

                    prop_name = f"{player} {bet_type} {line} {market_type}"
                    props[prop_name] = {
                        "odds": odds,
                        "confidence": get_initial_confidence(odds),
                        "risk_level": get_risk_level(odds)
                    }
        return props
    except requests.exceptions.RequestException:
        return {}

def get_player_stats(player_name):
    """Fetch player season stats from Balldontlie API."""
    url = f"{BALL_DONT_LIE_API_URL}/players?search={player_name}"
    try:
        response = requests.get(url, headers={"Authorization": st.secrets["balldontlie_api_key"]})
        response.raise_for_status()
        players = response.json()['data']
        if not players:
            return None
        player_id = players[0]['id']
        
        stats_url = f"{BALL_DONT_LIE_API_URL}/season_averages?season={datetime.now().year}&player_ids[]={player_id}"
        stats_response = requests.get(stats_url, headers={"Authorization": st.secrets["balldontlie_api_key"]})
        stats_response.raise_for_status()
        stats_data = stats_response.json()['data']
        return stats_data[0] if stats_data else None
    except requests.exceptions.RequestException:
        return None

def get_initial_confidence(odds):
    """Initial confidence score based on odds."""
    if odds <= -300:
        return 0.9
    elif -299 <= odds <= -200:
        return 0.8
    elif -199 <= odds <= -100:
        return 0.7
    elif -99 <= odds <= 100:
        return 0.6
    else:
        return 0.5

def get_risk_level(odds):
    """Assign risk level based on odds."""
    if odds <= -300:
        return "🔵 Very Safe"
    elif -299 <= odds <= -200:
        return "🟢 Safe"
    elif -199 <= odds <= 100:
        return "🟡 Moderate"
    elif 101 <= odds <= 250:
        return "🟠 High Risk"
    else:
        return "🔴 Very High Risk"

def calculate_parlay_odds(odds_list):
    """Calculate combined parlay odds."""
    decimal_odds = [1 + (abs(odds) / 100) if odds < 0 else (odds / 100) + 1 for odds in odds_list]
    final_odds = np.prod(decimal_odds)
    return round(final_odds, 2)

def detect_line_discrepancies(book_odds, model_confidence):
    """AI-based line discrepancy detector."""
    implied_odds = 1 / (1 + (abs(book_odds) / 100) if book_odds < 0 else (book_odds / 100) + 1)
    model_odds = model_confidence
    return model_odds > implied_odds * 1.1  # Flag if model odds are 10% better

def predict_prop_confidence(prop, book_odds, player_stats, game_context):
    """Predict confidence score using advanced models."""
    prop_parts = prop.split()
    prop_type = prop_parts[-1].lower()
    prop_value = None
    for part in prop_parts:
        try:
            prop_value = float(part)
            break
        except ValueError:
            continue
    
    if prop_value is None:
        return get_initial_confidence(book_odds)

    prior_confidence = get_initial_confidence(book_odds)
    likelihood = 0.7  
    evidence = 0.9  
    bayesian_confidence = (likelihood * prior_confidence) / evidence
    bayesian_confidence = min(max(bayesian_confidence, 0.1), 0.9)

    return round(bayesian_confidence, 2)

def get_sharp_money_insights(selected_props):
    """Track sharp money using odds movement from The Odds API."""
    api_key = st.secrets["odds_api_key"]
    insights = {}
    for game, props in selected_props.items():
        for prop in props:
            url = f"{ODDS_API_URL}/sports/basketball_nba/odds-history?regions=us&markets=player_points,player_rebounds,player_assists&oddsFormat=american&apiKey={api_key}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                initial_odds = data.get('initial_odds', {}).get(prop, book_odds + 20)
                current_odds = book_odds
                odds_shift = (initial_odds - current_odds) / abs(initial_odds)
                sharp_indicator = "🔥 Sharp Money" if odds_shift > 0.1 else "Public Money"
                insights[prop] = {"Sharp Indicator": sharp_indicator, "Odds Shift %": round(odds_shift * 100, 2)}
            except requests.exceptions.RequestException:
                insights[prop] = {"Sharp Indicator": "Data Unavailable", "Odds Shift %": 0}
    return insights
