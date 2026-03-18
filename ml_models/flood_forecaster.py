"""
LSTM-based flood forecaster.
Uses ERA5/CHIRPS historical time-series + GFS forecast to predict
flood probability over a 7-14 day horizon.

Falls back to a simpler GBM-based approach if PyTorch is unavailable.
"""

import json
import os

import ee
import numpy as np
import pandas as pd

try:
    import joblib
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler

    _SKLEARN = True
except ImportError:
    _SKLEARN = False

try:
    import torch
    import torch.nn as nn

    _TORCH = True
except ImportError:
    _TORCH = False


# ── LSTM Model Definition ──────────────────────────────────


class _FloodLSTM(nn.Module if _TORCH else object):
    """LSTM network for flood probability prediction from climate time-series."""

    def __init__(self, input_size=5, hidden_size=64, num_layers=2, dropout=0.2):
        if not _TORCH:
            return
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]
        return self.fc(last_hidden)


# ── Main Forecaster Class ──────────────────────────────────


class FloodForecaster:
    """
    Flood probability forecaster using climate time-series.

    Features (per timestep):
        - precipitation (mm)
        - temperature (C)
        - soil_moisture (m3/m3)
        - runoff (mm)
        - humidity (%)

    Target: binary flood event (1 if JRC water occurrence spike detected)

    Uses LSTM if PyTorch available, else falls back to GBM with
    rolling-window features.
    """

    MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
    LSTM_PATH = os.path.join(MODEL_DIR, "flood_lstm.pt")
    GBM_PATH = os.path.join(MODEL_DIR, "flood_forecast_gbm.joblib")
    SCALER_PATH = os.path.join(MODEL_DIR, "flood_forecast_scaler.joblib")

    SEQUENCE_LENGTH = 30  # 30 days of historical context
    FEATURE_NAMES = ["precip", "temp", "soil_moisture", "runoff", "humidity"]

    def __init__(self):
        self.model = None
        self.scaler = None
        self.use_lstm = _TORCH
        self.is_trained = False

    def _extract_training_data(self, aoi_json, years=None):
        """
        Extract daily climate time-series from ERA5-Land for training.

        Labels: flood=1 if daily precipitation > 95th percentile AND
                soil moisture > 90th percentile (proxy for flood conditions).
        """
        if years is None:
            years = list(range(2018, 2024))

        aoi_geom = ee.Geometry(json.loads(aoi_json))
        all_records = []

        for year in years:
            col = (
                ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
                .filterBounds(aoi_geom)
                .filterDate(f"{year}-06-01", f"{year}-11-01")  # Monsoon season
                .select(
                    [
                        "total_precipitation_sum",
                        "temperature_2m",
                        "volumetric_soil_water_layer_1",
                        "surface_runoff_sum",
                    ]
                )
            )

            count = col.size().getInfo()
            if not count:
                continue

            def extract_day(img):
                stats = img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=aoi_geom,
                    scale=11000,
                    maxPixels=1e8,
                )
                return ee.Feature(
                    None,
                    {
                        "date": img.date().format("YYYY-MM-dd"),
                        "precip": ee.Number(stats.get("total_precipitation_sum")).multiply(1000),
                        "temp": ee.Number(stats.get("temperature_2m")).subtract(273.15),
                        "soil_moisture": stats.get("volumetric_soil_water_layer_1"),
                        "runoff": ee.Number(stats.get("surface_runoff_sum")).multiply(1000),
                    },
                )

            fc = col.map(extract_day).getInfo()
            for f in fc.get("features", []):
                p = f["properties"]
                if p.get("precip") is not None:
                    all_records.append(
                        {
                            "date": p["date"],
                            "precip": round(p.get("precip", 0) or 0, 2),
                            "temp": round(p.get("temp", 25) or 25, 1),
                            "soil_moisture": round(p.get("soil_moisture", 0.3) or 0.3, 4),
                            "runoff": round(p.get("runoff", 0) or 0, 2),
                            "humidity": 70.0,  # placeholder — ERA5 Land lacks humidity
                        }
                    )

        if not all_records:
            return None

        df = pd.DataFrame(all_records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Create flood labels: top 5% precipitation AND top 10% soil moisture
        p95_precip = df["precip"].quantile(0.95)
        p90_sm = df["soil_moisture"].quantile(0.90)
        df["flood"] = ((df["precip"] >= p95_precip) & (df["soil_moisture"] >= p90_sm)).astype(int)

        return df

    def train(self, aoi_json, years=None):
        """Train the flood forecaster on historical ERA5 data."""
        df = self._extract_training_data(aoi_json, years)
        if df is None or len(df) < self.SEQUENCE_LENGTH + 10:
            return False

        features = df[self.FEATURE_NAMES].values
        labels = df["flood"].values

        # Fit scaler
        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(features)

        if self.use_lstm:
            return self._train_lstm(features_scaled, labels)
        return self._train_gbm(features_scaled, labels, df)

    def _train_lstm(self, features, labels):
        """Train LSTM model."""
        sequences, targets = [], []
        for i in range(self.SEQUENCE_LENGTH, len(features)):
            sequences.append(features[i - self.SEQUENCE_LENGTH : i])
            targets.append(labels[i])

        X = torch.FloatTensor(np.array(sequences))
        y = torch.FloatTensor(np.array(targets)).unsqueeze(1)

        self.model = _FloodLSTM(input_size=len(self.FEATURE_NAMES))
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.BCELoss()

        self.model.train()
        for epoch in range(50):
            optimizer.zero_grad()
            output = self.model(X)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()

        self.is_trained = True
        self._save()
        return True

    def _train_gbm(self, features, labels, df):
        """Train GBM with rolling-window features as LSTM fallback."""
        # Create rolling features
        roll_df = pd.DataFrame(features, columns=self.FEATURE_NAMES)
        for col in self.FEATURE_NAMES:
            roll_df[f"{col}_7d_mean"] = roll_df[col].rolling(7, min_periods=1).mean()
            roll_df[f"{col}_7d_max"] = roll_df[col].rolling(7, min_periods=1).max()
            roll_df[f"{col}_3d_sum"] = roll_df[col].rolling(3, min_periods=1).sum()

        # Drop initial rows without enough history
        valid = roll_df.iloc[self.SEQUENCE_LENGTH :].copy()
        valid_labels = labels[self.SEQUENCE_LENGTH :]

        self.model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
        )
        self.model.fit(valid, valid_labels)
        self.is_trained = True
        self._save()
        return True

    def _save(self):
        """Save model and scaler to disk."""
        os.makedirs(self.MODEL_DIR, exist_ok=True)
        if self.use_lstm and isinstance(self.model, _FloodLSTM):
            torch.save(self.model.state_dict(), self.LSTM_PATH)
        elif self.model is not None:
            joblib.dump(self.model, self.GBM_PATH)
        if self.scaler is not None:
            joblib.dump(self.scaler, self.SCALER_PATH)

    def load(self):
        """Load pre-trained model from disk."""
        if os.path.exists(self.SCALER_PATH):
            self.scaler = joblib.load(self.SCALER_PATH)

        if self.use_lstm and os.path.exists(self.LSTM_PATH):
            self.model = _FloodLSTM(input_size=len(self.FEATURE_NAMES))
            self.model.load_state_dict(torch.load(self.LSTM_PATH, weights_only=True))
            self.model.eval()
            self.is_trained = True
            return True
        elif os.path.exists(self.GBM_PATH):
            self.model = joblib.load(self.GBM_PATH)
            self.use_lstm = False
            self.is_trained = True
            return True
        return False

    def predict(self, recent_data_df, forecast_df=None):
        """
        Predict flood probability for upcoming days.

        Args:
            recent_data_df: DataFrame with last 30 days of FEATURE_NAMES columns.
            forecast_df: Optional GFS forecast DataFrame with similar columns.

        Returns dict with daily probabilities and overall assessment.
        """
        if not self.is_trained or self.model is None or self.scaler is None:
            return None

        # Build feature matrix from recent data
        features = recent_data_df[self.FEATURE_NAMES].fillna(0).values
        features_scaled = self.scaler.transform(features)

        if forecast_df is not None and len(forecast_df) > 0:
            # Map GFS columns to our feature names
            fc_features = pd.DataFrame(
                {
                    "precip": forecast_df.get("precip_mm", forecast_df.get("Precip (mm)", 0)),
                    "temp": forecast_df.get("temp_c", forecast_df.get("Temp (°C)", 25)),
                    "soil_moisture": 0.3,  # Assume average
                    "runoff": forecast_df.get("precip_mm", forecast_df.get("Precip (mm)", 0)) * 0.3,
                    "humidity": forecast_df.get("humidity_pct", forecast_df.get("Humidity (%)", 70)),
                }
            )
            fc_scaled = self.scaler.transform(fc_features[self.FEATURE_NAMES].fillna(0).values)
            all_scaled = np.vstack([features_scaled, fc_scaled])
        else:
            all_scaled = features_scaled

        # Generate predictions
        if self.use_lstm and isinstance(self.model, _FloodLSTM):
            return self._predict_lstm(all_scaled, len(features_scaled))
        return self._predict_gbm(all_scaled, len(features_scaled))

    def _predict_lstm(self, all_scaled, history_len):
        """Generate predictions using LSTM."""
        self.model.eval()
        probs = []
        n_forecast = len(all_scaled) - history_len

        for i in range(max(n_forecast, 7)):
            start = min(history_len + i, len(all_scaled)) - self.SEQUENCE_LENGTH
            start = max(0, start)
            end = start + self.SEQUENCE_LENGTH
            if end > len(all_scaled):
                break
            seq = torch.FloatTensor(all_scaled[start:end]).unsqueeze(0)
            with torch.no_grad():
                prob = self.model(seq).item()
            probs.append(round(prob, 3))

        return self._format_predictions(probs)

    def _predict_gbm(self, all_scaled, history_len):
        """Generate predictions using GBM with rolling features."""
        df = pd.DataFrame(all_scaled, columns=self.FEATURE_NAMES)
        for col in self.FEATURE_NAMES:
            df[f"{col}_7d_mean"] = df[col].rolling(7, min_periods=1).mean()
            df[f"{col}_7d_max"] = df[col].rolling(7, min_periods=1).max()
            df[f"{col}_3d_sum"] = df[col].rolling(3, min_periods=1).sum()

        forecast_rows = df.iloc[history_len : history_len + 14]
        if forecast_rows.empty:
            forecast_rows = df.iloc[-7:]

        probs = self.model.predict_proba(forecast_rows)[:, 1]
        return self._format_predictions([round(p, 3) for p in probs])

    def _format_predictions(self, probs):
        """Format prediction results."""
        if not probs:
            return None

        max_prob = max(probs)
        mean_prob = round(sum(probs) / len(probs), 3)
        peak_day = probs.index(max_prob) + 1

        if max_prob >= 0.7:
            risk_level = "HIGH"
        elif max_prob >= 0.4:
            risk_level = "MODERATE"
        elif max_prob >= 0.2:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"

        return {
            "daily_probabilities": probs,
            "max_probability": max_prob,
            "mean_probability": mean_prob,
            "peak_day": peak_day,
            "risk_level": risk_level,
            "n_forecast_days": len(probs),
            "model_type": "LSTM" if self.use_lstm else "GBM",
        }
