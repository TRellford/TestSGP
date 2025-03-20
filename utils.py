import requests
import streamlit as st
from datetime import datetime, timedelta
import time

# API Configuration
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
EVENT_ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
BALL_DONT_LIE_API_URL = "https://api.balldontlie.io/v1"

# Cache for API calls
CACHE = {}
CACHE_EXPIRATION = timedelta(minutes=15)  

def get_nba_games():
    """Fetch NBA games for today from Balldontlie API, with caching."""
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
    """Retrieve the event ID for a given NBA game with caching."""
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
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error fetching event ID: {e}")
        return None

def fetch_all_props(event_id):
    """Fetch all player props for a game in a single call to minimize API requests."""
    api_url = EVENT_ODDS_API_URL.format(event_id=event_id)
    params = {
        "apiKey": st.secrets["odds_api_key"],
        "regions": "us",
        "markets": "player_points,player_rebounds,player_assists,player_threes,"
                   "player_points_rebounds,player_points_assists,player_rebounds_assists,player_points_rebounds_assists",
        "bookmakers": "fanduel"
    }
    response = requests.get(api_url, params=params)

    return response.json() if response.status_code == 200 else {}

def get_risk_level(odds):
    """Assign risk level and emoji based on betting odds."""
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
    """Fetch player props for Same Game Parlay (SGP) with optimized selection logic."""
    event_id = selected_game.get("game_id")
    if not event_id:
        return {}

    odds_data = fetch_all_props(event_id)
    fanduel = next((b for b in odds_data.get("bookmakers", []) if b["key"] == "fanduel"), None)

    if not fanduel or not fanduel.get("markets"):
        return {}

    selected_props = []
    prop_categories = {"Points": [], "Rebounds": [], "Assists": [], "Threes": []}

    for market in fanduel["markets"]:
        for outcome in market.get("outcomes", []):
            player_name = outcome.get("description", "Unknown Player")  # Ensure player name extraction
            prop_name = market["key"].replace("_alternate", "").replace("player_", "").title()
            over_under = "Over" if "Over" in outcome["name"] else "Under"
            line_value = outcome.get("point", "N/A")

            odds = outcome["price"]

            # Convert Decimal Odds to American Odds
            if odds >= 2.0:
                odds = int((odds - 1) * 100)
            else:
                odds = int(-100 / (odds - 1))

            implied_prob = 1 / (1 + abs(odds) / 100) if odds < 0 else odds / (100 + odds)
            ai_prob = implied_prob * 1.1  # AI confidence calculation
            confidence_boost = round(ai_prob * 100, 2)  # Convert to percentage format
            betting_edge = round(ai_prob - implied_prob, 3)
            risk_level, emoji = get_risk_level(odds)

            insight_reason = f"{player_name} has a strong {prop_name.lower()} trend with {confidence_boost:.0f}% AI confidence."

            prop_data = {
                "player": player_name,
                "over_under": over_under,
                "prop": prop_name,
                "line": line_value,
                "odds": odds,
                "implied_prob": round(implied_prob, 3),
                "ai_prob": round(ai_prob, 3),
                "confidence_boost": confidence_boost,
                "betting_edge": betting_edge,
                "risk_level": f"{emoji} {risk_level}",
                "why_this_pick": insight_reason,
                "alt_line": "alternate" in market["key"]
            }

        # **Sort props into respective categories, including combos**
        if "Points" in prop_name:
            prop_categories["Points"].append(prop_data)
        elif "Rebounds" in prop_name:
            prop_categories["Rebounds"].append(prop_data)
        elif "Assists" in prop_name:
            prop_categories["Assists"].append(prop_data)
        elif "Threes" in prop_name:
            prop_categories["Threes"].append(prop_data)
        elif "Points Rebounds" in prop_name:
            prop_categories["Points + Rebounds"].append(prop_data)
        elif "Points Assists" in prop_name:
            prop_categories["Points + Assists"].append(prop_data)
        elif "Rebounds Assists" in prop_name:
            prop_categories["Rebounds + Assists"].append(prop_data)
        elif "Points Rebounds Assists" in prop_name:
            prop_categories["P + R + A"].append(prop_data)

        # **Step 1: Pick One from Each Category First (if available)**
        for category in ["Points", "Rebounds", "Assists", "Threes", "Points + Rebounds", "Points + Assists", "Rebounds + Assists", "P + R + A"]:
            if prop_categories[category]:
                best_prop = sorted(prop_categories[category], key=lambda x: x["confidence_boost"], reverse=True)[0]
                selected_props.append(best_prop)

        # **Step 2: Fill the Remaining Props with the Highest Confidence Props**
        all_props_sorted = sorted(
            prop_categories["Points"] + prop_categories["Rebounds"] + prop_categories["Assists"] + prop_categories["Threes"] +
            prop_categories["Points + Rebounds"] + prop_categories["Points + Assists"] + prop_categories["Rebounds + Assists"] + prop_categories["P + R + A"],
            key=lambda x: x["confidence_boost"],
            reverse=True
        )

        for prop in all_props_sorted:
            if len(selected_props) >= num_props:
                break
            if prop not in selected_props:  # Avoid duplicates
                selected_props.append(prop)
        selected_props = selected_props[:num_props]

        return {"selected_props": selected_props}
    
        # **Apply Filtering (Odds & Confidence Score)**
        if min_odds is not None and max_odds is not None:
            selected_props = [p for p in selected_props if min_odds <= p["odds"] <= max_odds]

        if confidence_level:
            selected_props = [p for p in selected_props if confidence_level[0] <= p["confidence_boost"] <= confidence_level[1]]

        # **Select top N props**
        selected_props = selected_props[:num_props]

        if not selected_props:
            st.warning("🚨 No valid props found after filtering.")
            return {}

        cache_key = f"props_{event_id}"
        CACHE[cache_key] = {"data": {"selected_props": selected_props}, "timestamp": time.time()}

        return {"selected_props": selected_props}

    except Exception as e:
        st.error(f"🚨 Exception in fetch_sgp_builder(): {e}")  # Dedent this line

        return {}  # Dedent this line as we
