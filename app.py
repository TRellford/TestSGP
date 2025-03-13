import streamlit as st
from utils import (
    fetch_games, fetch_odds_api_events, fetch_props, calculate_parlay_odds, get_sharp_money_insights,
    get_player_stats, predict_prop_confidence, detect_line_discrepancies, american_odds_to_string
)
from datetime import date, datetime

# Automatically determine the current season
current_year = datetime.now().year
current_month = datetime.now().month
SEASON = current_year if current_month >= 10 else current_year - 1  # NBA season starts in October

def get_current_date():
    return date.today()

# Streamlit UI Setup
st.set_page_config(page_title="SGP+ Builder", layout="wide")
st.title("Same Game Parlay Plus (SGP+)")

# Fetch today's date automatically
selected_date = get_current_date()

# Fetch Games from balldontlie API
games = fetch_games(selected_date)

# Fetch Events from The Odds API to map game IDs
odds_api_events = fetch_odds_api_events(selected_date)

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

if mapped_games:
    game_displays = [game["display"] for game in mapped_games]
    selected_displays = st.multiselect(
        "Select 2-12 Games",
        game_displays,
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

        for selected_game in selected_games:
            available_props = fetch_props(selected_game['odds_api_event_id'])

            if not available_props:
                st.warning(f"⚠️ No props available for {selected_game['display']}.")
                continue

            prop_confidence_list = []
            for prop in available_props.keys():
                prop_data = available_props[prop]
                player_name = " ".join(prop.split()[:2])
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

            prop_confidence_list = sorted(prop_confidence_list, key=lambda x: x['confidence'], reverse=True)
            game_selected_props = prop_confidence_list[:min(3, len(prop_confidence_list))]
            selected_props[selected_game['display']] = [item['prop'] for item in game_selected_props]
            total_props += len(game_selected_props)

            game_odds = [item['odds'] for item in game_selected_props]
            game_combined_odds = calculate_parlay_odds(game_odds) if game_odds else 0
            odds_list.extend(game_odds)

            game_prop_data.append({
                "game": selected_game,
                "props": game_selected_props,
                "combined_odds": game_combined_odds,
                "num_props": len(game_selected_props)
            })

        if total_props > 24:
            st.error("⚠️ You can select a maximum of 24 total props across all games.")
        elif total_props > 0:
            for game_data in game_prop_data:
                game = game_data['game']
                props = game_data['props']
                combined_odds = game_data['combined_odds']
                num_props = game_data['num_props']

                st.markdown(f"**SGP {game['home_team']} @ {game['away_team']}** {american_odds_to_string(combined_odds)}")
                st.write(f"{num_props} SELECTIONS")
                for prop in props:
                    st.markdown(f"- {prop['prop']}")
                st.markdown("---")

            final_odds = calculate_parlay_odds(odds_list)
            st.subheader("Final SGP+ Summary")
            st.write(f"**{total_props} Leg Same Game Parlay+** {american_odds_to_string(final_odds)}")
            st.write(f"Includes: {len(selected_games)} Games")

            wager = st.number_input("Wager ($)", min_value=0.0, value=10.0, step=0.5)
            payout = wager * (final_odds / 100) if final_odds > 0 else wager / (abs(final_odds) / 100)
            st.write(f"To Win: ${round(payout, 2)}")

            st.subheader("Sharp Money Insights")
            sharp_money_data = get_sharp_money_insights(selected_props)
            st.table(sharp_money_data)
        else:
            st.info("No props available for the selected games.")
else:
    st.error("⚠️ No games available or issue fetching games. Please try again later.")
