import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import calendar
import plotly.express as px
from dateutil.relativedelta import relativedelta
import streamlit.components.v1 as components
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from dataframe import update_cached_dataframe_with_gsheet


from auth import get_gspread_auth, authenticate_gspread, load_data
from plot import generate_plot
from style import format_euro, format_perc, format_titol

st.set_page_config(layout='wide', initial_sidebar_state='collapsed', page_title='Finances', page_icon='📈',
                   menu_items={'About':'Un dashboard per ajudar a la gestió de les finances personals.'})


# Now you can access the credentials as a dictionary
credentials = {
    "type": "service_account",
    "project_id": st.secrets['project_id'],
    "private_key_id": st.secrets['private_key_id'],
    "private_key": st.secrets['private_key'].replace('\\n','\n'),
    "client_email": st.secrets['client_email'],
    "client_id": st.secrets['client_id'],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": st.secrets['client_x509_cert_url']
}
input_spreadsheet_id = st.secrets['INPUT_SPREADSHEET_ID']
output_spreadsheet_id = st.secrets['OUTPUT_SPREADSHEET_ID']

# Carrega l'autenticació de Google
gspread_auth = get_gspread_auth(credentials)

print('Script running...')

#Agafar el excel del Google Drive
client = authenticate_gspread(credentials)
df = load_data(credentials, input_spreadsheet_id, sheet_name='DATA')

#Generació id categories per a fer servir després pels inputs

def generate_id(df):
    id_tip = df['Tipus'].unique()
    id_cat = df.query('Tipus == "Oci"')['Categoria'].unique()
    id_fixe = df.query('Tipus == "Fixe"')['Categoria'].unique()
    id_cat_total = np.append(id_cat, id_fixe)
    id_years = np.sort(df['Any'].unique())[::-1]
    dict_cat = {}
    for tipus in id_tip:
        dict_cat[tipus] = df.query('Tipus == @tipus')['Categoria'].unique()
    return id_tip, id_cat, id_fixe, id_cat_total, id_years, dict_cat

id_tip, id_cat, id_fixe, id_cat_total, id_years, dict_cat = generate_id(df)


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

# #Triant els colors de les gràfiques
vivid = px.colors.qualitative.Vivid
col_cat = {'Transport':vivid[10], 'Tabac':vivid[0], 'Beguda':vivid[7], 'Restaurant':vivid[9], 'Entrades':vivid[2],
           'Subscripcions':vivid[3], 'Supermercat':vivid[5], 'Compres':vivid[6], 'Altres':vivid[1]}


#Funcions
@st.cache_data
def fill_dataframe(df, year):
    if year == year_actual:
        bf = df.copy()
        bf['Data'] = bf.index
        bf['Data'] = bf['Data'].apply(neteja_data)
        bf['Data'] = pd.to_datetime(bf['Data'])
        #Generació d'un segon DataFrame (dummy) on es generen entrades per a cada dia i categoria amb import 0
        first_day = date(year_actual, 1, 1)
        last_day = date(year_actual, 12, 31)
        time_series = pd.date_range(start=first_day, end=last_day)
        df_zero = pd.DataFrame([0], columns=['Import'])
        i=0
        options = df['Concepte'].unique()
        for data in time_series:
            for opt in options:
                df_zero.loc[i, 'Data'] = data
                df_zero.loc[i, 'Concepte'] = opt
                df_zero.loc[i, 'Import'] = 0
                i+=1 
        #Unió dels dos DataFrames i retornar un únic per tenir valors de 0 per les categories on no hi ha despeses per un determinat mes
        bf = df_zero.merge(bf, on=['Data', 'Concepte'], how='left')
        bf = bf.fillna(0).drop(columns='Import_x').rename(columns={'Import_y':'Import'}).set_index('Data')
        bf['Any'] = bf.index.year
        bf['Mes'] = bf.index.month
        #Sumar imports de cada categoria mensualment
        bf = bf[['Any', 'Mes', 'Concepte', 'Import']].groupby(by=['Any', 'Mes', 'Concepte'], as_index=False, observed=True).sum()
        af = bf.filter(['Any', 'Concepte', 'Import']).groupby(by=['Any', 'Concepte'], as_index=False, observed=True).sum()
    else:
        bf = df.copy()
    return bf

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

def neteja_data(val):
    try:
        parts = str(val).split('-')
        any_ = int(float(parts[0]))
        mes = int(float(parts[1]))
        return f"{any_}-{mes:02d}"
    except:
        return None  # o pd.NaT

# Generar gràfiques per a oci/fixe/income
@st.cache_data
def generate_tipus_df(df, id_tip = id_tip):
    bf = df.copy()
    mf_tipus = {}
    for tipus in id_tip:
        mf_tipus['{}'.format(tipus)] = bf.query('Tipus == @tipus').drop(columns=['Categoria']).groupby(by=['Mes', 'Any', 'Tipus'], as_index=False).sum().sort_values(by=['Any', 'Mes'])
        mf_tipus[tipus]['Data'] = mf_tipus[tipus]['Any'].astype('string') + '-' + mf_tipus[tipus]['Mes'].astype('string')
        mf_tipus[tipus]['Data_clean'] = mf_tipus[tipus]['Data'].apply(neteja_data)
        mf_tipus[tipus]['Date'] = pd.to_datetime(mf_tipus[tipus]['Data_clean'], format='%Y-%m')
        mf_tipus[tipus]['Date'] = mf_tipus[tipus]['Date'].dt.date
        mf_tipus[tipus] = mf_tipus[tipus][mf_tipus[tipus]['Date'] < date.today()].sort_values('Date', ascending=False).drop(columns=['Data'])
        mf_tipus[tipus] = mf_tipus[tipus].set_index('Date').drop(columns=['Tipus'])
    return mf_tipus

# Generació DataFrames respecte categories
@st.cache_data
def generate_cat_df(bf, id_cat = id_cat):
    mf = bf.copy()
    mf['Data'] = mf['Any'].astype('string') + '-' + mf['Mes'].astype('string')
    mf['Data_clean'] = mf['Data'].apply(neteja_data)
    mf['Date'] = pd.to_datetime(mf['Data_clean'], format='%Y-%m')
    mf['Date'] = mf['Date'].dt.date
    mf = mf[mf['Date'] < date.today()].sort_values('Date', ascending=False)
    df = mf[:(14*6)]
    mf_cat = {}
    df_cat = {}
    for cat in id_cat:
        mf_grouped = mf.query("Categoria == @cat").groupby(['Mes', 'Any'], as_index=False)[['Import']].sum().sort_values(['Any', 'Mes'])
        mf_grouped['Date'] = pd.to_datetime(mf_grouped['Any'].astype(str) + '-' + mf_grouped['Mes'].astype(str), format='%Y-%m')
        df_grouped = df.query("Categoria == @cat").groupby(['Mes', 'Any'], as_index=False)[['Import']].sum().sort_values(['Any', 'Mes'])
        df_grouped['Date'] = pd.to_datetime(df_grouped['Any'].astype(str) + '-' + mf_grouped['Mes'].astype(str), format='%Y-%m')
        mf_cat[cat] = mf_grouped.set_index('Date')
        df_cat[cat] = df_grouped.set_index('Date')
        # mf_cat['{}'.format(cat)] = mf.query('Categoria == @cat').groupby(by=['Mes', 'Any'], as_index=False)[['Import']].sum().sort_values(by=['Any', 'Mes']).drop(columns=['Data'])
        # df_cat['{}'.format(cat)] = df.query('Categoria == @cat').groupby(by=['Mes', 'Any'], as_index=False)[['Import']].sum(numeric_only=True).sort_values(by=['Any', 'Mes']).drop(columns=['Data'])
        # mf_cat[cat] = mf_cat[cat].set_index('Date').drop(columns=['Tipus', 'Categoria'])
        # df_cat[cat] = df_cat[cat].set_index('Date').drop(columns=['Tipus', 'Categoria'])
    return mf_cat, df_cat

# Funció per obtenir informació de les dates
@st.cache_data
def get_datetime_info(df):
    bf = df.copy()
    bf['Data'] = bf['Any'].astype('string') + '-' + bf['Mes'].astype('string')
    bf['Data_clean'] = bf['Data'].apply(neteja_data)
    bf['Date'] = pd.to_datetime(bf['Data_clean'], format='%Y-%m')
    bf['Date'] = bf['Date'].dt.date
    bf = bf[bf['Date'] < date.today()].sort_values('Date', ascending=False).drop(columns=['Data'])
    bf = bf.set_index('Date')
    date_0 = bf.index.min()
    end_date = date.today()
    daterange = end_date - date_0
    diff_years = relativedelta(end_date, date_0).years
    return bf, date_0, diff_years, daterange

# Afegir una columna amb la data
@st.cache_data
def add_date(df):
    df = df.copy()
    df['Data'] = df['Any'].astype('string') + '-' + df['Mes'].astype('string') + '-' + df['Dia'].astype('string')
    df['Data_clean'] = df['Data'].apply(neteja_data)
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

#Generar DatafFrame
bf, af = update_cached_dataframe_with_gsheet(input_spreadsheet_id, output_spreadsheet_id, credentials, bf_sheet_name='bf', af_sheet_name='af')
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

gc = get_gspread_auth(credentials)
output_sh = gc.open_by_key(output_spreadsheet_id)
try:
    lim_cat_old = get_as_dataframe(output_sh.worksheet('limits')).dropna(how="all")
    lim_cat = dict(zip(lim_cat_old['Categoria'], lim_cat_old['Limit']))
except:
    lim_cat = dict.fromkeys(id_cat, 0)

table_cat = create_table(df, lim_cat=lim_cat, month=month, year=year)


#Pàgina principal
st.title('Dashboad finances')

tab10, tab20, tab30, tab40, tab50 = st.tabs(['Distribució mensual', 'Vista anual', 'Històric', 'Models', 'Configuració'])

# Configuració

with tab50:
    st.markdown('### Configuració')
    st.markdown('Límits')

    with st.form('limits_form', border=True):
        row1 = st.columns(4)
        row2 = st.columns(4)
        row3 = st.columns(4)
        i = 0
        for col in row1 + row2 + row3:
            if i < len(id_cat):
                tile = col.container()
                lim_cat[id_cat[i]] = tile.number_input(label=id_cat[i], min_value=0, format='%d', placeholder='Límit {}'.format(id_cat[i]), key='lim_{}'.format(id_cat[i]), value=int(lim_cat[id_cat[i]]), help='Límit disposat a gastar en euros (€).')
                i += 1
        submitted = st.form_submit_button('Guardar')
    lim_sum = sum(lim_cat[cat] for cat in id_cat)
    if submitted:
        lim_sum = 0
        for cat in id_cat:
            lim_sum = lim_sum + lim_cat[cat]
        try:
            lim_sheet = output_sh.worksheet('limits')
        except:
            lim_sheet = output_sh.add_worksheet(title='limits', rows=1000, cols=20)
        lim_sheet.clear()
        df_lim = pd.DataFrame({'Categoria': lim_cat.keys(), 'Limit': lim_cat.values()})
        set_with_dataframe(lim_sheet, df_lim)
    st.write(f'La quantitat total considerada pels límits és de {format_titol(lim_sum)}.')

@st.fragment
def mostrar_despeses():
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
            sel_df = sel_df.set_index('Date').drop(columns=['Any', 'Mes', 'Dia', 'Data_clean'])
            st.dataframe(sel_df.style.format(format_euro, subset=['Import']),
                    column_config={
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
            st.dataframe(sel_df.style.format(format_euro, subset=['Import']), column_order=['Date', 'Import', 'Concepte', 'Obs'],
                    column_config={
                    "Date":st.column_config.DateColumn(
                        "Data",
                        format="DD/MM/YYYY")},
                    hide_index=True,
                    use_container_width = True)
    else:
        if sel_cat == None:
            df_dis = add_date(df)
            sel_df = df_dis.query('Any == @year and Mes == @month and Tipus == @sel_tipus')
            sel_df = sel_df.set_index('Date').drop(columns=['Any', 'Mes', 'Dia'])
            st.dataframe(sel_df.style.format(format_euro, subset=['Import']), column_order=['Date', 'Import', 'Tipus', 'Categoria', 'Concepte', 'Obs'],
                    column_config={
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
            st.dataframe(sel_df.style.format(format_euro, subset=['Import']), column_order=['Date', 'Import', 'Concepte', 'Obs'],
                    column_config={
                    "Date":st.column_config.DateColumn(
                        "Data",
                        format="DD/MM/YYYY")},
                    hide_index=True,
                    use_container_width = True)
    return



# Distribució mensual

with tab10:
    st.markdown("### **%s %s**" % (dict_month[month], year))

    #Metrics amb diferents medidors a triar
    col10, col11, col12, col13 = st.columns(4)

    with col10:
        #Gast en oci en el mes seleccionat
        st.metric(label='Oci',
                value=format_euro(gast_mes(bf, month, year, 'Oci')),
                delta=format_euro(gast_mes(bf, month, year, 'Oci')-gast_mes(bf, last_month, last_year, 'Oci')),
                delta_color='inverse')
        if (gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')) != 0:
            st.metric(label='Percentatge Oci',
                    value = format_perc(gast_mes(bf, month, year, 'Oci')*100/(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))),
                    label_visibility = 'hidden')
    with col11:
        #Gast fixe en el mes seleccionat
        st.metric(label='Fixe',
                value=format_euro(gast_mes(bf, month, year, 'Fixe')),
                delta=format_euro(gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Fixe')),
                delta_color='inverse')
        if (gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')) != 0:
            st.metric(label='Percentatge Fixe',
                    value = format_perc(gast_mes(bf, month, year, 'Fixe')*100/(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))),
                    label_visibility = 'hidden')
    with col12:
        #Despeses totals del mes seleccionat
        st.metric(label='Despesa mensual',
                value=format_euro(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')),
                delta=format_euro(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Oci')-gast_mes(bf, last_month, last_year, 'Fixe')),
                delta_color='inverse')
        income = get_income(bf, month, year)
        if income == 0:
            st.metric(label='Esforç econòmic',
                    value = format_perc((gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))*100/get_income(bf, last_month, last_year)))
        else:
            st.metric(label='Esforç econòmic',
                    value = format_perc((gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))*100/income))
    with col13:
        if month == month_actual:
            #Previsió de gast del mes present
            prev = gast_mes(bf, month, year, 'Oci')*num_days/day_actual+gast_mes(bf, month, year, 'Fixe')
            st.metric(label='Previsió gast mensual',
                    value=format_euro(prev),
                    delta=format_euro(gast_mes(bf, last_month, last_year, 'Income')-prev),
                    delta_color='normal')
        else:
            #Balanç del mes
            bal = gast_mes(bf,month,year,'Income')-(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe'))
            st.metric(label='Balanç mensual', value=format_euro(bal), delta='')
            change_color(format_euro(bal), bal)
        st.metric(label='Gast promig diari',
                  value = format_euro((gast_mes(bf, month, year, 'Oci')/day_actual)))

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
        table_cat = table_cat.sort_values(['Import'], ascending=False).style.map(color_dif, subset=['Diff'])\
            .format(format_euro, subset=(['Import', 'Limit', 'Diff']))\
            .format(format_perc, subset=('Percentatge'))\
            .background_gradient(cmap='RdYlGn_r', subset=['Percentatge'], vmax=100, vmin=0)
        st.dataframe(table_cat, column_order=['Import', 'Percentatge', 'Limit', 'Diff', 'Trend'],
                     column_config={'Trend':st.column_config.LineChartColumn('Últims 6 mesos', y_min = 0)},
                     use_container_width = True)
        
    #Taula per veure despeses per mes amb filtres 
    with st.expander('Veure despeses'):
        mostrar_despeses()

serveis = ['Aigua', 'Gas', 'Electricitat', 'WiFi']


def create_lloguer(df = df, year_actual = year, plot=False):
    fixe = df[df['Tipus'] ==  'Fixe']
    fixe_lloguer = fixe[fixe['Categoria'] == 'Lloguer']
    fixe_lloguer = fixe_lloguer.drop(columns=['Dia']).groupby(by=['Any', 'Mes', 'Concepte'], as_index=False, observed=True).sum()
    fixe_lloguer['Dia'] = 1
    fixe_lloguer = add_date(fixe_lloguer)
    fixe_lloguer = fixe_lloguer.drop(columns=['Tipus', 'Dia', 'Obs']).set_index(['Date'])
    if plot:
        st.write("Lloguer")
        fig_lloguer = px.bar(fixe_lloguer, x=fixe_lloguer.index, y='Import', color='Concepte')
        st.plotly_chart(fig_lloguer)

    lloguer_year = fixe_lloguer[fixe_lloguer['Any'] == year_actual]
    if plot:
        fig_lloguer_year = px.bar(lloguer_year, x=lloguer_year.index, y='Import', color='Concepte')
        st.plotly_chart(fig_lloguer_year)

    df_lloguer = fixe_lloguer.groupby(by=['Any', 'Mes'], as_index=False, observed=True).sum()
    df_lloguer['Dia'] = 1
    df_lloguer = add_date(df_lloguer)
    df_lloguer = df_lloguer.drop(columns=['Dia', 'Concepte']).set_index(['Date'])
    df_year_lloguer = df_lloguer[df_lloguer['Any'] == year_actual]
    mean_last_lloguer = df_lloguer['Import'][-12:].mean()
    mean_year_lloguer = df_year_lloguer['Import'].mean()
    return fixe_lloguer, lloguer_year, mean_last_lloguer, mean_year_lloguer

def create_serveis(df = df, serveis = serveis, year_actual = year, plot = False):
    fixe = df[df['Tipus'] ==  'Fixe']
    fixe_serveis = fixe[fixe['Categoria'] == 'Serveis']
    dict_serveis = {}
    fig_serveis = {}
    dict_mean_serveis = {} # Mitja últim any de cada servei
    dict_year_serveis = {}
    for servei in serveis:
        dict_serveis[servei] = fixe_serveis [fixe_serveis['Concepte'] == servei].drop(columns=['Dia']).groupby(by=['Any', 'Mes'], as_index=False, observed=True).sum()
        dict_serveis[servei]['Dia'] = 1
        dict_serveis[servei] = add_date(dict_serveis[servei])
        dict_serveis[servei] = dict_serveis[servei].drop(columns=['Tipus', 'Dia', 'Categoria', 'Obs', 'Concepte']).set_index(['Date'])
        dict_year_serveis[servei] = dict_serveis[servei][dict_serveis[servei]['Any'] == year_actual]['Import'].mean()
        if plot:
            st.write(servei)
            fig_serveis[servei] = px.bar(dict_serveis[servei], x=dict_serveis[servei].index, y='Import')
            st.plotly_chart(fig_serveis[servei])
        if servei == 'Aigua' or servei == 'Gas':
            dict_mean_serveis[servei] = dict_serveis[servei]['Import'][-6:].mean()
        else:
            dict_mean_serveis[servei] = dict_serveis[servei]['Import'][-12:].mean()

    fixe_serveis_global = fixe_serveis.drop(columns=['Dia']).groupby(by=['Any', 'Mes', 'Concepte'], as_index=False, observed=True).sum()
    fixe_serveis_global['Dia'] = 1
    fixe_serveis_global = add_date(fixe_serveis_global)
    fixe_serveis_global = fixe_serveis_global.drop(columns=['Tipus', 'Dia', 'Categoria', 'Obs']).set_index(['Date'])
    fixe_serveis_year = fixe_serveis_global[fixe_serveis_global['Any'] == year_actual]
    if plot:
        fig_lloguer_global = px.bar(fixe_serveis_global, x=fixe_serveis_global.index, y='Import', color='Concepte')
        st.plotly_chart(fig_lloguer_global)

    df_year_serveis = fixe_serveis.groupby(by=['Any', 'Mes'], as_index=False, observed=True).sum()
    df_year_serveis['Dia'] = 1
    df_year_serveis = add_date(df_year_serveis)
    df_year_serveis = df_year_serveis.drop(columns=['Dia', 'Concepte', 'Categoria', 'Tipus', 'Obs']).set_index(['Date'])

    mean_last_serveis = df_year_serveis['Import'][-12:].mean()

    df_year_serveis = df_year_serveis[df_year_serveis['Any'] == year_actual]
    mean_year_serveis = df_year_serveis['Import'].mean()

    return dict_serveis, df_year_serveis, fixe_serveis_global, fixe_serveis_year, dict_mean_serveis, mean_last_serveis, mean_year_serveis, dict_year_serveis

def create_income(df = df, year_actual = year, plot = False):
    nomina = df[df['Tipus'] ==  'Income']
    nomina = nomina[nomina['Categoria'] == 'Nomina']
    nomina = nomina.drop(columns=['Dia']).groupby(by=['Any', 'Mes'], as_index=False, observed=True).sum()
    nomina['Dia'] = 1
    nomina = add_date(nomina)
    nomina = nomina.drop(columns=['Tipus', 'Dia', 'Categoria', 'Obs']).set_index(['Date'])
    if plot:
        fig_nomina = px.bar(nomina, x=nomina.index, y='Import', color='Concepte')
        st.plotly_chart(fig_nomina)
    nomina_year = nomina[nomina['Any'] == year_actual]
    mean_last_nomina = nomina['Import'][-12:].mean()
    mean_year_nomina = nomina_year['Import'].mean()
    return nomina, nomina_year, mean_year_nomina, mean_last_nomina


# Generacio DataFrames pels gràfics i mitges de les despeses fixes i nomina
nomina, nomina_year, mean_year_nomina, mean_last_nomina = create_income(df = df, year_actual=year)
lloguer, lloguer_year, mean_last_lloguer, mean_year_lloguer = create_lloguer(df= df, year_actual=year, plot=False)
dict_serveis, df_year_serveis, serveis_hist, serveis_year, dict_mean_serveis, mean_last_serveis, mean_year_serveis, dict_year_serveis = create_serveis(df= df, year_actual=year)


# Vista anual

with tab20:
    st.markdown("### **Balanç anual %s**" % (year))
    #Metrics amb diferents medidors a triar
    col10, col11, col12, col13 = st.columns(4)

    with col10:
        #Gast en oci en l'any
        st.metric(label='Oci',
                value=format_euro(gast_any(bf, year, 'Oci')),
                delta=format_euro(gast_any(bf, year, 'Oci')-gast_any(bf, year - 1, 'Oci')),
                delta_color='inverse')
        st.metric(label='Percentatge Oci',
                value = format_perc(gast_any(bf, year, 'Oci')*100/(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))),
                label_visibility = 'hidden')
    with col11:
        #Gast fixe en l'any
        st.metric(label='Fixe',
                value=format_euro(gast_any(bf, year, 'Fixe')),
                delta=format_euro(gast_any(bf, year, 'Fixe')-gast_any(bf, year - 1, 'Fixe')),
                delta_color='inverse')
        st.metric(label='Percentatge Fixe',
                value = format_perc(gast_any(bf, year, 'Fixe')*100/(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))),
                label_visibility = 'hidden')
    with col12:
        #Despeses totals de l'any
        st.metric(label='Despesa anual',
                value=format_euro(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe')),
                delta=format_euro(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe')-gast_any(bf, year - 1, 'Oci')-gast_any(bf, year - 1, 'Fixe')),
                delta_color='inverse')
        #Esforç econòmic
        perc_year = (gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))*100/gast_any(bf, year, 'Income')
        st.metric(label='Esforç econòmic',
                  value=format_perc(perc_year))
        color_perc(format_perc(perc_year), perc_year) 
    with col13:
        #Balanç de l'any
        bal_year = gast_any(bf,year,'Income')-(gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))
        st.metric(label='Balanç anual', value=format_euro(bal_year), delta='')
        change_color(format_euro(bal_year), bal_year)
        st.metric(label='Gast promig mensual',
                  value = format_euro((gast_any(bf, year, 'Oci')+gast_any(bf, year, 'Fixe'))/month_actual))

    # Gràfiques distribució anual per mesos
    yf = bf.query('Any == @year').groupby(by=['Mes', 'Tipus'], as_index=False, observed=True).sum().sort_values(by=['Mes', 'Tipus'])
    fig_summary_year = generate_plot(yf, x='Mes', level='Tipus', spacing=1000, year = year)
    st.plotly_chart(fig_summary_year)

    # Taula amb resum mensual de despeses i ingressos
    st.dataframe(summary_yearly[year].style.map(color_dif, subset=('Balance', summary_yearly[year].columns))\
                 .format(format_euro).format(format_perc, subset=('Esforç', summary_yearly[year].columns)), use_container_width=True)
    

    st.header('Fixe', divider='gray')

    fixe_df = bf.query('Tipus == "Fixe" and Any == @year')
    fig_fixe_year = generate_plot(fixe_df, x='Mes', level='Categoria', spacing = 200, year = year)
    st.plotly_chart(fig_fixe_year)

    mean_year_fixe = fixe_df.groupby(['Mes']).sum().query('Import != 0')['Import'].mean()
    st.write(f"El gast promig fixe l'últim any ha estat de **{format_titol(mean_year_fixe)}**.")



    year_col_3, year_col_4 = st.columns(2)

    with year_col_3:
        st.markdown('### Lloguer')
        yearly_lloguer = fill_dataframe(lloguer_year, year=year)
        st.dataframe(yearly_lloguer)
        fig_lloguer_year = generate_plot(yearly_lloguer, x='Mes', level='Concepte', spacing=200, year = year, tipus='Lloguer')
        st.plotly_chart(fig_lloguer_year)
        st.write(f"El gast promig en lloguer l'últim any ha estat de **{format_titol(mean_year_lloguer)}**.")
   
    with year_col_4:
        st.markdown('### Serveis')
        yearly_serveis = fill_dataframe(serveis_year, year=year)
        fig_serveis_year = generate_plot(yearly_serveis, x='Mes', level='Concepte', spacing=20, year=year, tipus='Serveis')
        st.plotly_chart(fig_serveis_year)
        st.write(f"""El gast promig durant l'últim any en serveis ha estat de **{format_titol(mean_year_serveis)}**;
                 dels quals **{format_titol(dict_year_serveis['Electricitat'])}** han estat de l'*electricitat*,
                 **{format_titol(dict_year_serveis['Aigua'])}** de l'*aigua*,
                 **{format_titol(dict_year_serveis['Gas'])}** del *gas* i **{format_titol(dict_year_serveis['WiFi'])}** del WiFi.
                 """)


    st.header('Oci', divider='gray')

    # Gràfica amb despeses per categoria i mes
    oci_df = bf.query('Tipus == "Oci" and Any == @year')
    fig_oci_year = generate_plot(oci_df, x='Mes', level='Categoria', spacing=500, year=year)
    st.plotly_chart(fig_oci_year)

    mean_year_oci = oci_df.groupby(['Mes']).sum().query('Import != 0')['Import'].mean()
    st.write(f"El gast promig en oci l'últim any ha estat de **{format_titol(mean_year_oci)}**.")

    # Taula amb despeses per categoria i mes
    st.dataframe(expenses_yearly[year].sort_values(['Total'], ascending=False).style.format(format_euro).background_gradient(cmap='RdYlGn_r', axis=0),
                  use_container_width=True)


    st.header('Ingressos', divider='gray')

    # Gràfica amb ingressos per mes
    yearly_income = fill_dataframe(nomina_year, year=year)
    fig_income_year = generate_plot(yearly_income, x='Mes', level='Concepte', spacing=1000, year=year)
    st.plotly_chart(fig_income_year)
    cap1, cap2, cap3 = st.columns(3)
    with cap2:
        st.write(f"""L'ingrés promig els últims 12 mesos ha estat de **{format_titol(mean_last_nomina)}**.""")


# Històric

with tab30:
    st.markdown("### **Balanç històric**")

    df_date = load_data(credentials, input_spreadsheet_id, sheet_name='DATA')
    df_date['Data'] = df['Any'].astype('string') + '-' + df['Mes'].astype('string') + '-' + df['Dia'].astype('string')
    df_date['Data'] = pd.to_datetime(df_date['Data'], dayfirst=True, format='%Y-%m-%d')
    last_date = df_date.sort_values('Data')['Data'].iloc[-1]
    last_day = last_date.date()
    num_years = (last_day - first_day).days / 365.25

    #Metrics amb diferents medidors a triar
    col10, col11, col12, col13 = st.columns(4)

    with col10:
        #Gast en oci històric
        st.metric(label='Oci',
                value=format_euro(gast_total(bf, 'Oci')))
        st.metric(label='Percentatge Oci',
                value = format_perc(gast_total(bf, 'Oci')*100/(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))),
                label_visibility = 'hidden')
    with col11:
        #Gast fixe històric
        st.metric(label='Fixe',
                value=format_euro(gast_total(bf, 'Fixe')))
        st.metric(label='Percentatge Fixe',
                value = format_perc(gast_total(bf, 'Fixe')*100/(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))),
                label_visibility = 'hidden')
    with col12:
        #Despeses totals històriques
        st.metric(label='Despesa total',
                value=format_euro(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe')))
        #Esforç econòmic
        st.metric(label='Esforç econòmic',
                  value=format_perc((gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))*100/gast_total(bf,'Income')))
    with col13:
        #Balanç total
        bal = gast_total(bf,'Income')-(gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))
        st.metric(label='Balanç', value=format_euro(bal), delta='')
        st.metric(label='Gast promig anual', value=format_euro((gast_total(bf, 'Oci')+gast_total(bf, 'Fixe'))/num_years), delta='')

    # Gràfica amb despeses i ingressos anuals
    xf = af.groupby(by=['Any', 'Tipus'], as_index=False, observed=True).sum()
    fig_ever = generate_plot(xf, x='Any', level='Tipus', spacing=5000, year=year)
    st.plotly_chart(fig_ever)

    # Taula amb resum anual d'ingressos i despeses
    st.dataframe(summary.style.map(color_dif, subset=('Balance',summary.columns)).format(format_euro).format(format_perc, subset=('Esforç', summary.columns)),
                 use_container_width = True)
    

    st.header('Fixe', divider='gray')
    fixe_df = af.query('Tipus == "Fixe"')
    fig_fixe_ever = generate_plot(fixe_df, x='Any', level='Categoria', spacing=2000, year=year)
    st.plotly_chart(fig_fixe_ever)


    exp_col_1, exp_col_2 = st.columns(2)

    with exp_col_1:
        st.markdown('### Lloguer')
        fig_lloguer_ever = generate_plot(lloguer, x='Any', level='Concepte', spacing=200, year=year)
        st.plotly_chart(fig_lloguer_ever)

    with exp_col_2:
        st.markdown('### Serveis')
        fig_serveis_ever = generate_plot(serveis_hist, x='Any', level='Concepte', spacing=50, year=year)
        st.plotly_chart(fig_serveis_ever)

    st.header('Oci', divider='gray')
    oci_df = af.query('Tipus == "Oci"')
    fig_oci_ever = generate_plot(oci_df, x='Any', level='Categoria', spacing=5000, year=year)
    st.plotly_chart(fig_oci_ever)

    @st.fragment
    def gradient_view():
        choice = st.radio('Gradient direction', options=['Per categoria', 'Per any'], horizontal=True)
        if choice == 'Per categoria':
            st.dataframe(expenses_table.style.format(format_euro).background_gradient(cmap='OrRd', axis=1), use_container_width=True)
        else:
            st.dataframe(expenses_table.style.format(format_euro).background_gradient(cmap='OrRd', axis=0), use_container_width=True)

    gradient_view()


# Models
with tab40:
    st.markdown('### **Models**')
    # models_cat, fi, scores_mean, scores_cat, preds_cat = generate_cat_models(mf_cat, plot=True, n_splits=5, test_size=12)
    # st.write(models_cat['Transport'].get_params())

print('Up to date!')
