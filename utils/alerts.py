"""
Feature 17: Real-Time Alerts.
Checks recent CHIRPS rainfall against return period thresholds.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages flood risk alerts based on recent rainfall data."""

    ALERT_LEVELS = {
        "NORMAL": {"color": "#1a9850", "icon": "✓", "priority": 0},
        "WATCH": {"color": "#ffffbf", "icon": "⚠", "priority": 1},
        "WARNING": {"color": "#fc8d59", "icon": "⚠", "priority": 2},
        "SEVERE": {"color": "#d73027", "icon": "🔴", "priority": 3},
        "EXTREME": {"color": "#67001f", "icon": "🔴", "priority": 4},
    }

    def __init__(self):
        self.alerts = []

    def check_rainfall_alert(self, aoi_json, rp_data=None):
        """
        Check recent 7-day rainfall against thresholds.

        Returns alert dict with level, message, and metadata.
        """
        from gee_functions.chirps import get_chirps_series

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

        try:
            rain_df = get_chirps_series(aoi_json, start_date, end_date)
        except Exception:
            return {"level": "NORMAL", "message": "Unable to fetch recent rainfall data."}

        if rain_df is None or rain_df.empty:
            return {"level": "NORMAL", "message": "No recent rainfall data available."}

        recent_7d = rain_df.tail(7)["rainfall_mm"].sum()
        recent_3d = rain_df.tail(3)["rainfall_mm"].sum()
        daily_peak = rain_df.tail(7)["rainfall_mm"].max()

        # Determine alert level
        if rp_data and rp_data.get("return_periods"):
            rp = rp_data["return_periods"]
            daily_rate = recent_7d / 7
            projected_monsoon = daily_rate * 150

            if projected_monsoon >= rp.get(100, float("inf")):
                level = "EXTREME"
            elif projected_monsoon >= rp.get(25, float("inf")):
                level = "SEVERE"
            elif projected_monsoon >= rp.get(10, float("inf")):
                level = "WARNING"
            elif projected_monsoon >= rp.get(5, float("inf")):
                level = "WATCH"
            else:
                level = "NORMAL"
        else:
            # Fallback: absolute thresholds
            if daily_peak > 100:
                level = "SEVERE"
            elif daily_peak > 60 or recent_3d > 150:
                level = "WARNING"
            elif daily_peak > 30 or recent_7d > 200:
                level = "WATCH"
            else:
                level = "NORMAL"

        alert = {
            "level": level,
            "recent_7d_mm": round(recent_7d, 1),
            "recent_3d_mm": round(recent_3d, 1),
            "daily_peak_mm": round(daily_peak, 1),
            "message": self._format_message(level, recent_7d, daily_peak),
            **self.ALERT_LEVELS[level],
        }

        self.alerts.append(alert)
        return alert

    def _format_message(self, level, rain_7d, peak):
        messages = {
            "NORMAL": f"Normal conditions. 7-day rain: {rain_7d:.0f}mm.",
            "WATCH": f"Elevated rainfall detected. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.",
            "WARNING": f"Heavy rainfall warning. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.",
            "SEVERE": f"Severe flood risk. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.",
            "EXTREME": f"Extreme flood risk. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.",
        }
        return messages.get(level, "")

    def render_alert_banner(self, alert):
        """Log an alert banner."""
        if alert["level"] == "NORMAL":
            return

        msg = f"FLOOD ALERT: {alert['level']} - {alert['message']}"
        if alert["level"] in ("EXTREME", "SEVERE"):
            logger.error(msg)
        elif alert["level"] == "WARNING":
            logger.warning(msg)
        else:
            logger.info(msg)
