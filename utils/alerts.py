"""
Feature 17: Real-Time Alerts.
Checks recent CHIRPS rainfall against return period thresholds.
"""

import streamlit as st
from datetime import datetime, timedelta


class AlertManager:
    """Manages flood risk alerts based on recent rainfall data."""

    ALERT_LEVELS = {
        'NORMAL': {'color': '#1a9850', 'icon': '✓', 'priority': 0},
        'WATCH': {'color': '#ffffbf', 'icon': '⚠', 'priority': 1},
        'WARNING': {'color': '#fc8d59', 'icon': '⚠', 'priority': 2},
        'SEVERE': {'color': '#d73027', 'icon': '🔴', 'priority': 3},
        'EXTREME': {'color': '#67001f', 'icon': '🔴', 'priority': 4},
    }

    def __init__(self):
        self.alerts = []

    def check_rainfall_alert(self, aoi_json, rp_data=None):
        """
        Check recent 7-day rainfall against thresholds.

        Returns alert dict with level, message, and metadata.
        """
        from gee_functions.chirps import get_chirps_series

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

        try:
            rain_df = get_chirps_series(aoi_json, start_date, end_date)
        except Exception:
            return {'level': 'NORMAL', 'message': 'Unable to fetch recent rainfall data.'}

        if rain_df is None or rain_df.empty:
            return {'level': 'NORMAL', 'message': 'No recent rainfall data available.'}

        recent_7d = rain_df.tail(7)['rainfall_mm'].sum()
        recent_3d = rain_df.tail(3)['rainfall_mm'].sum()
        daily_peak = rain_df.tail(7)['rainfall_mm'].max()

        # Determine alert level
        if rp_data and rp_data.get('return_periods'):
            rp = rp_data['return_periods']
            daily_rate = recent_7d / 7
            projected_monsoon = daily_rate * 150

            if projected_monsoon >= rp.get(100, float('inf')):
                level = 'EXTREME'
            elif projected_monsoon >= rp.get(25, float('inf')):
                level = 'SEVERE'
            elif projected_monsoon >= rp.get(10, float('inf')):
                level = 'WARNING'
            elif projected_monsoon >= rp.get(5, float('inf')):
                level = 'WATCH'
            else:
                level = 'NORMAL'
        else:
            # Fallback: absolute thresholds
            if daily_peak > 100:
                level = 'SEVERE'
            elif daily_peak > 60 or recent_3d > 150:
                level = 'WARNING'
            elif daily_peak > 30 or recent_7d > 200:
                level = 'WATCH'
            else:
                level = 'NORMAL'

        alert = {
            'level': level,
            'recent_7d_mm': round(recent_7d, 1),
            'recent_3d_mm': round(recent_3d, 1),
            'daily_peak_mm': round(daily_peak, 1),
            'message': self._format_message(level, recent_7d, daily_peak),
            **self.ALERT_LEVELS[level],
        }

        self.alerts.append(alert)
        return alert

    def _format_message(self, level, rain_7d, peak):
        messages = {
            'NORMAL': f'Normal conditions. 7-day rain: {rain_7d:.0f}mm.',
            'WATCH': f'Elevated rainfall detected. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.',
            'WARNING': f'Heavy rainfall warning. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.',
            'SEVERE': f'Severe flood risk. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.',
            'EXTREME': f'Extreme flood risk. 7-day: {rain_7d:.0f}mm, Peak: {peak:.0f}mm/day.',
        }
        return messages.get(level, '')

    def render_alert_banner(self, alert):
        """Render an alert banner in Streamlit."""
        if alert['level'] == 'NORMAL':
            return

        color = alert['color']
        icon = alert['icon']
        st.markdown(f"""
            <div style="background:rgba({self._hex_to_rgb(color)},0.1);
                        border:1px solid {color};border-radius:8px;
                        padding:12px 20px;margin-bottom:16px;
                        display:flex;align-items:center;gap:12px;">
                <div style="font-size:1.5rem;">{icon}</div>
                <div>
                    <div style="font-family:'Rajdhani',sans-serif;font-size:0.9rem;
                                font-weight:700;color:{color};letter-spacing:2px;">
                        FLOOD ALERT: {alert['level']}</div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                                color:#5a7a8a;margin-top:2px;">{alert['message']}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def _hex_to_rgb(hex_color):
        h = hex_color.lstrip('#')
        return ','.join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))
