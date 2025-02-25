import streamlit as st
import datetime
import math
from utils import (
    fetch_best_props, fetch_sgp_builder, fetch_sharp_money_trends,
    get_nba_games
)

st.set_page_config(page_title="NBA Betting AI", layout="wide")

# Sidebar Navigation
st.sidebar.title("🔍 Navigation")
menu_option = st.sidebar.selectbox("Select a Section:", ["Same Game Parlay", "SGP+"])


# Same Game Parlay (SGP)
if menu_option == "Same Game Parlay":
    st.header("🎯 Same Game Parlay (SGP) - One Game Only")

    date_option = st.radio("Choose Game Date:", ["Today's Games", "Tomorrow's Games"], key="sgp_date")
    game_date = datetime.date.today() if date_option == "Today's Games" else datetime.date.today() + datetime.timedelta(days=1)
    
    available_games = get_nba_games(game_date)
    
    st.write(f"📅 Fetching games for: {game_date.strftime('%Y-%m-%d')}")
    st.write(f"🎮 Number of games found: {len(available_games)}")

    if available_games:
        game_labels = [f"{game['home_team']} vs {game['away_team']}" for game in available_games]
        selected_game_label = st.selectbox("Select a Game:", game_labels, key="sgp_game")
        selected_game = next(g for g in available_games if f"{g['home_team']} vs {g['away_team']}" == selected_game_label)
        
        num_props = st.slider("Number of Props (1-8):", 1, 8, 1, key="sgp_num_props")
        
        if st.button("Generate SGP Prediction"):
            sgp_result = fetch_sgp_builder(selected_game, num_props=num_props)
            st.write(sgp_result)
    else:
        st.warning("🚨 No NBA games found for the selected date.")

# SGP+ (Multi-Game Parlay)
elif menu_option == "SGP+":
    st.header("🔥 Multi-Game Parlay (SGP+) - Select 2 to 12 Games")
    
    today_games = get_nba_games(datetime.date.today())
    tomorrow_games = get_nba_games(datetime.date.today() + datetime.timedelta(days=1))
    all_games = today_games + tomorrow_games
    game_labels = [f"{game['home_team']} vs {game['away_team']}" for game in all_games]
    selected_labels = st.multiselect("Select Games (Min: 2, Max: 12):", game_labels)
    selected_games = [g for g in all_games if f"{g['home_team']} vs {g['away_team']}" in selected_labels]
    
    if len(selected_games) < 2:
        st.warning("⚠️ You must select at least 2 games.")
    elif len(selected_games) > 12:
        st.warning("⚠️ You cannot select more than 12 games.")
    else:
        max_props_per_game = math.floor(24 / len(selected_games))
        props_per_game = st.slider(f"Choose Props Per Game (Max {max_props_per_game}):", 1, max_props_per_game)
        
        if st.button("Generate SGP+ Prediction"):
            num_props_total = props_per_game * len(selected_games)
            sgp_plus_result = fetch_sgp_builder(selected_games, num_props=num_props_total, multi_game=True)
            st.write(sgp_plus_result)
