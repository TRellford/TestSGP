import streamlit as st
from utils import (
    fetch_games, fetch_props, calculate_parlay_odds, get_sharp_money_insights,
    get_player_stats, predict_prop_confidence, detect_line_discrepancies, american_odds_to_string
)
from datetime import date

# Streamlit UI Setup
st.set_page_config(page_title="SGP+ Builder", layout="wide")
st.title("Same Game Parlay Plus (SGP+)")

# Sidebar for Odds Filtering and Prop Suggestions
st.sidebar.subheader("Odds Filter")
min_odds = st.sidebar.number_input("Min Odds", min_value=-1000, max_value=1000, value=-350, step=10)
max_odds = st.sidebar.number_input("Max Odds", min_value=-1000, max_value=1000, value=200, step=10)

st.sidebar.subheader("Prop Suggestions")
props_per_game = st.sidebar.number_input(
    "Number of Props Suggested per Game", min_value=1, max_value=8, value=3, step=1,
    help="Select how many props to suggest per game (1-8)."
)

# Fetch and Display Games using balldontlie API
games = fetch_games(date.today())

if games and "display" in games[0]:
    game_displays = [game["display"] for game in games]
    selected_displays = st.multiselect(
        "Select 2-12 Games",
        game_displays,
        default=None,
        help="Choose between 2 and 12 NBA games.",
        max_selections=12
    )
    selected_games = [game for game in games if game["display"] in selected_displays]

    if len(selected_games) < 2:
        st.warning("⚠️ Please select at least 2 games to build an SGP+.")
    else:
        total_props = 0
        selected_props = {}
        odds_list = []
        prop_confidence_data = []

        # Prop Selection for Each Game
        for selected_game in selected_games:
            with st.expander(f"{selected_game['display']} Props", expanded=False):
                available_props = fetch_props(selected_game['id'])

                if not available_props:
                    st.warning(f"⚠️ No props available for {selected_game['display']}.")
                    continue

                # Filter props by odds range
                filtered_props = {
                    prop: data for prop, data in available_props.items()
                    if min_odds <= data['odds'] <= max_odds
                }

                if not filtered_props:
                    st.info(f"No props available for {selected_game['display']} within odds range {min_odds} to {max_odds}.")
                    continue

                # Select Props (Max 8 per game)
                selected_props[selected_game['display']] = st.multiselect(
                    f"Select Props for {selected_game['display']} (1-8)",
                    list(filtered_props.keys()),
                    default=None,
                    max_selections=8,
                    help="Choose up to 8 props per game."
                )
                total_props += len(selected_props[selected_game['display']])

                # Display Props Table with Confidence Scores and Risk Levels
                if selected_props[selected_game['display']]:
                    selected_data = []
                    game_prop_confidence = []
                    for prop in filtered_props.keys():
                        prop_data = filtered_props[prop]
                        # Fetch player stats and predict confidence
                        player_name = prop.split()[0] + " " + prop.split()[1]  # Simplified parsing
                        player_stats = get_player_stats(player_name)
                        confidence_score = predict_prop_confidence(prop, prop_data['odds'], player_stats, selected_game)
                        line_discrepancy = detect_line_discrepancies(prop_data['odds'], confidence_score)
                        prop_entry = {
                            "Prop": prop,
                            "Odds": american_odds_to_string(prop_data['odds']),
                            "Confidence": confidence_score,
                            "Risk Level": prop_data['risk_level'],
                            "Line Discrepancy": "🔥" if line_discrepancy else ""
                        }
                        if prop in selected_props[selected_game['display']]:
                            selected_data.append(prop_entry)
                        game_prop_confidence.append({
                            "prop": prop,
                            "confidence": confidence_score,
                            "odds": prop_data['odds']
                        })
                    st.table(selected_data)
                    odds_list.extend([filtered_props[prop]['odds'] for prop in selected_props[selected_game['display']]])

                    # Store prop confidence data for suggestions
                    prop_confidence_data.append({
                        "game": selected_game['display'],
                        "props": game_prop_confidence
                    })

        # Enforce Max 24 Props Across All Games
        if total_props > 24:
            st.error("⚠️ You can select a maximum of 24 total props across all games.")
        elif total_props > 0:
            # Final Parlay Odds Calculation
            final_odds = calculate_parlay_odds(odds_list)
            st.subheader("Final SGP+ Summary")
            st.write(f"**Total Props Selected**: {total_props}")
            st.write(f"**Combined Parlay Odds**: {american_odds_to_string(final_odds)}")

            # Auto-Generated Parlay Suggestions
            st.subheader("Auto-Generated Parlay Suggestions")
            suggested_props = []
            total_suggested = 0
            for game_data in prop_confidence_data:
                game_props = sorted(game_data['props'], key=lambda x: x['confidence'], reverse=True)
                game_suggestions = game_props[:min(props_per_game, len(game_props))]
                for suggestion in game_suggestions:
                    if total_suggested < 24:  # Respect overall limit
                        suggested_props.append({
                            "Game": game_data['game'],
                            "Prop": suggestion['prop'],
                            "Odds": american_odds_to_string(suggestion['odds']),
                            "Confidence": suggestion['confidence']
                        })
                        total_suggested += 1
            if suggested_props:
                st.table(suggested_props)
            else:
                st.info("No suggestions available.")

            # Sharp Money Insights
            st.subheader("Sharp Money Insights")
            sharp_money_data = get_sharp_money_insights(selected_props)
            st.table(sharp_money_data)
        else:
            st.info("Please select at least one prop to see the parlay odds.")
else:
    st.error("⚠️ No games available or issue fetching games. Please try again later.")
