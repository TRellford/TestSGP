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
use_odds_filter = st.sidebar.checkbox("Apply Odds Range Filter", value=False)
min_odds, max_odds = -1000, 1000  # Default: no filtering
if use_odds_filter:
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
        game_prop_data = []

        # Analyze Each Game and Select Top Props
        for selected_game in selected_games:
            available_props = fetch_props(selected_game['id'])

            if not available_props:
                st.warning(f"⚠️ No props available for {selected_game['display']}.")
                continue

            # Filter props by odds range if enabled
            filtered_props = available_props
            if use_odds_filter:
                filtered_props = {
                    prop: data for prop, data in available_props.items()
                    if min_odds <= data['odds'] <= max_odds
                }

            if not filtered_props:
                st.info(f"No props available for {selected_game['display']} within odds range {min_odds} to {max_odds}.")
                continue

            # Automatically select top N props based on confidence
            prop_confidence_list = []
            for prop in filtered_props.keys():
                prop_data = filtered_props[prop]
                player_name = prop.split()[0] + " " + prop.split()[1]  # Simplified parsing
                player_stats = get_player_stats(player_name)
                confidence_score = predict_prop_confidence(prop, prop_data['odds'], player_stats, selected_game)
                line_discrepancy = detect_line_discrepancies(prop_data['odds'], confidence_score)
                prop_confidence_list.append({
                    "prop": prop,
                    "confidence": confidence_score,
                    "odds": prop_data['odds'],
                    "risk_level": prop_data['risk_level'],
                    "line_discrepancy": "🔥" if line_discrepancy else ""
                })

            # Sort by confidence and select top N props
            prop_confidence_list = sorted(prop_confidence_list, key=lambda x: x['confidence'], reverse=True)
            game_selected_props = prop_confidence_list[:min(props_per_game, len(prop_confidence_list))]
            selected_props[selected_game['display']] = [item['prop'] for item in game_selected_props]
            total_props += len(game_selected_props)

            # Calculate combined odds for this game
            game_odds = [item['odds'] for item in game_selected_props]
            game_combined_odds = calculate_parlay_odds(game_odds) if game_odds else 0
            odds_list.extend(game_odds)

            # Store data for display
            game_prop_data.append({
                "game": selected_game,
                "props": game_selected_props,
                "combined_odds": game_combined_odds,
                "num_props": len(game_selected_props)
            })

        # Enforce Max 24 Props Across All Games
        if total_props > 24:
            st.error("⚠️ You can select a maximum of 24 total props across all games.")
        elif total_props > 0:
            # Display Suggested Props per Game in SGP Style
            for game_data in game_prop_data:
                game = game_data['game']
                props = game_data['props']
                combined_odds = game_data['combined_odds']
                num_props = game_data['num_props']

                st.markdown(f"**SGP {game['home_team']} @ {game['away_team']}** {american_odds_to_string(combined_odds)}")
                st.write(f"{num_props} SELECTIONS  6:10PM CT")  # Placeholder time
                for prop in props:
                    st.markdown(f"- {prop['prop']}")
                st.markdown("---")

            # Final SGP+ Summary
            final_odds = calculate_parlay_odds(odds_list)
            st.subheader("Final SGP+ Summary")
            st.write(f"**{total_props} Leg Same Game Parlay+** {american_odds_to_string(final_odds)}")
            st.write(f"Includes: {len(selected_games)} Games")

            # Wager and Payout Calculation
            wager = st.number_input("Wager ($)", min_value=0.0, value=10.0, step=0.5)
            if final_odds > 0:
                payout = wager * (final_odds / 100)
            else:
                payout = wager / (abs(final_odds) / 100)
            st.write(f"To Win: ${round(payout, 2)}")

            # Odds Movement Notification (Placeholder)
            st.info("Odds have changed for some of your selections")
            st.checkbox("Accept odds movement", value=False)

            # Sharp Money Insights
            st.subheader("Sharp Money Insights")
            sharp_money_data = get_sharp_money_insights(selected_props)
            st.table(sharp_money_data)
        else:
            st.info("No props available for the selected games.")
else:
    st.error("⚠️ No games available or issue fetching games. Please try again later.")
