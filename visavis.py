import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import calendar
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objs as go
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb
from sklearn.metrics import mean_squared_error
from dateutil.relativedelta import relativedelta
import streamlit.components.v1 as components

st.set_page_config(layout='wide', initial_sidebar_state='collapsed', page_title='Finances', page_icon='📈',
                   menu_items={'About':'Un dashboard per ajudar a la gestió de les finances personals.'})

#Autentificacio per l'API de Google Sheets
def authenticate_gspread(credentials_path_or_dict):
    """
    Authenticate with Google Sheets using the provided service account credentials.

    This function uses OAuth2 to authenticate with Google Sheets and
    provides access to spreadsheets, drive files, etc. depending on the scopes provided.

    Parameters:
    - credentials_path_or_dict (str/dict): The file path to the service account's JSON key
                                          or the actual credentials as a dictionary.

    Returns:
    - gspread.Client: An authenticated gspread client that can be used to interact with Google Sheets.

    Usage:
    >>> client = authenticate_gspread('path_to_service_account.json')
    or
    >>> creds_dict = {
    ...    'type': '...',
    ...    'project_id': '...',
    ...    # ... other credentials data
    ... }
    >>> client = authenticate_gspread(creds_dict)
    >>> sheet = client.open('My Spreadsheet')
    """
    # Define the scopes necessary for accessing and manipulating Google Sheets and Drive
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]

    # Check the type of the provided credentials_path_or_dict to decide the method to use
    if isinstance(credentials_path_or_dict, str):
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path_or_dict, scope)
    elif isinstance(credentials_path_or_dict, dict):
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_path_or_dict, scope)
    else:
        raise ValueError("The provided credentials_path_or_dict should be either a string (file path) or a dictionary (actual credentials).")

    # Authorize and return a gspread client
    client = gspread.authorize(creds)
    print("Successfully authenticated with Google Sheets.")
    return client

def fetch_data_from_sheet(client, spreadsheet_id, worksheet_name='DATA'):
    """
    Fetch data from a specific worksheet in a Google Sheet and return it as a list of lists.

    This function connects to a Google Sheet using the provided client and fetches data from a specified worksheet. 
    By default, it fetches data from the 'Revenue 2023' worksheet.

    Parameters:
    - client (gspread.Client): The client object that represents the Google Sheets API. Must be authenticated before calling this function.
    - spreadsheet_id (str): The unique identifier for the target Google Sheet. It is usually found in the sheet's URL.
    - worksheet_name (str, optional): The name of the worksheet to fetch data from. Defaults to 'Revenue 2023'.

    Returns:
    - list of lists: Rows of data fetched from the specified worksheet, where each row is represented as a list.

    Example:
    ```
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name('your_credentials_file.json', scope)
    client = gspread.authorize(creds)

    spreadsheet_id = 'your_spreadsheet_id'
    data = fetch_data_from_sheet(client, spreadsheet_id, 'Some Worksheet Name')
    for row in data[:5]:  # print first five rows
        print(row)
    ```

    Note:
    Ensure the Google Sheet and the specified worksheet are accessible by the provided client credentials.
    """
    sheet = client.open_by_key(key=spreadsheet_id)
    data = sheet.worksheet(worksheet_name).get_values(value_render_option = "UNFORMATTED_VALUE")
    
    return data

def load_data(_client, spreadsheet_id):
    data = fetch_data_from_sheet(client, spreadsheet_id, worksheet_name='DATA')
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# Now you can access the credentials as a dictionary
credentials = {
    "type": st.secrets['type'],
    "project_id": st.secrets['project_id'],
    "private_key_id": st.secrets['private_key_id'],
    "private_key": st.secrets['private_key'].replace('\\\\n', '\\n'),
    "client_email": st.secrets['client_email'],
    "client_id": st.secrets['client_id'],
    "auth_uri": st.secrets['auth_uri'],
    "token_uri": st.secrets['token_uri'],
    "auth_provider_x509_cert_url": st.secrets['auth_provider_x509_cert_url'],
    "client_x509_cert_url": st.secrets['client_x509_cert_url']
}
spreadsheet_id = "1--akOa5R5ghC35dztP78BvrdLZYFJT6LDwKSTR0mWSk"

#Agafar el excel del Google Drive
client = authenticate_gspread(credentials)
df = load_data(client, spreadsheet_id)

#Generació id categories per a fer servir després pels inputs
## Estaria bé automatitzar-ho a partir de valors o bé generals (Income/Expenses) o a partir del input del dataframe o de la propia app
id_tipus = ['Despesa', 'Estalvi', 'Ingressos']
id_tip = df['Tipus'].unique()
id_tipus_gast = ['Fixe', 'Oci']
dict_cat = {}
for tipus in id_tip:
    aux_df = df.copy()
    dict_cat[tipus] = aux_df.query('Tipus == @tipus')['Categoria'].unique()
id_cat = df.query('Tipus == "Oci"')['Categoria'].unique()
id_fixe = df.query('Tipus == "Fixe"')['Categoria'].unique()
id_cat_total = np.append(id_cat, id_fixe)
id_years = np.sort(df['Any'].unique())[::-1]

dict_month = {1:'Gener', 2:'Febrer', 3:'Març', 4:'Abril', 5:'Maig', 6:'Juny',
7:'Juliol', 8:'Agost', 9:'Setembre', 10:'Octubre', 11:'Novembre', 12:'Desembre'}
dict_gast = {'Oci':id_cat, 'Fixe':id_fixe}
dict_tipus = {'Despesa':'Gast', 'Estalvi':'Estalvi', 'Ingressos':'Income'}
dict_tip_cat = {'Estalvi':'', 'Oci':id_cat, 'Fixe':id_fixe, 'Income':''}

id_months = dict_month.values()

month_actual = date.today().month
year_actual = date.today().year
day_actual = date.today().day
num_days = calendar.monthrange(year_actual, month_actual)[-1]

#Triant els colors de les gràfiques
palette = px.colors.qualitative.T10
dict_color = {'Income':palette[4], 'Oci':palette[2], 'Fixe':palette[1], 'Estalvi':palette[9]}
bold = px.colors.qualitative.Bold
vivid = px.colors.qualitative.Vivid
col_cat = {'Transport':vivid[10], 'Tabac':vivid[0], 'Beguda':vivid[7], 'Restaurant':vivid[9], 'Entrades':vivid[2],
           'Subscripcions':vivid[3], 'Supermercat':vivid[5], 'Compres':vivid[6], 'Altres':vivid[1]}
dict_order = {'Tipus':['Income', 'Oci', 'Fixe', 'Estalvi'], 'Categoria':id_cat}

#Funcions
@st.cache_data
def generate_dataframe(df):
    #Generació d'un primer DataFrame amb una nova columna que és la data en format datetime i eliminar categories de Income i Estalvi que no és fan servir
    df_date = df.copy()
    id_cat_df = set(df.Categoria.unique())
    id_cat_out = id_cat_df.difference(id_cat_total)
    df_date['Categoria'] = df_date['Categoria'].replace(id_cat_out, '')
    df_date['Data'] = df['Any'].astype('string') + '-' + df['Mes'].astype('string') + '-' + df['Dia'].astype('string')
    df_date = df_date.filter(['Data', 'Tipus', 'Categoria', 'Import']).groupby(by=['Data', 'Tipus', 'Categoria']).sum().reset_index()
    df_date['Data'] = pd.to_datetime(df_date['Data'], dayfirst=True, format='%Y-%m-%d')
    df_date = df_date.groupby(by=['Data', 'Tipus', 'Categoria']).sum()
    #Generació d'un segon DataFrame (dummy) on es generen entrades per a cada dia i categoria amb import 0
    first_day = df_date.index[0][0] #Aquí es considera el primer dia on es té informació, també es pot considerar incloure tot el primer any
    last_day = date(year_actual, 12, 31)
    time_series = pd.date_range(start=first_day, end=last_day)
    df_zero = pd.DataFrame([0], columns=['Import'])
    i=0
    for data in time_series:
        for tipus in id_tip:
            if tipus in id_tipus_gast:
                for cat in dict_gast[tipus]:
                    df_zero.loc[i, 'Data'] = data
                    df_zero.loc[i, 'Tipus'] = tipus
                    df_zero.loc[i, 'Categoria'] = cat
                    df_zero.loc[i, 'Import'] = 0
                    i += 1
            else:
                df_zero.loc[i, 'Data'] = data
                df_zero.loc[i, 'Tipus'] = tipus
                df_zero.loc[i, 'Categoria'] = ''
                df_zero.loc[i, 'Import'] = 0
                i += 1   
    #Unió dels dos DataFrames i retornar un únic per tenir valors de 0 per les categories on no hi ha despeses per un determinat mes
    bf = df_zero.merge(df_date, on=['Data', 'Tipus', 'Categoria'], how='left')
    bf = bf.fillna(0).drop(columns='Import_x').rename(columns={'Import_y':'Import'}).set_index('Data')
    bf['Any'] = bf.index.year
    bf['Mes'] = bf.index.month
    #Sumar imports de cada categoria mensualment
    bf = bf.groupby(by=['Any', 'Mes', 'Tipus', 'Categoria'], as_index=False, observed=True).sum()
    af = bf.filter(['Any', 'Tipus', 'Categoria', 'Import']).groupby(by=['Any', 'Tipus', 'Categoria'], as_index=False, observed=True).sum()
    return bf, af

@st.cache_data
def gast_any(data, any, tipus):
    output = data.query('Any == @any and Tipus == @tipus').agg('sum').get('Import')
    return output

@st.cache_data
def gast_mes(data, mes, any, tipus):
    output = data.query('Any == @any and Mes == @mes and Tipus == @tipus').agg('sum').get('Import')
    return output

@st.cache_data
def gast_total(data, tipus):
    output = data.query('Tipus == @tipus').agg('sum').get('Import')
    return output

@st.cache_data
def gast_cat(data, mes, any, cat):
    output = data.query('Any == @any and Mes == @mes and Categoria == @cat').agg('sum').get('Import')
    return output

@st.cache_data
def get_income(data, mes, any):
    output = data.query('Any == @any and Mes == @mes and Tipus == "Income"').agg('sum').get('Import')
    return output

@st.cache_data
def get_month_number(mes):
    for i in range(1,13):
        if dict_month[i] == mes:
            month_num= i
    return month_num

@st.cache_data
def get_last_month(mes, any):
    i = mes - 1
    j = any
    if mes == 1:
        last_month = 12, j - 1
    else:
        last_month = i, j
    return last_month


# Funcions per a la generació de models

@st.cache_data
def add_lags(df, lag1 = 1, lag2= 2, lag3 = 3):
    df = df.copy()
    target_map = df['Import'].to_dict()
    df['lag1'] = (df.index - pd.DateOffset(years=lag1)).map(target_map)
    df['lag2'] = (df.index - pd.DateOffset(years=lag2)).map(target_map)
    df['lag3'] = (df.index - pd.DateOffset(years=lag3)).map(target_map)
    return df


# Generar gràfiques per a oci/fixe/income
@st.cache_data
def generate_tipus_df(df, id_tip = id_tip):
    bf = df.copy()
    mf_tipus = {}
    for tipus in id_tip:
        mf_tipus['{}'.format(tipus)] = bf.query('Tipus == @tipus').drop(columns=['Categoria']).groupby(by=['Mes', 'Any', 'Tipus'], as_index=False).sum().sort_values(by=['Any', 'Mes'])
        mf_tipus[tipus]['Data'] = mf_tipus[tipus]['Any'].astype('string') + '-' + mf_tipus[tipus]['Mes'].astype('string')
        mf_tipus[tipus]['Date'] = pd.to_datetime(mf_tipus[tipus]['Data'], format='%Y-%m')
        mf_tipus[tipus]['Date'] = mf_tipus[tipus]['Date'].dt.date
        mf_tipus[tipus] = mf_tipus[tipus][mf_tipus[tipus]['Date'] < date.today()].sort_values('Date', ascending=False).drop(columns=['Data'])
        mf_tipus[tipus] = mf_tipus[tipus].set_index('Date').drop(columns=['Tipus'])
    return mf_tipus


# Generació DataFrames respecte categories
@st.cache_data
def generate_cat_df(bf, id_cat = id_cat):
    mf = bf.copy()
    mf['Data'] = mf['Any'].astype('string') + '-' + mf['Mes'].astype('string')
    mf['Date'] = pd.to_datetime(mf['Data'], format='%Y-%m')
    mf['Date'] = mf['Date'].dt.date
    mf = mf[mf['Date'] < date.today()].sort_values('Date', ascending=False)
    df = mf[:(14*6)]
    mf_cat = {}
    df_cat = {}
    for cat in id_cat:
        mf_cat['{}'.format(cat)] = mf.query('Categoria == @cat').groupby(by=['Mes', 'Any'], as_index=False).sum().sort_values(by=['Any', 'Mes']).drop(columns=['Data'])
        df_cat['{}'.format(cat)] = df.query('Categoria == @cat').groupby(by=['Mes', 'Any'], as_index=False).sum().sort_values(by=['Any', 'Mes']).drop(columns=['Data'])
        mf_cat[cat] = mf_cat[cat].set_index('Date').drop(columns=['Tipus', 'Categoria'])
        df_cat[cat] = df_cat[cat].set_index('Date').drop(columns=['Tipus', 'Categoria'])
    return mf_cat, df_cat


# Ara mateix els df de cat es generen en ordre ascendent i els de tipus en ordre descendent


# Funció per obtenir informació de les dates
@st.cache_data
def get_datetime_info(df):
    bf = df.copy()
    bf['Data'] = bf['Any'].astype('string') + '-' + bf['Mes'].astype('string')
    bf['Date'] = pd.to_datetime(bf['Data'], format='%Y-%m')
    bf['Date'] = bf['Date'].dt.date
    bf = bf[bf['Date'] < date.today()].sort_values('Date', ascending=False).drop(columns=['Data'])
    bf = bf.set_index('Date')
    date_0 = bf.index.min()
    end_date = date.today()
    daterange = end_date - date_0
    diff_years = relativedelta(end_date, date_0).years
    return bf, date_0, diff_years, daterange


# Generar models per a cada categoria
@st.cache_data
def generate_cat_models(mf_cat, id_cat = id_cat, plot=False, n_splits = 5, test_size = 12, gap = 0):
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

# Afegir una columna amb la data
@st.cache_data
def add_date(df):
    df = df.copy()
    df['Data'] = df['Any'].astype('string') + '-' + df['Mes'].astype('string') + '-' + df['Dia'].astype('string')
    df['Date'] = pd.to_datetime(df['Data'], format='%Y-%m-%d')
    df['Date'] = df['Date'].dt.date
    df = df.drop(columns=['Data'])
    return df



def create_table(df, lim_cat,  month = month_actual, year = year_actual):
    df = df.copy()
    df = add_date(df)
    df = df[df['Date'] < date.today()].sort_values('Date', ascending=False)
    df_monthly = pd.DataFrame(columns=['Import'], index=id_cat)
    for cat in id_cat:
        df_cat = df.query('Categoria == @cat').drop(columns=['Categoria', 'Tipus', 'Dia', 'Concepte', 'Obs', 'Date']).groupby(['Mes', 'Any']).sum().sort_values(by=['Any', 'Mes'], ascending=False)
        yeye = df_cat.reset_index()
        trend_cat = yeye['Import'][:6]
        i = -1
        for value in trend_cat:
            df_monthly.loc[[cat],[str(i)]] = value
            i -= 1
        df_monthly.loc[[cat], ['Import']] = gast_cat(bf, month, year, cat)
        df_monthly.loc[[cat], ['Limit']] = lim_cat[cat]
    sum = df_monthly['Import'].sum()
    df_monthly['Percentatge'] = df_monthly['Import'] / sum *100
    df_monthly['Diff'] = df_monthly['Limit'] - df_monthly['Import']
    trend = df_monthly[['-6', '-5', '-4', '-3', '-2', '-1']]
    trend = trend.astype(str).agg(', '.join,axis=1)
    df_monthly['Trend'] = trend
    df_monthly = df_monthly.drop(columns=['-1', '-2', '-3', '-4', '-5', '-6'])
    return df_monthly


def color_dif(val):
    if val < 0:
        color = 'red'
    elif val == 0:
        color = 'yellow'
    else:
        color = 'green'
    return f'color: {color}'

@st.cache_data
def create_summary_table(df):
    df = df.copy()
    years = df['Any'].unique()
    summary = pd.DataFrame(index=years)
    for year in years:
        summary.loc[[year],['Income']] = gast_any(df, year, 'Income')
        summary.loc[[year],['Expenses']] = gast_any(df, year, 'Oci') + gast_any(df, year, 'Fixe')
        summary.loc[[year],['Oci']] = gast_any(df, year, 'Oci')
        summary.loc[[year],['Fixe']] = gast_any(df, year, 'Fixe')
    summary['Balance'] = summary['Income'] - summary['Expenses']
    summary['Esforç'] = summary['Expenses'] * 100 / summary['Income']
    summary = summary[['Income', 'Oci', 'Fixe', 'Expenses', 'Balance', 'Esforç']]
    summary = summary.sort_index(ascending=True).transpose()
    return summary

@st.cache_data
def create_summary_yearly(df):
    df = df.copy()
    years = df['Any'].unique()
    summary_yearly = {}
    for year in years:
        if year == date.today().year:
            date_range = np.array([dict_month[x] for x in range(1, month_actual + 1)])
            summy = pd.DataFrame(index=date_range)
            for i in range(1, date.today().month + 1):
                month = dict_month[i]
                summy.loc[[month],['Income']] = gast_mes(df, get_month_number(month), year, 'Income')
                summy.loc[[month],['Oci']] = gast_mes(df, get_month_number(month), year, 'Oci')
                summy.loc[[month],['Fixe']] = gast_mes(df, get_month_number(month), year, 'Fixe')
                summy.loc[[month],['Expenses']] = gast_mes(df, get_month_number(month), year, 'Oci') + gast_mes(df, get_month_number(month), year, 'Fixe')
        else:
            summy = pd.DataFrame(index=id_months)
            for month in id_months:
                summy.loc[[month],['Income']] = gast_mes(df, get_month_number(month), year, 'Income')
                summy.loc[[month],['Oci']] = gast_mes(df, get_month_number(month), year, 'Oci')
                summy.loc[[month],['Fixe']] = gast_mes(df, get_month_number(month), year, 'Fixe')
                summy.loc[[month],['Expenses']] = gast_mes(df, get_month_number(month), year, 'Oci') + gast_mes(df, get_month_number(month), year, 'Fixe')
        summy['Balance'] = summy['Income'] - summy['Expenses']
        summy['Esforç'] = summy['Expenses'] * 100 / summy['Income']
        summary_yearly[year] = summy.transpose()
    return summary_yearly

def ColourWidgetText(wgt_txt, wch_colour = '#000000'):
    htmlstr = """<script>var elements = window.parent.document.querySelectorAll('*'), i;
                    for (i = 0; i < elements.length; ++i) { if (elements[i].innerText == |wgt_txt|) 
                        elements[i].style.color = ' """ + wch_colour + """ '; } </script>  """

    htmlstr = htmlstr.replace('|wgt_txt|', "'" + wgt_txt + "'")
    components.html(f"{htmlstr}", height=0, width=0)

def change_color(wgt_txt, value):
    if value < 0:
        ColourWidgetText(wgt_txt, wch_colour='#ab1b16')
    elif value == 0:
        ColourWidgetText(wgt_txt, wch_colour='#faff5c')
    else:
        ColourWidgetText(wgt_txt, wch_colour='#25b00c')
    return

def color_perc(wgt_txt, value):
    if value >= 100:
        ColourWidgetText(wgt_txt,wch_colour='#700b08')
    elif value >= 80:
        ColourWidgetText(wgt_txt, wch_colour='#ab1b16')
    elif value >= 60:
        ColourWidgetText(wgt_txt, wch_colour='#c46a10')
    elif value >= 30:
        ColourWidgetText(wgt_txt, wch_colour='#faff5c')
    else:
        ColourWidgetText(wgt_txt, wch_colour='#25b00c')
    return

# Generar taules de gast per categories i mes per a cada any
@st.cache_data
def create_expenses_tables_yearly(df, mf_cat, dict_month, id_cat=id_cat):
    df = df.copy()
    years = df['Any'].unique()
    expenses = {}
    for year in years:
        df_year = pd.DataFrame()
        for cat in id_cat:
            aux_df = mf_cat[cat].query('Any == @year')
            df_year[cat] = aux_df['Import']
        df_year = df_year.reset_index()
        month = pd.to_datetime(df_year['Date'])
        month = month.dt.month
        df_year['Mes'] = month
        df_year.index = df_year['Mes']
        df_year = df_year.drop(columns=['Date', 'Mes'])
        num_months = len(df_year)
        df_year = df_year.transpose().rename(columns=dict_month)
        df_year['Total'] = df_year.sum(axis=1)
        df_year['Mitja'] = df_year['Total'] / num_months
        expenses[year] = df_year
    return expenses

@st.cache_data
def create_expenses_table(df, id_cat=id_cat):
    df = df.copy()
    years = df['Any'].unique()
    expenses = pd.DataFrame(index=years)
    for year in years:
        df_year = df.query('Any == @year')
        for cat in id_cat:
            df_year_cat = df_year.query('Categoria == @cat')
            expenses.loc[[year],[cat]] = df_year_cat.agg('sum').get('Import')
    expenses = expenses.transpose()
    return expenses


lim_cat = {
    'Transport' : 50,
    'Tabac' : 50,
    'Restaurant' : 100,
    'Beguda' : 100,
    'Entrades' : 50,
    'Subscripcions' : 50,
    'Transferencies' : 50,
    'Supermercat' : 300,
    'Compres' : 100,
    'Altres' : 50
}

#Generar DatafFrame
bf, af = generate_dataframe(df)
mf_tipus = generate_tipus_df(bf)
mf_cat, df_cat = generate_cat_df(bf)
tf, first_day, num_years, date_range = get_datetime_info(bf)

n_splits = num_years
test_size = 12

#Generar taules
summary_yearly = create_summary_yearly(bf)
summary = create_summary_table(bf)
expenses_yearly = create_expenses_tables_yearly(bf, mf_cat, dict_month, id_cat)
expenses_table = create_expenses_table(bf, id_cat)

#Pàgina web

#Sidebar
st.sidebar.markdown('## Mes a visualitzar')
last_month, last_year = get_last_month(month_actual, year_actual)
month = month_actual
year = year_actual
with st.sidebar.form('Seleccio_mes', border=False):
    sel_month = st.selectbox('Mes:', id_months, index=None)
    year = st.selectbox('Any:', id_years, index=None)
    month_selection = st.form_submit_button('Selecciona')
if year is None:
    year = year_actual
if sel_month is None:
    month = month_actual
else:
    month = get_month_number(sel_month)
last_month, last_year = get_last_month(month, year)

table_cat = create_table(df, lim_cat=lim_cat, month=month, year=year)


#Pàgina principal
st.title('Dashboad finances')

tab10, tab20, tab30, tab40, tab50 = st.tabs(['Distribució mensual', 'Vista anual', 'Històric', 'Models', 'Configuració'])

# Configuració

with tab50:
    st.markdown('### Configuració')
    st.markdown('Límits')
    with st.form('limits_form', border=True):
        lim_cat = {}
        row1 = st.columns(5)
        row2 = st.columns(5)
        i = 0
        for col in row1 + row2:
            tile = col.container()
            lim_cat[id_cat[i]] = tile.number_input(label=id_cat[i], min_value=0, format='%d', placeholder='Límit {}'.format(id_cat[i]), key='lim_{}'.format(id_cat[i]), value=None, help='Límit disposat a gastar en euros (€).')
            i += 1
        submitted = st.form_submit_button('Guardar')
    lim_sum = 0
    if submitted:
        lim_sum = 0
        for cat in id_cat:
            lim_sum = lim_sum + lim_cat[cat]
    st.write('La quantitat total considerada pels límits és de {} €'.format(lim_sum))

# S'hauria de pensar com fer perquè els límits es mantinguin d'una sessió a una altre, es podria inicialitzar amb els últims valors rebuts o guardar-ho al cache

# Distribució mensual

with tab10:
    st.markdown("### **%s %s**" % (dict_month[month], year))

    #Metrics amb diferents medidors a triar
    col10, col11, col12, col13 = st.columns(4)

    with col10:
        #Gast en oci en el mes seleccionat
        st.metric(label='Oci',
                value='{:,.2f} €'.format(gast_mes(bf, month, year, 'Oci')),
                delta='{:,.2f} €'.format(gast_mes(bf, month, year, 'Oci')-gast_mes(bf, last_month, last_year, 'Oci')),
                delta_color='inverse')
        if (gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')) != 0:
            st.metric(label='',
                    value = '{:,.2f} %'.format(gast_mes(bf, month, year, 'Oci')*100/(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))))
    with col11:
        #Gast fixe en el mes seleccionat
        st.metric(label='Fixe',
                value='{:,.2f} €'.format(gast_mes(bf, month, year, 'Fixe')),
                delta='{:,.2f} €'.format(gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Fixe')),
                delta_color='inverse')
        if (gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')) != 0:
            st.metric(label='',
                    value = '{:,.2f} %'.format(gast_mes(bf, month, year, 'Fixe')*100/(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))))
    with col12:
        #Despeses totals del mes seleccionat
        st.metric(label='Despesa mensual',
                value='{:,.2f} €'.format(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')),
                delta='{:,.2f} €'.format(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Oci')-gast_mes(bf, last_month, last_year, 'Fixe')),
                delta_color='inverse')
        income = get_income(bf, month, year)
        if income == 0:
            st.metric(label='Esforç econòmic',
                    value = '{:,.2f} %'.format((gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))*100/get_income(bf, last_month, last_year)))
        else:
            st.metric(label='Esforç econòmic',
                    value = '{:,.2f} %'.format((gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))*100/income))
    with col13:
        if month == month_actual:
            #Previsió de gast del mes present
            prev = gast_mes(bf, month, year, 'Oci')*num_days/day_actual+gast_mes(bf, month, year, 'Fixe')
            st.metric(label='Previsió gast mensual',
                    value='{:,.2f} €'.format(prev),
                    delta='{:,.2f} €'.format(gast_mes(bf, last_month, last_year, 'Income')-prev),
                    delta_color='normal')
        else:
            #Balanç del mes
            bal = gast_mes(bf,month,year,'Income')-(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))
            st.metric(label='Balanç mensual', value='{:,.2f} €'.format(bal), delta='')
            change_color('{:,.2f} €'.format(bal), bal)

    # Gràfiques i taules
    col100, col200 = st.columns([5,5])

    with col100:
        # Gràfica gast mensual per categories
        fig = px.bar(bf.query('Any == @year and Mes == @month and Tipus == "Oci"').sort_values(['Import'], ascending=False),
                    y='Categoria', x='Import', orientation ='h', color='Categoria', color_discrete_map=col_cat)
        fig.update_traces(hovertemplate='%{value:,.02f} €')
        fig.update_xaxes(title='')
        fig.update_layout(showlegend=False, xaxis_ticksuffix = '€', xaxis_tickformat= ',', separators='.,')
        st.plotly_chart(fig, use_container_width=True)
    with col200:
        # Taula amb despesa per categories
        table_cat = table_cat.style.applymap(color_dif, subset=['Diff'])\
            .format('{:,.2f} €', subset=(['Import', 'Limit', 'Diff']))\
            .format('{:,.2f} %', subset=('Percentatge'))\
            .background_gradient(cmap='RdYlGn_r', subset=['Percentatge'], vmax=100, vmin=0)
        st.dataframe(table_cat, column_order=['Import', 'Percentatge', 'Limit', 'Diff', 'Trend'],
                     column_config={'Trend':st.column_config.LineChartColumn('Últims 6 mesos', y_min = 0)},
                     use_container_width = True)
        
    #Taula per veure despeses per mes amb filtres

    with st.expander('Veure despeses'):
        col_exp_1, col_exp_2 = st.columns(2)
        with col_exp_1:
            sel_tipus = st.selectbox(label='Tipus', options=id_tip, index=None, key='main_tipus', placeholder='Filtrar per tipus')
        with col_exp_2:
            if sel_tipus == None:
                sel_cat = st.selectbox(label='Categoria', options=id_cat, index=None, key='main_cat', placeholder='Filtrar per categoria')
            else:
                sel_cat = st.selectbox(label='Categoria', options=dict_cat[sel_tipus], index=None, key='main_cat', placeholder='Filtrar per categoria')
        if sel_tipus == None:
            if sel_cat == None:
                df_dis = add_date(df)
                sel_df = df_dis.query('Any == @year and Mes == @month')
                sel_df = sel_df.set_index('Date').drop(columns=['Any', 'Mes', 'Dia'])
                st.dataframe(sel_df,
                        column_config={"Import": st.column_config.NumberColumn(
                        "Import",
                        help="Import en euros",
                        min_value=0,
                        max_value=1000,
                        step=0.01,
                        format="%f €",),
                        "Date":st.column_config.DateColumn(
                            "Data",
                            format="DD/MM/YYYY"
                        )},
                        hide_index=False,
                        use_container_width = True)
            else:
                df_dis = add_date(df)
                sel_df = df_dis.query('Any == @year and Mes == @month and Categoria == @sel_cat')
                sel_df = sel_df.drop(columns=['Any', 'Mes', 'Dia', 'Tipus', 'Categoria'])
                st.dataframe(sel_df, column_order=['Date', 'Import', 'Concepte', 'Obs'],
                        column_config={"Import": st.column_config.NumberColumn(
                        "Import",
                        help="Import en euros",
                        min_value=0,
                        max_value=1000,
                        step=0.01,
                        format="%f €",),
                        "Date":st.column_config.DateColumn(
                            "Data",
                            format="DD/MM/YYYY")},
                        hide_index=True,
                        use_container_width = True)
        else:
            if sel_cat == None:
                df_dis = add_date(df)
                sel_df = df_dis.query('Any == @year and Mes == @month and Tipus == @sel_tipus')
                sel_df = sel_df.drop(columns=['Any', 'Mes', 'Dia'])
                st.dataframe(sel_df,
                        column_config={"Import": st.column_config.NumberColumn(
                        "Import",
                        help="Import en euros",
                        min_value=0,
                        max_value=1000,
                        step=0.01,
                        format="%f €",),
                        "Date":st.column_config.DateColumn(
                            "Data",
                            format="DD/MM/YYYY"
                        )},
                        hide_index=True,
                        use_container_width = True)
            else:
                df_dis = add_date(df)
                sel_df = df_dis.query('Any == @year and Mes == @month and Categoria == @sel_cat')
                sel_df = sel_df.drop(columns=['Any', 'Mes', 'Dia', 'Tipus', 'Categoria'])
                st.dataframe(sel_df, column_order=['Date', 'Import', 'Concepte', 'Obs'],
                        column_config={"Import": st.column_config.NumberColumn(
                        "Import",
                        help="Import en euros",
                        min_value=0,
                        max_value=1000,
                        step=0.01,
                        format="%f €",),
                        "Date":st.column_config.DateColumn(
                            "Data",
                            format="DD/MM/YYYY")},
                        hide_index=True,
                        use_container_width = True)
# Vista anual

with tab20:
    # year = st.radio('Any', options=id_years, horizontal = True, label_visibility='collapsed')
    st.markdown("### **Balanç anual %s**" % (year))
    #Metrics amb diferents medidors a triar
    col10, col11, col12, col13 = st.columns(4)

    with col10:
        #Gast en oci en l'any
        st.metric(label='Oci',
                value='{:,.2f} €'.format(gast_any(bf, year, 'Oci')),
                delta='{:,.2f} €'.format(gast_any(bf, year, 'Oci')-gast_any(bf, year - 1, 'Oci')),
                delta_color='inverse')
        st.metric(label='',
                value = '{:,.2f} %'.format(gast_any(bf, year, 'Oci')*100/(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))))
    with col11:
        #Gast fixe en l'any
        st.metric(label='Fixe',
                value='{:,.2f} €'.format(gast_any(bf, year, 'Fixe')),
                delta='{:,.2f} €'.format(gast_any(bf, year, 'Fixe')-gast_any(bf, year - 1, 'Fixe')),
                delta_color='inverse')
        st.metric(label='',
                value = '{:,.2f} %'.format(gast_any(bf, year, 'Fixe')*100/(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))))
    with col12:
        #Despeses totals de l'any
        st.metric(label='Despesa anual',
                value='{:,.2f} €'.format(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe')),
                delta='{:,.2f} €'.format(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe')-gast_any(bf, year - 1, 'Oci')-gast_any(bf, year - 1, 'Fixe')),
                delta_color='inverse')
        #Esforç econòmic
        perc_year = (gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))*100/gast_any(bf, year, 'Income')
        st.metric(label='Esforç econòmic',
                  value='{:,.2f} %'.format(perc_year))
        color_perc('{:,.2f} %'.format(perc_year), perc_year) 
    with col13:
        #Balanç de l'any
        bal_year = gast_any(bf,year,'Income')-(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))
        st.metric(label='Balanç anual', value='{:,.2f} €'.format(bal_year), delta='')
        change_color('{:,.2f} €'.format(bal_year), bal_year)


    # Gràfiques distribució anual per mesos
    yf = bf.query('Any == @year').groupby(by=['Mes', 'Tipus'], as_index=False, observed=True).sum().sort_values(by=['Mes', 'Tipus'])
    k = 0
    for i in range(1,13):
        for tipus in yf.Tipus.unique():  
            yf.loc[k, 'Mean'] = gast_any(bf,year,tipus) / 12
            k += 1
    mean_gast = yf.query('Tipus != "Income"').groupby(by=['Mes'], as_index=False, observed=True).sum()
    if year == year_actual:
        month_range = range(1,month_actual+1)
    else:
        month_range = range(1,13)
    mean_gast = mean_gast.query('Mes in @month_range')
    yf['Cost'] = 1
    yf['Cost'] = yf['Cost'].where(yf['Tipus'] == 'Income', -1)
    mean_income = yf.query('Mes in @month_range')
    fig = px.bar(yf, x='Mes', y='Import', color = 'Tipus', hover_data='Tipus', barmode='group', color_discrete_map=dict_color,
                    category_orders = dict_order)
    fig.update_traces(hovertemplate='%{customdata} <br>%{value:,.0f} €')
    fig.add_trace(go.Scatter(x=mean_income.query('Tipus == "Income"')['Mes'], y=mean_income.query('Tipus == "Income"')['Import'],
                                name='Income mean', mode = 'lines', line={'shape':'spline', 'dash':'dot', 'color':'green'},
                                showlegend=False, hoverinfo='none'))
    fig.add_trace(go.Scatter(x=mean_gast['Mes'], y=mean_gast['Import'],
                                name='Despeses mean', mode = 'lines', hoverinfo='none',
                                hoveron = 'fills', line={'shape':'spline', 'dash':'dot', 'color':'red'}, showlegend=False))
    fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
    fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,',
                      legend = dict(title=None, orientation='h',yanchor='bottom', y=1, xanchor='left', x=0))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(summary_yearly[year].style.applymap(color_dif, subset=('Balance', summary_yearly[year].columns))\
                 .format('{:,.2f} €').format('{:,.2f} %', subset=('Esforç', summary_yearly[year].columns)), use_container_width=True)
    
    year_col_1, year_col_2 = st.columns(2)

    with year_col_1:
        st.markdown('## Oci')
        oci_df = bf.query('Tipus == "Oci" and Any == @year')
        fig_oci = px.bar(oci_df, x='Mes', y='Import', color = 'Categoria', color_discrete_map=col_cat)
        fig_oci.update_traces(hovertemplate='%{value:,.0f} €')
        fig_oci.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig_oci.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,', showlegend=True,
                               legend = dict(title=None, orientation='h',yanchor='bottom', y=1.15, xanchor='left', x=-0.15))
        st.plotly_chart(fig_oci, use_container_width=True)
        st.dataframe(expenses_yearly[year].style.format('{:,.2f} €').background_gradient(cmap='RdYlGn_r', axis=0),
                     use_container_width=True)
    with year_col_2:
        st.markdown('## Fixe')
        fixe_df = bf.query('Tipus == "Fixe" and Any == @year')
        fig_fixe = px.bar(fixe_df, x='Mes', y='Import', color = 'Categoria', color_discrete_map=col_cat)
        fig_fixe.update_traces(hovertemplate='%{value:,.0f} €')
        fig_fixe.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig_fixe.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,', showlegend=True,
                               legend = dict(title=None, orientation='h',yanchor='bottom', y=1.15, xanchor='center', x=0))
        st.plotly_chart(fig_fixe, use_container_width=True)
    





# Històric

with tab30:
    st.markdown("### **Balanç històric**")

    #Metrics amb diferents medidors a triar
    col10, col11, col12, col13 = st.columns(4)

    with col10:
        #Gast en oci històric
        st.metric(label='Oci',
                value='{:,.2f} €'.format(gast_total(bf, 'Oci')))
        st.metric(label='',
                value = '{:,.2f} %'.format(gast_total(bf, 'Oci')*100/(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))))
    with col11:
        #Gast fixe històric
        st.metric(label='Fixe',
                value='{:,.2f} €'.format(gast_total(bf, 'Fixe')))
        st.metric(label='',
                value = '{:,.2f} %'.format(gast_total(bf, 'Fixe')*100/(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))))
    with col12:
        #Despeses totals històriques
        st.metric(label='Despesa total',
                value='{:,.2f} €'.format(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe')))
        #Esforç econòmic
        st.metric(label='Esforç econòmic',
                  value='{:,.2f} %'.format((gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))*100/gast_total(bf,'Income')))
    with col13:
        #Balanç del mes
        bal = gast_total(bf,'Income')-(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))
        st.metric(label='Balanç', value='{:,.2f} €'.format(bal), delta='')

    xf = af.groupby(by=['Any', 'Tipus'], as_index=False, observed=True).sum()
    gast = xf.reset_index().query('Tipus == "Oci" or Tipus == "Fixe"').groupby(by=['Any']).sum().get('Import').reset_index()
    fig = px.bar(xf, x='Any', y='Import', color = 'Tipus', hover_data='Tipus', barmode='group', color_discrete_map=dict_color,
                 category_orders = dict_order)
    fig.update_traces(hovertemplate='%{customdata} <br>%{value:,.0f} €')
    fig.add_trace(go.Scatter(x=xf.query('Tipus == "Income"')['Any'], y=xf.query('Tipus == "Income"')['Import'],
                                name='Income mean', mode = 'lines', line={'shape':'spline', 'dash':'dot', 'color':'green'},
                                showlegend=False, hoverinfo='none'))
    fig.add_trace(go.Scatter(x=gast['Any'], y=gast['Import'],
                                name='Income mean', mode = 'lines', line={'shape':'spline', 'dash':'dot', 'color':'red'},
                                showlegend=False, hoverinfo='none'))
    fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
    fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,',
                      legend = dict(title=None, orientation='h',yanchor='bottom', y=1, xanchor='left', x=0))
    st.plotly_chart(fig, use_container_width=True)


    st.dataframe(summary.style.applymap(color_dif, subset=('Balance',summary.columns)).format('{:,.2f} €').format('{:,.2f} %', subset=('Esforç', summary.columns)),
                 use_container_width = True)
    
    

    # from st_aggrid import AgGrid

    # AgGrid(summary)
    exp_col_1, exp_col_2 = st.columns(2)

    with exp_col_1:
        st.markdown('## Oci')
        oci_df = af.query('Tipus == "Oci"')
        fig_oci = px.bar(oci_df, x='Any', y='Import', color = 'Categoria', color_discrete_map=col_cat)
        fig_oci.update_traces(hovertemplate='%{value:,.0f} €')
        fig_oci.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig_oci.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,', showlegend=True,
                               legend = dict(title=None, orientation='h',yanchor='bottom', y=1.15, xanchor='left', x=-0.15))
        st.plotly_chart(fig_oci, use_container_width=True)
        choice = st.radio('Gradient direction', options=['Per categoria', 'Per any'], horizontal=True)
        auxie = 0
        if choice == 'Per categoria':
            auxie = 1
        elif choice == 'Per any':
            auxie = 0
        st.dataframe(expenses_table.style.format('{:,.2f} €').background_gradient(cmap='RdYlGn_r', axis=auxie),
                     use_container_width=True)
    with exp_col_2:
        st.markdown('## Fixe')
        fixe_df = af.query('Tipus == "Fixe"')
        fig_fixe = px.bar(fixe_df, x='Any', y='Import', color = 'Categoria', color_discrete_map=col_cat)
        fig_fixe.update_traces(hovertemplate='%{value:,.0f} €')
        fig_fixe.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig_fixe.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,', showlegend=True,
                               legend = dict(title=None, orientation='h',yanchor='bottom', y=1.15, xanchor='center', x=0))
        st.plotly_chart(fig_fixe, use_container_width=True)


# Models

with tab40:
    st.markdown('### **Models**')
    models_cat, fi, scores_mean, scores_cat, preds_cat = generate_cat_models(mf_cat, plot=False, n_splits=n_splits, test_size=12)
    st.write(models_cat['Transport'].get_params())
