"""
Feature 3: AutoML hyperparameter tuning with Optuna.
Tunes the Gradient Boosting SAR classifier and returns the best parameters.
"""

import numpy as np
import pandas as pd

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _OPTUNA = True
except ImportError:
    _OPTUNA = False

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


class OptunaTuner:
    """Optuna-based hyperparameter tuning for flood classifiers."""

    def __init__(self, n_trials=50, cv_folds=3, metric='f1'):
        if not _OPTUNA:
            raise ImportError("optuna is required. Run: pip install optuna")
        if not _SKLEARN:
            raise ImportError("scikit-learn is required.")
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.metric = metric
        self.best_params = None
        self.best_score = None
        self.study = None

    def tune_gradient_boosting(self, df, feature_names, label_col='flood_label'):
        """Tune GradientBoostingClassifier hyperparameters."""
        X = df[feature_names].copy().fillna(0)
        y = df[label_col].astype(int)

        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 500, step=50),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 5, 50),
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 30),
            }
            model = GradientBoostingClassifier(**params, random_state=42)
            scores = cross_val_score(model, X, y, cv=self.cv_folds, scoring=self.metric, n_jobs=-1)
            return scores.mean()

        self.study = optuna.create_study(direction='maximize')
        self.study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        self.best_params = self.study.best_params
        self.best_score = round(self.study.best_value, 4)

        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'n_trials': self.n_trials,
            'metric': self.metric,
        }

    def tune_xgboost(self, df, feature_names, label_col='flood_label'):
        """Tune XGBClassifier hyperparameters."""
        try:
            from xgboost import XGBClassifier
        except ImportError:
            raise ImportError("xgboost is required for XGBoost tuning.")

        X = df[feature_names].copy().fillna(0)
        y = df[label_col].astype(int)

        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 500, step=50),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 30),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            }
            model = XGBClassifier(**params, random_state=42, eval_metric='logloss', verbosity=0)
            scores = cross_val_score(model, X, y, cv=self.cv_folds, scoring=self.metric, n_jobs=-1)
            return scores.mean()

        self.study = optuna.create_study(direction='maximize')
        self.study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        self.best_params = self.study.best_params
        self.best_score = round(self.study.best_value, 4)

        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'n_trials': self.n_trials,
            'metric': self.metric,
        }

    def get_optimization_history(self):
        """Return trial history as a DataFrame for visualization."""
        if self.study is None:
            return None
        trials = []
        for t in self.study.trials:
            trials.append({
                'trial': t.number,
                'score': t.value if t.value is not None else 0,
                'state': str(t.state),
            })
        return pd.DataFrame(trials)
