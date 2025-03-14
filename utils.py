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

def fetch_games(date, max_retries=3, initial_delay=2):
    """Fetch NBA games from Balldontlie API for a given date with retries."""
    api_key = st.secrets.get("balldontlie_api_key", None)
    if not api_key:
        st.error("❌ Balldontlie API key is missing in secrets. Please add 'balldontlie_api_key' to your Streamlit secrets.")
        return []

    url = f"{BALL_DONT_LIE_API_URL}/games"
    headers = {"Authorization": api_key}
    params = {"dates[]": date.strftime("%Y-%m-%d")}

    retries = 0
    while retries < max_retries:
        try:
            st.write(f"Fetching games for date: {date.strftime('%Y-%m-%d')} (Attempt {retries + 1}/{max_retries})")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"Request URL: {response.url}")  # Debug: Log the exact
