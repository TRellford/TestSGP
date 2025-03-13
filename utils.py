import requests
import numpy as np
from datetime import date
import streamlit as st
from scipy.stats import poisson
import random

# Constants
SEASON = "2023"  # Adjust for current NBA season

def fetch_games():
    """Fetch today's NBA games from balldontlie API."""
    today = date.today().isoformat()
    url = f"https://www.balldontlie.io/api/v1/games?start_date={today}&end_date={today}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            games = [
                {
                    "id": game['id'],
                    "display": f"{game['home_team']['abbreviation']} vs {game['visitor_team']['abbreviation']}",
                    "home_team": game['home_team']['full_name'],
                    "away_team": game['visitor_team']['full_name']
                }
                for game in data['data']
            ]
            return games if games else [{"display": "No games available"}]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching games: {e}")
        return [{"display": "Error fetching games"}]

def fetch_props(game_id):
    """Fetch player props and alternate lines from The Odds API."""
    api_key = st.secrets["odds_api_key"]
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{game_id}/odds?regions=us&markets=player_points,player_rebounds,player_assists&oddsFormat=american&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        props = {}
        if 'bookmakers' in data:
            for bookmaker in data['bookmakers'][:1]:  # Use first bookmaker for simplicity
                for market in bookmaker['markets']:
                    for outcome in market['outcomes']:
                        prop_name = f"{outcome['description']} {outcome['name']}"
                        odds = outcome['price']
                        props[prop_name] = {
                            'odds': odds,
                            'confidence': get_initial_confidence(odds),
                            'risk_level': get_risk_level(odds)
                        }
        return props
    except requests.exceptions.RequestException as e:
        print(f"Error fetching props for game {game_id}: {e}")
        return {}

def get_player_stats(player_name):
    """Fetch player season stats from balldontlie API."""
    url = f"https://www.balldontlie.io/api/v1/players?search={player_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        players = response.json()['data']
        if not players:
            return None
        player_id = players[0]['id']
        
        stats_url = f"https://www.balldontlie.io/api/v1/season_averages?season={SEASON}&player_ids[]={player_id}"
        stats_response = requests.get(stats_url)
        stats_response.raise_for_status()
        stats_data = stats_response.json()['data']
        return stats_data[0] if stats_data else None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching player stats for {player_name}: {e}")
        return None

def get_initial_confidence(odds):
    """Initial confidence score based on odds (simplified heuristic)."""
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
    """Calculate combined parlay odds from a list of American odds."""
    decimal_odds = [1 + (abs(odds) / 100) if odds < 0 else (odds / 100) + 1 for odds in odds_list]
    final_odds = np.prod(decimal_odds)
    return round(final_odds, 2)

def bayesian_update(prior, likelihood, evidence):
    """Bayesian Inference for updating confidence scores."""
    posterior = (likelihood * prior) / evidence
    return min(max(posterior, 0.1), 0.9)  # Bound between 0.1 and 0.9

def xgboost_predict(player_stats, prop_value, prop_type):
    """Simplified XGBoost prediction (simulated for MVP)."""
    if not player_stats:
        return 0.5
    stat_key = {'points': 'pts', 'rebounds': 'reb', 'assists': 'ast'}[prop_type]
    avg = player_stats.get(stat_key, 0)
    # Simulate XGBoost: higher avg relative to prop value = higher confidence
    return min(0.9, max(0.1, avg / prop_value if prop_value > 0 else 0.5))

def monte_carlo_simulation(player_stats, prop_value, prop_type, n_simulations=10000):
    """Monte Carlo simulation for prop hit rate."""
    if not player_stats:
        return 0.5
    stat_key = {'points': 'pts', 'rebounds': 'reb', 'assists': 'ast'}[prop_type]
    avg = player_stats.get(stat_key, 0)
    simulations = np.random.normal(avg, avg * 0.2, n_simulations)  # Assume 20% variance
    hit_rate = np.mean(simulations > prop_value)
    return hit_rate

def poisson_score_prediction(team_avg, opponent_defense):
    """Poisson distribution for score prediction."""
    adjusted_avg = team_avg * (1 - opponent_defense * 0.1)  # Simplified adjustment
    return poisson.pmf(range(50, 150), adjusted_avg)

def linear_regression_adjustment(player_stats, game_context):
    """Linear regression for adjustments (simulated for MVP)."""
    if not player_stats:
        return 1.0
    pace_factor = game_context.get('pace', 1.0)
    injury_factor = 0.8 if game_context.get('injury', False) else 1.0
    return pace_factor * injury_factor

def detect_line_discrepancies(book_odds, model_confidence):
    """AI-based line discrepancy detector."""
    implied_odds = 1 / (1 + (abs(book_odds) / 100) if book_odds < 0 else (book_odds / 100) + 1)
    model_odds = model_confidence
    return model_odds > implied_odds * 1.1  # Flag if model odds are 10% better

def predict_prop_confidence(prop, book_odds, player_stats, game_context):
    """Predict confidence score using advanced models."""
    prop_parts = prop.split()
    prop_type = prop_parts[-1].lower()  # e.g., points, rebounds, assists
    prop_value = float(prop_parts[-2])  # e.g., 20.5
    
    # Initial confidence (prior)
    prior_confidence = get_initial_confidence(book_odds)
    
    # Bayesian Inference (simulated live update)
    likelihood = 0.7  # Placeholder for live data
    evidence = 0.9  # Placeholder for normalization
    bayesian_confidence = bayesian_update(prior_confidence, likelihood, evidence)
    
    # XGBoost Prediction
    xgboost_confidence = xgboost_predict(player_stats, prop_value, prop_type)
    
    # Monte Carlo Simulation
    monte_carlo_confidence = monte_carlo_simulation(player_stats, prop_value, prop_type)
    
    # Linear Regression Adjustment
    adjustment_factor = linear_regression_adjustment(player_stats, game_context)
    
    # Combine scores (weighted average)
    final_confidence = (bayesian_confidence * 0.2 + xgboost_confidence * 0.3 + 
                        monte_carlo_confidence * 0.3) * adjustment_factor
    
    return round(final_confidence, 2)

def get_sharp_money_insights(selected_props):
    """Track sharp money using odds movement from The Odds API."""
    api_key = st.secrets["odds_api_key"]
    insights = {}
    for game, props in selected_props.items():
        for prop in props:
            # Simulate fetching odds movement (requires historical odds or multiple calls)
            url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds-history?regions=us&markets=player_points,player_rebounds,player_assists&oddsFormat=american&apiKey={api_key}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                # Simplified: Check if odds shortened significantly
                initial_odds = data.get('initial_odds', {}).get(prop, book_odds + 20)
                current_odds = book_odds
                odds_shift = (initial_odds - current_odds) / abs(initial_odds)
                sharp_indicator = "🔥 Sharp Money" if odds_shift > 0.1 else "Public Money"
                insights[prop] = {"Sharp Indicator": sharp_indicator, "Odds Shift %": round(odds_shift * 100, 2)}
            except requests.exceptions.RequestException:
                insights[prop] = {"Sharp Indicator": "Data Unavailable", "Odds Shift %": 0}
    return insights
