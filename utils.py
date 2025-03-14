Skip to content
Navigation Menu
TRellford
TestSGP

Type / to search
Code
Issues
Pull requests
Actions
Projects
Wiki
Security
Insights
Settings
Commit fc78bc1
TRellford
TRellford
authored
25 minutes ago
Verified
Update utils.py
main
1 parent 
05b47e3
 commit 
fc78bc1
File tree
Filter files…
utils.py
1 file changed
+34
-93
lines changed
Search within code
 
‎utils.py
+34
-93
Original file line number	Diff line number	Diff line change
@@ -71,109 +71,50 @@ def get_event_id(selected_game):

# Fetch Player Props for a Given Game (with Debugging Logs)
def fetch_sgp_builder(selected_game, num_props=1, min_odds=None, max_odds=None, confidence_level=None):
    """Fetch player props for a Same Game Parlay (SGP), including standard and alternate lines for all categories."""
    event_id = get_event_id(selected_game)
    if not event_id:
        return "🚨 No event ID found for this game. Cannot fetch props."
    try:
        response = requests.get(
            EVENT_ODDS_API_URL.format(event_id=event_id),
            params={
                "apiKey": st.secrets["odds_api_key"],
                "regions": "us",
                "markets": ",".join([
                    "player_points", "player_rebounds", "player_assists", "player_threes",  # Standard Props
                    "player_points_alternate", "player_rebounds_alternate", "player_assists_alternate",  # Alt Props
                    "player_threes_alternate"  # Alternate 3PTM Props
                ]),
                "bookmakers": "fanduel"
            }
        )
        props = fetch_best_props(selected_game, min_odds, max_odds, confidence_level)

        if response.status_code != 200:
            st.error(f"❌ Error fetching props: {response.status_code} - {response.text}")
            return []
        if not props:
            return {"selected_props": [], "combined_odds": None}
        props = sorted(props, key=lambda x: x["confidence_boost"], reverse=True)
        selected_props = props[:num_props]

        odds_data = response.json()
        best_props = []
        fanduel = next((b for b in odds_data.get("bookmakers", []) if b["key"] == "fanduel"), None)
        if not fanduel:
            return "🚨 No FanDuel odds available for this game."
        for market in fanduel.get("markets", []):
            for outcome in market.get("outcomes", []):
                price = outcome["price"]
                # Extract actual player name (FanDuel sometimes stores "Over" in outcome["name"])
                player_name = outcome["description"].split(" Over")[0] if " Over" in outcome["description"] else outcome["description"].split(" Under")[0]
                # Format prop type correctly
                prop_mappings = {
                "points_alternate": "Alternate Points",
                "rebounds_alternate": "Alternate Rebounds",
                "assists_alternate": "Alternate Assists",
                "threes_alternate": "Alternate Threes",
                "three_pointers_made": "3PT Made"
}
                prop_type = prop_mappings.get(market["key"], market["key"].replace("_", " ").title())
                # Identify if it's an alternative line
                is_alt = "alternate" in market["key"]
                # Convert sportsbook odds to implied probability
                sportsbook_implied_prob = 1 / (1 + (price / 100 if price > 0 else 100 / abs(price)))
                # AI Model Probabilities (Placeholder)
                ai_probability = 0.65  # This should be dynamically computed using our models
                # Betting edge calculation
                betting_edge = (ai_probability - sportsbook_implied_prob) / sportsbook_implied_prob if sportsbook_implied_prob > 0 else 0
                confidence_boost = min(max(betting_edge * 50 + 50, 0), 100)
                # Filter by Confidence Score
                if confidence_level:
                    confidence_mapping = {"High": 80, "Medium": 60, "Low": 40}
                    if confidence_boost < confidence_mapping[confidence_level]:
                        continue
                # Filter by Odds Range
                if min_odds is not None and max_odds is not None:
                    if not (min_odds <= price <= max_odds):
                        continue
                best_props.append({
                    "player": player_name,
                    "prop": prop_type,
                    "odds": price,
                    "implied_prob": sportsbook_implied_prob,
                    "ai_prob": ai_probability,
                    "confidence_boost": confidence_boost,
                    "betting_edge": betting_edge,
                    "alt_line": is_alt  # Flag if it's an alternative line
                })
        if not best_props:
            return "🚨 No valid props found for this game. (DEBUG: No props met the filter criteria)"
        # Sort by confidence and select top N props
        selected_props = sorted(best_props, key=lambda x: x["confidence_boost"], reverse=True)[:num_props]
        # Calculate Combined Odds
        combined_odds = 1.0
        for prop in selected_props:
            decimal_odds = (prop["odds"] / 100 + 1) if prop["odds"] > 0 else (1 + 100 / abs(prop["odds"]))
            odds = prop["odds"]
            decimal_odds = (odds / 100 + 1) if odds > 0 else (1 + 100 / abs(odds))
            combined_odds *= decimal_odds

        american_odds = int((combined_odds - 1) * 100) if combined_odds > 2 else int(-100 / (combined_odds - 1))
        combined_american_odds = int((combined_odds - 1) * 100) if combined_odds > 2 else int(-100 / (combined_odds - 1))
        for prop in selected_props:
            prop["Risk Level"], prop["Risk Emoji"] = get_risk_level(prop["odds"])
            prop["Why This Pick?"] = generate_insight(prop)

        return {
            "selected_props": selected_props,
            "combined_odds": american_odds
            "combined_odds": combined_american_odds
        }

    except Exception as e:
        st.error(f"❌ Unexpected error fetching SGP props: {e}")
        return []
        print(f"❌ Error in fetch_sgp_builder: {str(e)}")
        return {"selected_props": [], "combined_odds": None}
def get_risk_level(odds):
    if -450 <= odds <= -300:
        return "🔵 Very Safe", "🔵"
    elif -299 <= odds <= -200:
        return "🟢 Safe", "🟢"
    elif -199 <= odds <= 100:
        return "🟡 Moderate", "🟡"
    elif 101 <= odds <= 250:
        return "🟠 High Risk", "🟠"
    else:
        return "🔴 Very High Risk", "🔴"
def generate_insight(prop):
    return (
        f"{prop['player']} has hit {prop['prop']} in {round(prop['confidence_boost'], 1)}% of recent games. "
        f"Odds: {prop['odds']}. AI suggests a {prop['Risk Level']} play."
    )
0 commit comments
Comments
0
 (0)
Comment
You're receiving notifications because you're subscribed to this thread.

Update utils.py · TRellford/TestSGP@fc78bc1
