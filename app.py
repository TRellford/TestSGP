import streamlit as st
import datetime
import pandas as pd
from utils import fetch_sgp_builder, get_nba_games

st.set_page_config(page_title="NBA Betting AI", layout="wide")

# Sidebar Navigation
st.sidebar.title("🔍 Navigation")
menu_option = st.sidebar.selectbox("Select a Section:", ["Same Game Parlay"])

# Same Game Parlay
if menu_option == "Same Game Parlay":
    st.header("🎯 Same Game Parlay (SGP) - One Game Only")

    # Display today's games
    st.subheader(f"📅 Games for Today: {datetime.date.today().strftime('%Y-%m-%d')}")
    available_games = get_nba_games()

    if available_games:
        game_labels = [f"{game['home_team']} vs {game['away_team']}" for game in available_games]
        selected_game_label = st.selectbox("Select a Game:", game_labels, key="sgp_game")
        selected_game = next(g for g in available_games if f"{g['home_team']} vs {g['away_team']}" == selected_game_label)

        # Number of props selection
        num_props = st.slider("Number of Props (1-8):", 1, 8, 3, key="sgp_num_props")

        # Toggle for Filtering Mode
        filter_mode = st.radio("Choose How to Select Props:", 
                               ["Auto-Select Best Props", "Filter by Confidence Score", "Filter by Odds Range"], 
                               key="filter_mode")

        # Define variables for filtering
        confidence_level = None
        min_odds, max_odds = None, None

        if filter_mode == "Filter by Confidence Score":
            confidence_levels = [
                ("🔥 High Confidence (80-100%)", 80, 100),
                ("⚡ Medium Confidence (60-79%)", 60, 79),
                ("⚠️ Low Confidence (40-59%)", 40, 59)
            ]
            conf_options = [level for level, _, _ in confidence_levels]
            conf_index = st.selectbox("Select Confidence Level:", conf_options, key="conf_level")
            selected_confidence = next((min_c, max_c) for lvl, min_c, max_c in confidence_levels if lvl == conf_index)
            confidence_level = selected_confidence

        elif filter_mode == "Filter by Odds Range":
            risk_levels = [
                ("🔵 Very Safe (-450 to -300)", -450, -300),
                ("🟢 Safe (-299 to -200)", -299, -200),
                ("🟡 Moderate Risk (-199 to +100)", -199, 100),
                ("🟠 High Risk (+101 to +250)", 101, 250),
                ("🔴 Very High Risk (+251 and above)", 251, float('inf'))
            ]
            risk_options = [level for level, _, _ in risk_levels]
            risk_index = st.selectbox("Select Risk Level:", risk_options, key="sgp_risk_level")
            selected_risk = next((min_o, max_o) for lvl, min_o, max_o in risk_levels if lvl == risk_index)
            min_odds, max_odds = selected_risk

        show_advanced = st.checkbox("Show Advanced Insights", value=False, key="adv_insights")

        if st.button("Generate SGP Prediction"):
            sgp_results = fetch_sgp_builder(
                selected_game,
                num_props=num_props,
                min_odds=min_odds if filter_mode == "Filter by Odds Range" else None,
                max_odds=max_odds if filter_mode == "Filter by Odds Range" else None,
                confidence_level=confidence_level if filter_mode == "Filter by Confidence Score" else None
            )

        if sgp_results and "selected_props" in sgp_results:
                selected_props = sgp_results["selected_props"]
    
        if not selected_props:
        st.warning("🚨 No valid props found for this game.")
            else:
        df = pd.DataFrame(selected_props)
        
        # Print column names for debugging
        st.write("🔍 **DEBUG: DataFrame Columns Before Renaming:**", df.columns.tolist())
        st.write(df.head())  # Show the first few rows for debugging

        column_mapping = {
            "player": "Player",
            "prop": "Prop",
            "odds": "Odds",
            "confidence_boost": "Confidence Score",
            "risk_level": "Risk Level",
            "insight": "Why This Pick?"
        }
        df.rename(columns=column_mapping, inplace=True)

        # Print new column names after renaming
        st.write("🔍 **DEBUG: DataFrame Columns After Renaming:**", df.columns.tolist())

        # Ensure required columns exist before selecting them
        required_columns = ["Player", "Prop", "Odds", "Confidence Score", "Risk Level", "Why This Pick?"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            st.error(f"🚨 Missing columns in data: {missing_columns}")
        else:
            df = df[required_columns]  # Select only the necessary columns

            st.write("### 🎯 **Same Game Parlay Selections**")
            st.dataframe(df, use_container_width=True)

            if "combined_odds" in sgp_results:
                st.subheader(f"📊 **Final Parlay Odds: {sgp_results['combined_odds']}**")
