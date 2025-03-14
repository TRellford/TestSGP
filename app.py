import streamlit as st
import datetime
import pandas as pd
from utils import (
    fetch_sgp_builder, get_nba_games
)

st.set_page_config(page_title="NBA Betting AI", layout="wide")

# Sidebar Navigation
st.sidebar.title("🔍 Navigation")
menu_option = st.sidebar.selectbox("Select a Section:", ["Same Game Parlay"])

# Same Game Parlay
if menu_option == "Same Game Parlay":
    st.header("🎯 Same Game Parlay (SGP) - One Game Only")

    # Display today's games (removing "Tomorrow's Games")
    st.subheader(f"📅 Games for Today: {datetime.date.today().strftime('%Y-%m-%d')}")
    available_games = get_nba_games()

    if available_games:
        game_labels = [f"{game['home_team']} vs {game['away_team']}" for game in available_games]
        selected_game_label = st.selectbox("Select a Game:", game_labels, key="sgp_game")
        selected_game = next(g for g in available_games if f"{g['home_team']} vs {g['away_team']}" == selected_game_label)

        # Number of props selection
        num_props = st.slider("Number of Props (1-8):", 1, 8, 3, key="sgp_num_props")

        # Risk level selection with colors
        risk_levels = [
            ("Very Safe", "🔵", (-450, -300)),
            ("Safe", "🟢", (-299, -200)),
            ("Moderate Risk", "🟡", (-199, +100)),
            ("High Risk", "🟠", (+101, +250)),
            ("Very High Risk", "🔴", (+251, float('inf')))
        ]
        risk_options = [f"{level} :large_{color}_circle:" for level, color, _ in risk_levels]
        risk_index = st.selectbox("Select Risk Level:", risk_options, key="sgp_risk_level")
        selected_risk = next(((r, c, o) for r, c, o in risk_levels if f"{r} :large_{c}_circle:" == risk_index), risk_levels[0])
        risk_level, color, (min_odds, max_odds) = selected_risk  # Correct unpacking        risk_level, color, (min_odds, max_odds) = selected_risk

        # Toggle: Choose Between Confidence Score or Odds Range
        filter_type = st.radio("Filter by:", ["Confidence Score", "Odds Range"], key="filter_type")

        confidence_level = None
        if filter_type == "Confidence Score":
            confidence_level = st.selectbox("Select Confidence Level:", ["High", "Medium", "Low"])

        if st.button("Generate SGP Prediction"):
            # Fetch SGP results
            sgp_results = fetch_sgp_builder(
                selected_game,
                num_props=num_props,
                min_odds=min_odds if filter_type == "Odds Range" else None,
                max_odds=max_odds if filter_type == "Odds Range" else None,
                confidence_level=confidence_level if filter_type == "Confidence Score" else None
            )

            # Display Results in a Table
            if sgp_results and isinstance(sgp_results, dict) and "selected_props" in sgp_results:
                selected_props = sgp_results["selected_props"]
                
                if selected_props:
                    # Convert to DataFrame for easy display
                    df = pd.DataFrame(selected_props)

                    # Rename columns for clarity
                    df.rename(columns={
                        "player": "Player",
                        "prop": "Prop",
                        "alt_line": "Alt Line?",
                        "odds": "Odds",
                        "confidence_boost": "Confidence Score",
                        "betting_edge": "Betting Edge"
                    }, inplace=True)

                    # Adjust formatting
                    df["Confidence Score"] = df["Confidence Score"].apply(lambda x: f"{x:.1f}%")
                    df["Betting Edge"] = df["Betting Edge"].apply(lambda x: f"{x:.1f}%" if x > 0 else f"{x:.1f}% (Sharp Line)")

                    # Display table in Streamlit
                    st.write("### 🎯 **Same Game Parlay Selections**")
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("🚨 No valid player props found for this game.")

            # Show Final Parlay Odds
            if "combined_odds" in sgp_results:
                st.subheader(f"📊 **Final Parlay Odds: {sgp_results['combined_odds']}**")

    else:
        st.warning("🚨 No NBA games found for today.")
