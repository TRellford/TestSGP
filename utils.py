import requests
import streamlit as st
from datetime import datetime, timedelta
import time

# **API Configuration**
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
EVENT_ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"

# **Cache Configuration**
CACHE = {}
CACHE_EXPIRATION = timedelta(minutes=15)

# **Category Mapping for Props**
category_map = {
    "player_points": "Points",
    "player_rebounds": "Rebounds",
    "player_assists": "Assists",
    "player_threes": "Threes",
    "player_points_rebounds": "Points + Rebounds",
    "player_points_assists": "Points + Assists",
    "player_rebounds_assists": "Rebounds + Assists",
    "player_points_rebounds_assists": "P + R + A"
}

def get_nba_games():
    """
    Fetch NBA games for today from the Balldontlie API with caching.

    Returns:
        list: A list of dictionaries containing game details (home_team, away_team, game_id, date).
    """
    today = datetime.today().strftime("%Y-%m-%d")
    if "games" in CACHE and time.time() - CACHE["games"]["timestamp"] < CACHE_EXPIRATION.total_seconds():
        return CACHE["games"]["data"]

    try:
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
        CACHE["games"] = {"data": formatted_games, "timestamp": time.time()}
        return formatted_games
    except Exception as e:
        st.error(f"❌ Unexpected error fetching games: {e}")
        return []

def get_event_id(selected_game):
    """
    Retrieve the event ID from The Odds API for a given NBA game with caching.

    Args:
        selected_game (dict): Dictionary containing game details (home_team, away_team, game_id).

    Returns:
        str or None: The event ID if found, None otherwise.
    """
    if "event_id" in CACHE and selected_game["game_id"] in CACHE["event_id"]:
        return CACHE["event_id"][selected_game["game_id"]]

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
                CACHE.setdefault("event_id", {})[selected_game["game_id"]] = event["id"]
                return event["id"]
        st.warning(f"⚠️ No matching event found for {selected_game['home_team']} vs {selected_game['away_team']}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error fetching event ID: {e}")
        return None

def fetch_all_props(event_id):
    """
    Fetch all player props for a game from The Odds API in a single call with caching.

    Args:
        event_id (str): The event ID from The Odds API.

    Returns:
        dict: The API response containing prop data, or an empty dict on failure.
    """
    cache_key = f"props_{event_id}"
    if cache_key in CACHE and time.time() - CACHE[cache_key]["timestamp"] < CACHE_EXPIRATION.total_seconds():
        return CACHE[cache_key]["data"]

    try:
        api_url = EVENT_ODDS_API_URL.format(event_id=event_id)
        params = {
            "apiKey": st.secrets["odds_api_key"],
            "regions": "us",
            "markets": "player_points,player_rebounds,player_assists,player_threes,"
                       "player_points_rebounds,player_points_assists,player_rebounds_assists,player_points_rebounds_assists",
            "bookmakers": "fanduel"
        }
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            CACHE[cache_key] = {"data": data, "timestamp": time.time()}
            return data
        else:
            st.error(f"❌ Error fetching props: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        st.error(f"❌ Unexpected error fetching props: {e}")
        return {}

def get_risk_level(odds):
    """
    Assign a risk level and emoji based on betting odds.

    Args:
        odds (int): The American odds value.

    Returns:
        tuple: (risk_level, emoji) indicating the risk assessment.
    """
    if -450 <= odds <= -300:
        return "Very Safe", "🔵"
    elif -299 <= odds <= -200:
        return "Safe", "🟢"
    elif -199 <= odds <= 100:
        return "Moderate Risk", "🟡"
    elif 101 <= odds <= 250:
        return "High Risk", "🟠"
    else:
        return "Very High Risk", "🔴"

def fetch_sgp_builder(selected_game, num_props=1, min_odds=None, max_odds=None, confidence_level=None):
    """
    Fetch and process player props for a Same Game Parlay (SGP) with optimized selection logic.

    Args:
        selected_game (dict): The selected game details.
        num_props (int): Number of props to return (default: 1).
        min_odds (int, optional): Minimum odds filter.
        max_odds (int, optional): Maximum odds filter.
        confidence_level (tuple, optional): Confidence range filter (min, max).

    Returns:
        dict: A dictionary containing the selected props, or empty if none are found.
    """
    # **Get the correct event ID**
    event_id = get_event_id(selected_game)
    if not event_id:
        return {}

    # **Fetch prop data**
    odds_data = fetch_all_props(event_id)
    if not odds_data.get("bookmakers"):
        st.error("❌ No bookmakers data available in the API response.")
        return {}
    fanduel = next((b for b in odds_data.get("bookmakers", []) if b["key"] == "fanduel"), None)
    if not fanduel or not fanduel.get("markets"):
        st.error("❌ FanDuel data or markets not available for this event.")
        return {}

    # **Initialize prop categories**
    prop_categories = {cat: [] for cat in category_map.values()}

    # **Process each market**
    for market in fanduel["markets"]:
        for outcome in market.get("outcomes", []):
            player_name = outcome.get("description", "Unknown Player")
            prop_key = market["key"].replace("_alternate", "")
            category = category_map.get(prop_key, "Other")
            if category == "Other":
                continue
            over_under = "Over" if "Over" in outcome["name"] else "Under"
            line_value = outcome.get("point", "N/A")
            odds = outcome["price"]

            # **Convert Decimal Odds to American Odds**
            if odds >= 2.0:
                american_odds = int((odds - 1) * 100)
            else:
                american_odds = int(-100 / (odds - 1))
            implied_prob = 1 / (1 + abs(american_odds) / 100) if american_odds < 0 else american_odds / (100 + american_odds)
            ai_prob = implied_prob  # Placeholder: No AI model, using implied probability
            confidence_boost = round(ai_prob * 100, 2)
            betting_edge = 0  # Since ai_prob equals implied_prob
            risk_level, emoji = get_risk_level(american_odds)
            insight_reason = f"{player_name} has a {confidence_boost:.0f}% chance based on implied probability."

            prop_data = {
                "player": player_name,
                "over_under": over_under,
                "prop": category,
                "line": line_value,
                "odds": american_odds,
                "implied_prob": round(implied_prob, 3),
                "ai_prob": round(ai_prob, 3),
                "confidence_boost": confidence_boost,
                "betting_edge": betting_edge,
                "risk_level": f"{emoji} {risk_level}",
                "why_this_pick": insight_reason,
                "alt_line": "alternate" in market["key"]
            }
            prop_categories[category].append(prop_data)

    # **Filter function**
    def satisfies_filters(prop):
        if min_odds is not None and (prop["odds"] < min_odds or prop["odds"] > max_odds):
            return False
        if confidence_level is not None and (prop["confidence_boost"] < confidence_level[0] or prop["confidence_boost"] > confidence_level[1]):
            return False
        return True

    # **Select props**
    selected_props = []
    # Step 1: Try to select one prop from each category
    for category in prop_categories:
        category_props = [p for p in prop_categories[category] if satisfies_filters(p)]
        if category_props:
            best_prop = max(category_props, key=lambda x: x["confidence_boost"])
            selected_props.append(best_prop)

    # Step 2: Fill remaining slots with highest confidence props
    all_filtered_props = [p for cat in prop_categories.values() for p in cat if satisfies_filters(p) and p not in selected_props]
    all_filtered_props_sorted = sorted(all_filtered_props, key=lambda x: x["confidence_boost"], reverse=True)
    while len(selected_props) < num_props and all_filtered_props_sorted:
        selected_props.append(all_filtered_props_sorted.pop(0))

    # **Handle case where no props are selected**
    if not selected_props:
        st.warning("🚨 No valid props found after filtering.")
        return {}

    # **Return the selected props**
    return {"selected_props": selected_props}
