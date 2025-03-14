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
            # Confidence Level Selection
            confidence_levels = [
                ("High Confidence (80-100%)", "🔥", 80, 100),
                ("Medium Confidence (60-79%)", "⚡", 60, 79),
                ("Low Confidence (40-59%)", "⚠️", 40, 59)
            ]
            conf_options = [f"{level} {emoji}" for level, emoji, _, _ in confidence_levels]
            conf_index = st.selectbox("Select Confidence Level:", conf_options, key="conf_level")
            selected_confidence = next(((lvl, emj, min_c, max_c) for lvl, emj, min_c, max_c in confidence_levels if f"{lvl} {emj}" == conf_index), confidence_levels[0])
            confidence_level = selected_confidence[0]

        elif filter_mode == "Filter by Odds Range":
            # Risk level selection with odds range
            risk_levels = [
                ("🔵 Very Safe (-450 to -300)", "🔵", (-450, -300)),
                ("🟢 Safe (-299 to -200)", "🟢", (-299, -200)),
                ("🟡 Moderate Risk (-199 to +100)", "🟡", (-199, 100)),
                ("🟠 High Risk (+101 to +250)", "🟠", (101, 250)),
                ("🔴 Very High Risk (+251 and above)", "🔴", (251, float('inf')))
            ]
            risk_options = [f"{level}" for level, _, _ in risk_levels]
            risk_index = st.selectbox("Select Risk Level:", risk_options, key="sgp_risk_level")
            selected_risk = next(((r, c, o) for r, c, o in risk_levels if f"{r}" == risk_index), risk_levels[0])
            risk_level, color, (min_odds, max_odds) = selected_risk

        # Advanced insights toggle
        show_advanced = st.checkbox("Show Advanced Insights", value=False, key="adv_insights")

        if st.button("Generate SGP Prediction"):
            st.write("🔄 Fetching Same Game Parlay (SGP) Predictions...")

    try:
        # Fetch SGP results
        sgp_results = fetch_sgp_builder(
            selected_game,
            num_props=num_props,
            min_odds=min_odds if filter_mode == "Filter by Odds Range" else None,
            max_odds=max_odds if filter_mode == "Filter by Odds Range" else None,
            confidence_level=confidence_level if filter_mode == "Filter by Confidence Score" else None
        )

        if not sgp_results:
            st.error("🚨 No data returned from `fetch_sgp_builder()`. Please check your API response.")
            
        elif "selected_props" not in sgp_results or not sgp_results["selected_props"]:
            st.warning("🚨 No valid props found for this game.")
        
        else:
            selected_props = sgp_results["selected_props"]
            df = pd.DataFrame(selected_props)

            # Debugging: Print column names
            st.write("🔍 **DEBUG:** Column Names in Fetched Data:", df.columns.tolist())

            # Column mapping
            column_mapping = {
                "player": "Player",
                "prop": "Prop",
                "odds": "Odds",
                "confidence_boost": "Confidence Score",
                "risk_level": "Risk Level",
                "insight": "Why This Pick?"  
        }

        df.rename(columns=column_mapping, inplace=True)

        missing_columns = [col for col in column_mapping.values() if col not in df.columns]

        if missing_columns:
            st.error(f"🚨 Missing columns in data: {missing_columns}")
            st.write("🔍 **DEBUG:** Full DataFrame", df)
        else:
            # Add AI Pick Label
            df["AI Pick"] = "🔥 AI-Selected" if filter_mode == "Auto-Select Best Props" else "User Picked"

            # Display basic vs. advanced view
            if not show_advanced:
                df = df[["Player", "Prop", "Odds", "Confidence Score", "Risk Level", "Why This Pick?"]]
            else:
                df["Betting Edge"] = df["Betting Edge"].apply(lambda x: f"{x:.1f}%" if x > 0 else f"{x:.1f}% (Sharp Line)")
                df = df[["Player", "Prop", "Odds", "Confidence Score", "Risk Level", "Why This Pick?", "Betting Edge", "AI Pick"]]

            # Display table
            st.write("### 🎯 **Same Game Parlay Selections**")
            st.dataframe(df, use_container_width=True)

            # Display Final Parlay Odds
            if "combined_odds" in sgp_results:
                st.subheader(f"📊 **Final Parlay Odds: {sgp_results['combined_odds']}**")

    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
