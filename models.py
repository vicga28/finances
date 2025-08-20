import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb
from sklearn.metrics import mean_squared_error

# Funcions per a la generació de models

@st.cache_data
def add_lags(df, lag1 = 1, lag2= 2, lag3 = 3):
    df = df.copy()
    target_map = df['Import'].to_dict()
    df['lag1'] = (df.index - pd.DateOffset(years=lag1)).map(target_map)
    df['lag2'] = (df.index - pd.DateOffset(years=lag2)).map(target_map)
    df['lag3'] = (df.index - pd.DateOffset(years=lag3)).map(target_map)
    return df

# Generar models per a cada categoria
@st.cache_data
def generate_cat_models(mf_cat, id_cat, plot=False, n_splits = 5, test_size = 12, gap = 0):
    scores_mean = pd.DataFrame()
    scores_mean = {}
    fi_cat = {}
    preds_cat = {}
    scores_cat = {}
    models_cat = {}
    tss = TimeSeriesSplit(n_splits = n_splits, test_size = test_size, gap = gap)
    for cat in id_cat:
        mf_cat[cat] = add_lags(mf_cat[cat])
        fig, axs = plt.subplots(5, 1, figsize = (15, 15), sharex = True)
        fold = 0
        preds = []
        scores = []
        reg = xgb.XGBRegressor(base_score=0.5, booster='gbtree',    
                                n_estimators=1000,
                                early_stopping_rounds=50,
                                objective='reg:squarederror',
                                max_depth=3,
                                learning_rate=0.01)
        for train_idx, val_idx in tss.split(mf_cat[cat]):
            train = mf_cat[cat].iloc[train_idx]
            test = mf_cat[cat].iloc[val_idx]
            
            FEATURES = ['Any', 'Mes', 'lag1','lag2','lag3']
            TARGET = 'Import'

            X_train = train[FEATURES]
            y_train = train[TARGET]

            X_test = test[FEATURES]
            y_test = test[TARGET]

            reg.fit(X_train, y_train,
                    eval_set=[(X_train, y_train), (X_test, y_test)],
                    verbose=100)

            y_pred = reg.predict(X_test)
            preds.append(y_pred)
            score = np.sqrt(mean_squared_error(y_test, y_pred))
            scores.append(score)
            predictions = pd.DataFrame(y_test)
            predictions['prediction'] = y_pred
            train['Import'].plot(ax = axs[fold], label = 'Training Set', title=f'Data Train/Test Split Fold {fold}')
            test['Import'].plot(ax = axs[fold], label = 'Test Set')
            axs[fold].axvline(test.index.min(), color='black', ls='--')
            predictions.plot(ax=axs[fold], label = 'Predictions')
            fold += 1
        preds_cat[cat] = preds
        scores_cat[cat] = scores
        models_cat[cat] = reg
        if plot:
            st.write(cat)
            st.pyplot(fig)
            st.write('Scores')
            st.write(scores)
            st.write(f'Score across folds {np.mean(scores):0.4f}')
        scorie = np.mean(scores)
        scores_mean[cat] = scorie
        fi = pd.DataFrame(data=reg.feature_importances_,
                    index=reg.feature_names_in_,
                    columns=['importance'])
        if plot:
            axie = fi.sort_values('importance').plot(kind='barh', title='Feature Importance')
            frig = axie.get_figure()
            st.pyplot(frig)
        fi_cat[cat] = fi.sort_values('importance', ascending=False)
    fi = pd.DataFrame()
    for cat in id_cat:
        fi[cat] = fi_cat[cat]
    return models_cat, fi, scores_mean, scores_cat, preds_cat

def generate_serveis_models(mf_serveis, serveis, plot=False, n_splits = 5, test_size = 12, gap = 0):
    scores_mean = pd.DataFrame()
    scores_mean = {}
    fi_serveis = {}
    preds_serveis = {}
    scores_serveis = {}
    models_serveis = {}
    tss = TimeSeriesSplit(n_splits = n_splits, test_size = test_size, gap = gap)
    for servei in serveis:
        mf_serveis[servei] = add_lags(mf_serveis[servei])
        fig, axs = plt.subplots(5, 1, figsize = (15, 15), sharex = True)
        fold = 0
        preds = []
        scores = []
        reg = xgb.XGBRegressor(base_score=0.5, booster='gbtree',    
                                n_estimators=1000,
                                early_stopping_rounds=50,
                                objective='reg:squarederror',
                                max_depth=3,
                                learning_rate=0.01)
        for train_idx, val_idx in tss.split(mf_serveis[servei]):
            train = mf_serveis[servei].iloc[train_idx]
            test = mf_serveis[servei].iloc[val_idx]
            
            FEATURES = ['Any', 'Mes', 'lag1','lag2','lag3']
            TARGET = 'Import'

            X_train = train[FEATURES]
            y_train = train[TARGET]

            X_test = test[FEATURES]
            y_test = test[TARGET]

            reg.fit(X_train, y_train,
                    eval_set=[(X_train, y_train), (X_test, y_test)],
                    verbose=100)

            y_pred = reg.predict(X_test)
            preds.append(y_pred)
            score = np.sqrt(mean_squared_error(y_test, y_pred))
            scores.append(score)
            predictions = pd.DataFrame(y_test)
            predictions['prediction'] = y_pred
            train['Import'].plot(ax = axs[fold], label = 'Training Set', title=f'Data Train/Test Split Fold {fold}')
            test['Import'].plot(ax = axs[fold], label = 'Test Set')
            axs[fold].axvline(test.index.min(), color='black', ls='--')
            predictions.plot(ax=axs[fold], label = 'Predictions')
            fold += 1
        preds_serveis[servei] = preds
        scores_serveis[servei] = scores
        models_serveis[servei] = reg
        if plot:
            st.write(servei)
            st.pyplot(fig)
            st.write('Scores')
            st.write(scores)
            st.write(f'Score across folds {np.mean(scores):0.4f}')
        scorie = np.mean(scores)
        scores_mean[servei] = scorie
        fi = pd.DataFrame(data=reg.feature_importances_,
                    index=reg.feature_names_in_,
                    columns=['importance'])
        if plot:
            axie = fi.sort_values('importance').plot(kind='barh', title='Feature Importance')
            frig = axie.get_figure()
            st.pyplot(frig)
        fi_serveis[servei] = fi.sort_values('importance', ascending=False)
    fi = pd.DataFrame()
    for servei in serveis:
        fi[servei] = fi_serveis[servei]
    return models_serveis, fi, scores_mean, scores_serveis, preds_serveis