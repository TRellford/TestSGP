import streamlit as st
from utils import get_available_games, get_player_props, calculate_parlay_odds

st.title("Same Game Parlay Builder")

# Game Selection
games = get_available_games()
game_options = {game['id']: game['name'] for game in games}
selected_game = st.selectbox("Select a Game", options=list(game_options.keys()), format_func=lambda x: game_options[x])

if selected_game:
    # Fetch Player Props
    props = get_player_props(selected_game)
    prop_options = {prop['id']: f"{prop['player']} - {prop['type']} ({prop['odds']})" for prop in props}
    selected_props = st.multiselect("Select Props (1-8)", options=list(prop_options.keys()), format_func=lambda x: prop_options[x])
    
    if selected_props:
        if len(selected_props) > 8:
            st.warning("You can select up to 8 props only.")
        else:
            # Calculate Final Parlay Odds
            selected_props_data = [prop for prop in props if prop['id'] in selected_props]
            final_odds = calculate_parlay_odds(selected_props_data)
            st.subheader(f"Final Parlay Odds: {final_odds}")
