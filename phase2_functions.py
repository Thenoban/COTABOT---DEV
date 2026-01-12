
# Historical Data Tracking and Trend Analysis Functions

def _save_to_history(self, period, deltas):
    """
    Save report data to history array for trend analysis.
    
    Args:
        period (str): "weekly" or "monthly"
        deltas (list): Player delta data from _calculate_deltas()
    """
    if not deltas:
        return
    
    report_db = self._get_report_db()
    
    # Initialize history structure
    if "history" not in report_db:
        report_db["history"] = {"weekly": [], "monthly": []}
    
    # Sort players by score
    top_players = sorted(deltas, key=lambda x: x.get('score', 0), reverse=True)
    top_10 = top_players[:10]
    
    # Find best performers
    best_kills = max(deltas, key=lambda x: x.get('kills', 0))
    best_kd = max(deltas, key=lambda x: x.get('kd', 0))
    
   # Calculate summary statistics
    total_active = len(deltas)
    avg_score = sum(d.get('score', 0) for d in deltas) / total_active if total_active > 0 else 0
    avg_kills = sum(d.get('kills', 0) for d in deltas) / total_active if total_active > 0 else 0
    
    now = datetime.datetime.now()
    
    # Create history entry
    history_entry = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "week_number": now.isocalendar()[1],
        "year": now.year,
        "summary": {
            "top_scorer": {
                "name": top_players[0]['name'],
                "score": top_players[0]['score']
            } if top_players else {},
            "most_kills": {
                "name": best_kills['name'],
                "kills": best_kills['kills']
            } if best_kills else {},
            "best_kd": {
                "name": best_kd['name'],
                "kd": best_kd['kd']
            } if best_kd else {},
            "total_active": total_active,
            "avg_score": round(avg_score, 2),
            "avg_kills": round(avg_kills, 2)
        },
        "top_10": [
            {
                "name": p['name'],
                "score": p.get('score', 0),
                "kills": p.get('kills', 0),
                "deaths": p.get('deaths', 0),
                "kd": p.get('kd', 0)
            } for p in top_10
        ]
    }
    
    # Add to history
    report_db["history"][period].append(history_entry)
    
    # Auto-prune old entries
    max_items = 52 if period == "weekly" else 12
    if len(report_db["history"][period]) > max_items:
        report_db["history"][period] = report_db["history"][period][-max_items:]
        logger.info(f"Pruned {period} history to last {max_items} entries")
    
    self._save_report_db(report_db)
    logger.info(f"Saved {period} report to history: {total_active} active players, avg score: {avg_score:.0f}")


def _analyze_trends(self, period="weekly", count=4):
    """
    Analyze performance trends over recent periods.
    
    Args:
        period (str): "weekly" or "monthly"
        count (int): Number of recent periods to analyze
    
    Returns:
        dict: Trend analysis results or None if insufficient data
    """
    report_db = self._get_report_db()
    history = report_db.get("history", {}).get(period, [])
    
    if len(history) < 2:
        logger.debug(f"Insufficient history for trend analysis: {len(history)} entries")
        return None
    
    # Get last N periods
    recent = history[-min(count, len(history)):]
    
    # Extract metrics
    avg_scores = [h["summary"]["avg_score"] for h in recent]
    total_actives = [h["summary"]["total_active"] for h in recent]
    
    # Trend detection (simple comparison)
    if len(avg_scores) >= 3:
        first_avg = sum(avg_scores[:2]) / 2  # Average of first 2
        last_avg = sum(avg_scores[-2:]) / 2  # Average of last 2
        
        if last_avg > first_avg * 1.1:
            activity_trend = "increasing"
        elif last_avg < first_avg * 0.9:
            activity_trend = "decreasing"
        else:
            activity_trend = "stable"
    else:
        activity_trend = "stable"
    
    # Score change (last vs previous)
    avg_score_change = avg_scores[-1] - avg_scores[-2] if len(avg_scores) >= 2 else 0
    
    # Most consistent player (appears in top 10 most frequently)
    player_appearances = {}
    for h in recent:
        for p in h.get("top_10", []):
            name = p["name"]
            player_appearances[name] = player_appearances.get(name, 0) + 1
    
    most_consistent = max(player_appearances.items(), key=lambda x: x[1])[0] if player_appearances else None
    consistency_count = player_appearances.get(most_consistent, 0) if most_consistent else 0
    
    return {
        "activity_trend": activity_trend,
        "avg_score_change": round(avg_score_change, 2),
        "most_consistent": most_consistent,
        "consistency_count": consistency_count,
        "weekly_averages": avg_scores,
        "active_counts": total_actives,
        "period_count": len(recent),
        "first_date": recent[0]["date"],
        "last_date": recent[-1]["date"]
    }
