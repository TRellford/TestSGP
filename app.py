import streamlit as st
from utils import (
    fetch_games, fetch_odds_api_events, fetch_props, calculate_parlay_odds, get_sharp_money_insights,
    get_player_stats, predict_prop_confidence, detect_line_discrepancies, american_odds_to_string, get_current_season_year
)
from datetime import date

# Streamlit UI Setup
st.set_page_config(page_title="SGP+ Builder", layout="wide")
st.title("Same Game Parlay Plus (SGP+)")

# Automatically use today's date and current season
current_date = date.today()
current_season_year = get_current_season_year()

# Sidebar for Odds Filtering, Props Selection, and Prop Type Filter
st.sidebar.subheader("Odds Filter")
use_odds_filter = st.sidebar.checkbox("Apply Odds Range Filter", value=False)
min_odds, max_odds = -1000, 1000  # Default: no filtering
if use_odds_filter:
    min_odds = st.sidebar.number_input("Min Odds", min_value=-1000, max_value=1000, value=-350, step=10)
    max_odds = st.sidebar.number_input("Max Odds", min_value=-1000, max_value=1000, value=200, step=10)

st.sidebar.subheader("Props per Game")
props_per_game = st.sidebar.number_input(
    "Number of Props per Game", min_value=1, max_value=8, value=3, step=1,
    help="Select how many props to include per game (1-8)."
)

# Prop Type Selection with Checkboxes
st.sidebar.subheader("Prop Types to Analyze")
all_selected = st.sidebar.checkbox("Select All Prop Types", value=True, key="select_all")
prop_types = []
if all_selected:
    prop_types = ["points", "rebounds", "assists", "steals", "blocks"]
else:
    if st.sidebar.checkbox("Points", value=False, key="points"):
        prop_types.append("points")
    if st.sidebar.checkbox("Rebounds", value=False, key="rebounds"):
        prop_types.append("rebounds")
    if st.sidebar.checkbox("Assists", value=False, key="assists"):
        prop_types.append("assists")
    if st.sidebar.checkbox("Steals", value=False, key="steals"):
        prop_types.append("steals")
    if st.sidebar.checkbox("Blocks", value=False, key="blocks"):
        prop_types.append("blocks")

# Validate Prop Type Selection
if not prop_types:
    st.sidebar.error("⚠️ Please select at least one prop type to analyze.")
    st.stop()

st.sidebar.write(f"Selected prop types: {', '.join(prop_types)}")

# Fetch Games from balldontlie API for today
games = fetch_games(current_date)

if not games:
    st.info("No NBA games scheduled for today.")
else:
    # Fetch Events from The Odds API for today
    odds_api_events = fetch_odds_api_events(current_date)
    
    if not odds_api_events:
        st.info("No odds available for today's NBA games yet.")
    else:
        # Map balldontlie games to The Odds API events
        mapped_games = []
        for game in games:
            game_display = game["display"]
            home_team = game["home_team"]
            away_team = game["away_team"]
            matching_event = next(
                (event for event in odds_api_events if event["home_team"] == home_team and event["away_team"] == away_team),
                None
            )
            if matching_event:
                game["odds_api_event_id"] = matching_event["id"]
                mapped_games.append(game)
            else:
                st.warning(f"⚠️ No matching event found in The Odds API for {game_display}.")
        
        if not mapped_games:
            st.info("No matching events found in The Odds API for today's games.")
        else:
            game_displays = [game["display"] for game in mapped_games]
            selected_displays = st.multiselect(
                "Select 2-12 Games",
                game_displays,
                default=None,
                help="Choose between 2 and 12 NBA games.",
                max_selections=12
            )
            selected_games = [game for game in mapped_games if game["display"] in selected_displays]

            if len(selected_games) < 2:
                st.warning("⚠️ Please select at least 2 games to build an SGP+.")
            else:
                total_props = 0
                selected_props = {}
                odds_list = []
                game_prop_data = []

                # Analyze Each Game and Select Top Props
                for selected_game in selected_games:
                    available_props = fetch_props(selected_game['odds_api_event_id'], prop_types)
                    if not available_props:
                        st.warning(f"⚠️ No props available for {selected_game['display']}. Check API key, rate limits, or game availability.")
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

                    # Calculate confidence for each prop
                    prop_confidence_list = []
                    for prop, prop_data in filtered_props.items():
                        player_name = prop.split()[0] + " " + prop.split()[1]  # e.g., "Tim Hardaway"
                        player_stats = get_player_stats(player_name, current_season_year)
                        confidence_score = predict_prop_confidence(prop, prop_data, player_stats, selected_game)
                        line_discrepancy = detect_line_discrepancies(prop_data['odds'], confidence_score)
                        prop_confidence_list.append({
                            "prop": prop,
                            "confidence": confidence_score,
                            "odds": prop_data['odds'],
                            "risk_level": prop_data['risk_level'],
                            "line_discrepancy": "🔥" if line_discrepancy else "",
                            "player_stat_key": f"{player_name}_{prop_data['prop_type']}"  # e.g., "Tim Hardaway_points"
                        })

                    # Sort by confidence
                    prop_confidence_list = sorted(prop_confidence_list, key=lambda x: x['confidence'], reverse=True)

                    # Select top N props while avoiding conflicts (e.g., Over and Under for the same player stat)
                    selected_prop_keys = set()  # Track selected player_stat combinations
                    game_selected_props = []
                    for prop_item in prop_confidence_list:
                        player_stat_key = prop_item['player_stat_key']
                        if player_stat_key not in selected_prop_keys and len(game_selected_props) < props_per_game:
                            selected_prop_keys.add(player_stat_key)
                            game_selected_props.append(prop_item)

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
