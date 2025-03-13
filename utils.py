import requests
import numpy as np
from datetime import date
import streamlit as st
from scipy.stats import poisson
import time
import random

# Constants
BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"
ODDS_API_URL = "https://api.the-odds-api.com/v4"

# Simple in-memory cache for player stats
player_stats_cache = {}

def get_current_season_year():
    """Determine the current NBA season year based on today's date."""
    today = date.today()
    if today.month >= 10:  # October or later: current year
        return str(today.year)
    else:  # Before October: previous year
        return str(today.year - 1)

def fetch_games(date):
    """Fetch NBA games from Balldontlie API for a given date."""
    try:
        url = f"{BALL_DONT_LIE_API_URL}/games"
        headers = {"Authorization": st.secrets["balldontlie_api_key"]}
        params = {"dates[]": date.strftime("%Y-%m-%d")}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 401:
            st.error("❌ Unauthorized (401). Check your Balldontlie API key in secrets.")
            return []
        if response.status_code != 200:
            st.error(f"❌ Error fetching games: {response.status_code} - {response.text}")
            return []

        games_data = response.json().get("data", [])

        if not games_data:
            return []

        formatted_games = [
            {
                "id": game["id"],
                "display": f"{game['home_team']['abbreviation']} vs {game['visitor_team']['abbreviation']}",
                "home_team": game["home_team"]["full_name"],
                "away_team": game["visitor_team"]["full_name"],
                "date": game["date"]
            }
            for game in games_data
        ]
        return formatted_games

    except Exception as e:
        st.error(f"❌ Unexpected error fetching games: {e}")
        return []

def fetch_odds_api_events(date):
    """Fetch all NBA events from The Odds API for a given date."""
    api_key = st.secrets.get("odds_api_key", None)
    if not api_key:
        st.error("❌ The Odds API key is missing in secrets. Please add 'odds_api_key' to your Streamlit secrets.")
        return []

    url = f"{ODDS_API_URL}/sports/basketball_nba/events?date={date.strftime('%Y-%m-%d')}&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error fetching events from The Odds API: {e}")
        if "429" in str(e):
            st.error("⚠️ The Odds API rate limit exceeded. Check your usage at https://the-odds-api.com/.")
        return []

def fetch_props(event_id, prop_types=None):
    """Fetch player props from The Odds API for specified prop types."""
    api_key = st.secrets.get("odds_api_key", None)
    if not api_key:
        st.error("❌ The Odds API key is missing in secrets. Please add 'odds_api_key' to your Streamlit secrets.")
        return {}

    # Include all desired markets: points, rebounds, assists, steals, blocks
    markets = "player_points,player_rebounds,player_assists,player_steals,player_blocks"
    url = f"{ODDS_API_URL}/sports/basketball_nba/events/{event_id}/odds?regions=us&markets={markets}&oddsFormat=american&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        props = {}
        if 'bookmakers' in data and data['bookmakers']:
            for bookmaker in data['bookmakers'][:1]:  # Use first bookmaker for simplicity
                for market in bookmaker['markets']:
                    prop_type = market['key'].replace('player_', '')  # e.g., 'points', 'rebounds', 'assists', 'steals', 'blocks'
                    # Only process if prop_type is in the selected list or all are selected
                    if not prop_types or prop_type in prop_types:
                        for outcome in market['outcomes']:
                            if 'point' in outcome:
                                prop_name = f"{outcome['description']} {outcome['name']} {outcome['point']} {prop_type}"
                                odds = outcome['price']
                                props[prop_name] = {
                                    'odds': odds,
                                    'confidence': get_initial_confidence(odds),
                                    'risk_level': get_risk_level(odds),
                                    'prop_type': prop_type,
                                    'point': outcome['point']
                                }
        if not props:
            st.info(f"No props (points, rebounds, assists, steals, blocks) available for event {event_id} from the bookmaker for the selected types.")
        return props

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error fetching props for event {event_id}: {e}")
        if "429" in str(e):
            st.error("⚠️ The Odds API rate limit exceeded. Check your usage at https://the-odds-api.com/.")
        return {}

def get_player_stats(player_name, season, max_retries=3, initial_delay=2):
    """Fetch player season stats from balldontlie API with caching, delay, and retries."""
    cache_key = f"{player_name}_{season}"
    if cache_key in player_stats_cache:
        return player_stats_cache[cache_key]

    # Add a delay before making the API request to avoid rate limits
    time.sleep(initial_delay)

    retries = 0
    while retries < max_retries:
        try:
            # Fetch player ID
            url = f"{BALL_DONT_LIE_API_URL}/players?search={player_name}"
            response = requests.get(url, headers={"Authorization": st.secrets["balldontlie_api_key"]})
            response.raise_for_status()
            players = response.json()['data']
            if not players:
                player_stats_cache[cache_key] = None
                return None
            player_id = players[0]['id']

            # Add a small delay before the second request to fetch stats
            time.sleep(initial_delay)

            # Fetch player stats
            stats_url = f"{BALL_DONT_LIE_API_URL}/season_averages?
