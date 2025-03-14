import streamlit as st
import datetime
import math
from utils import (
    fetch_sgp_builder,
    get_nba_games
)

st.set_page_config(page_title="NBA Same Game Parlay AI", layout="wide")

# Sidebar Navigation
st.sidebar.title("🔍 Navigation")
menu_option = st.sidebar.selectbox("Select a Section:", ["Same Game Parlay"])

# Same Game Parlay (SGP) Section
if menu_option == "Same Game Parlay":
    st.header("🎯 Same Game Parlay (SGP) - One Game Only")

    # Game Date Selection
    st.subheader(f"📅 Games for Today: {datetime.date.today().strftime('%Y-%m-%d')}")
    game_date = datetime.date.today()

    # Fetch Games
    available_games = get_nba_games()

    if available_games:
        game_labels = [f"{game['home_team']} vs {game['away_team']}" for game in available_games]
        selected_game_label = st.selectbox("Select a Game:", game_labels, key="sgp_game")
        selected_game = next(g for g in available_games if f"{g['home_team']} vs {g['away_team']}" == selected_game_label)

        # Number of Props Selection
        num_props = st.slider("Number of Props (1-8):", 1, 8, 1, key="sgp_num_props")

        # Toggle for Filtering by Confidence or Odds Range
        filter_method = st.radio(
            "Filter by:", ["Confidence Score", "Odds Range"], horizontal=True, key="sgp_filter"
        )

        if filter_method == "Confidence Score":
            confidence_level = st.selectbox("Select Confidence Level:", ["High", "Medium", "Low"], key="sgp_confidence")
            min_odds, max_odds = None, None  # Ignore odds filtering

        elif filter_method == "Odds Range":
            min_odds, max_odds = st.slider("Set Odds Range:", min_value=-450, max_value=250, value=(-300, 100), key="sgp_odds")
            confidence_level = None  # Ignore confidence filtering

        # Generate SGP Prediction
        if st.button("Generate SGP Prediction"):
            sgp_result = fetch_sgp_builder(
                selected_game, num_props=num_props, min_odds=min_odds, max_odds=max_odds,
                confidence_level=confidence_level
            )
            st.write(sgp_result)

    else:
        st.warning("🚨 No NBA games found for the selected date.")
