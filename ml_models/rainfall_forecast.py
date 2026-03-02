"""
Model 2: Prophet rainfall forecaster.
Fits per-AOI at runtime using CHIRPS historical daily rainfall data.
Forecasts 7-30 days ahead and cross-references with Gumbel return periods.
"""

import pandas as pd
import numpy as np


class RainfallForecaster:
    def __init__(self):
        self.model = None

    def fit_and_forecast(self, rain_df, horizon_days=14):
        """
        Fit Prophet on historical CHIRPS rainfall and forecast ahead.

        Args:
            rain_df: DataFrame from get_chirps_series() with DateTimeIndex
                     and 'rainfall_mm' column.
            horizon_days: Number of days to forecast (7-30).

        Returns:
            dict with forecast_df, cumulative_mm, daily_peak_mm, uncertainty_range.
        """
        try:
            from prophet import Prophet
        except ImportError:
            raise ImportError(
                "Prophet is required for rainfall forecasting. "
                "Install it with: pip install prophet"
            )

        # Prophet requires columns named 'ds' and 'y'
        df_prophet = rain_df.reset_index()
        # Handle both 'date' and datetime index names
        if 'date' in df_prophet.columns:
            df_prophet = df_prophet.rename(columns={'date': 'ds', 'rainfall_mm': 'y'})
        else:
            df_prophet.columns = ['ds', 'y']

        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])

        # Suppress Prophet's verbose logging
        import logging
        logging.getLogger('prophet').setLevel(logging.WARNING)
        logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.1,
            seasonality_prior_scale=10.0,
            interval_width=0.90
        )

        # Add monsoon seasonality
        self.model.add_seasonality(
            name='monsoon', period=365.25, fourier_order=8
        )

        self.model.fit(df_prophet)

        future = self.model.make_future_dataframe(periods=horizon_days)
        forecast = self.model.predict(future)

        # Extract only the forecast period
        forecast_only = forecast.tail(horizon_days)[
            ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
        ].copy()

        # Rainfall can't be negative
        forecast_only['yhat'] = forecast_only['yhat'].clip(lower=0)
        forecast_only['yhat_lower'] = forecast_only['yhat_lower'].clip(lower=0)
        forecast_only['yhat_upper'] = forecast_only['yhat_upper'].clip(lower=0)

        cumulative = forecast_only['yhat'].sum()

        return {
            'forecast_df': forecast_only,
            'cumulative_mm': round(cumulative, 1),
            'daily_peak_mm': round(forecast_only['yhat'].max(), 1),
            'uncertainty_range': (
                round(forecast_only['yhat_lower'].sum(), 1),
                round(forecast_only['yhat_upper'].sum(), 1)
            )
        }

    def estimate_flood_probability(self, forecast_result, return_period_data):
        """
        Cross-reference forecast with Gumbel return periods.

        Scales the forecasted daily rate to an equivalent monsoon season total,
        then compares against return period thresholds.
        """
        if not return_period_data or not return_period_data.get('return_periods'):
            return {'risk_level': 'UNKNOWN', 'probability': None}

        rp = return_period_data['return_periods']
        n_days = len(forecast_result['forecast_df'])
        if n_days == 0:
            return {'risk_level': 'UNKNOWN', 'probability': None}

        # Scale daily forecast to equivalent monsoon-season rate (~150 days Jun-Oct)
        daily_rate = forecast_result['cumulative_mm'] / n_days
        projected_monsoon = daily_rate * 150

        if projected_monsoon >= rp.get(100, float('inf')):
            return {'risk_level': 'EXTREME', 'return_period': '> 100-yr', 'probability': 0.01}
        elif projected_monsoon >= rp.get(25, float('inf')):
            return {'risk_level': 'VERY HIGH', 'return_period': '25-100 yr', 'probability': 0.04}
        elif projected_monsoon >= rp.get(10, float('inf')):
            return {'risk_level': 'HIGH', 'return_period': '10-25 yr', 'probability': 0.10}
        elif projected_monsoon >= rp.get(5, float('inf')):
            return {'risk_level': 'MODERATE', 'return_period': '5-10 yr', 'probability': 0.20}
        else:
            return {'risk_level': 'LOW', 'return_period': '< 5 yr', 'probability': 0.50}
