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

st.set_page_config(layout='wide', initial_sidebar_state='expanded', page_title='Finances', page_icon='📈',
                   menu_items={'About':'Primera versió'})

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

client = authenticate_gspread(credentials)
spreadsheet_id = "1--akOa5R5ghC35dztP78BvrdLZYFJT6LDwKSTR0mWSk"
data = fetch_data_from_sheet(client, spreadsheet_id, worksheet_name='DATA')

#Agafar el excel del Google Drive
df = pd.DataFrame(data[1:], columns=data[0])

#Generació id categories per a fer servir després pels inputs
id_tipus = ['Despesa', 'Estalvi', 'Ingressos']
id_tipus_gast = ['Fixe', 'Oci']
id_cat = ['Transport', 'Tabac', 'Restaurant', 'Beguda', 'Entrades', 'Transferencies', 'Subscripcions', 'Supermercat', 'Compres', 'Altres']
id_fixe = ['Lloguer', 'Serveis']
id_years = np.sort(df['Any'].unique())[::-1]

dict_month = {1:'Gener', 2:'Febrer', 3:'Març', 4:'Abril', 5:'Maig', 6:'Juny',
7:'Juliol', 8:'Agost', 9:'Setembre', 10:'Octubre', 11:'Novembre', 12:'Desembre'}
dict_gast = {'Oci':id_cat, 'Fixe':id_fixe}
dict_tipus = {'Despesa':'Gast', 'Estalvi':'Estalvi', 'Ingressos':'Income'}

id_months = dict_month.values()

month_actual = date.today().month
year_actual = date.today().year
day_actual = date.today().day
num_days = calendar.monthrange(year_actual, month_actual)[-1]

#Generació DataFrames

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

#DataFrame amb despeses per categoria mensuals
bf = bf.copy()
bf = bf.filter(['Any', 'Mes', 'Tipus', 'Categoria', 'Import'])
bf = bf.groupby(by=['Any', 'Mes', 'Tipus', 'Categoria'], as_index=False, observed=True).sum()

#Dataframe amb despeses per categoria anuals 
af = df.copy()
af = af.filter(['Any', 'Tipus', 'Categoria', 'Import']).groupby(by=['Any', 'Tipus', 'Categoria'], as_index=False, observed=True).sum()

#Funcions
def gast_any(data, any, tipus):
    output = data.query('Any == @any and Tipus == @tipus').agg('sum').get('Import')
    return output

def gast_mes(data, mes, any, tipus):
    output = data.query('Any == @any and Mes == @mes and Tipus == @tipus').agg('sum').get('Import')
    return output

def get_month_number(mes):
    for i in range(1,13):
        if dict_month[i] == mes:
            month_num= i
    return month_num

def get_last_month(mes, any):
    i = mes - 1
    j = any
    if mes == 1:
        last_month = 12, j - 1
    else:
        last_month = i, j
    return last_month

#Sidebar
st.sidebar.markdown('### Selecció paràmetres')
st.sidebar.markdown('## Mes a visualitzar')
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
st.sidebar.markdown('## Categoria a visualitzar')
sel_tipus = st.sidebar.selectbox('Tipus:', id_tipus, index=None)
if sel_tipus is None:
    sel_tipus = 'Oci'
    dummy_tipus_gast = st.sidebar.selectbox('Tipus de despesa:', [''])
    dummy_cat = st.sidebar.selectbox('Categoria:', [''])
    sel_cat = None
else:
    sel_tipus_gast = st.sidebar.selectbox('Tipus de despesa:', id_tipus_gast, index=None)
    sel_tipus = dict_tipus[sel_tipus]
    sel_cat = None
    if sel_tipus_gast is None:
        dummy_cat = st.sidebar.selectbox('Categoria:', [''])
    else:
        sel_tipus = sel_tipus_gast
        sel_cat = st.sidebar.selectbox('Categoria:', dict_gast[sel_tipus_gast], index=None)

#Pàgina principal
st.title('Dashboad finances')
st.markdown("### **%s %s**" % (dict_month[month], year))

#Metrics amb diferents medidors a triar
col10, col11, col12, col13 = st.columns(4)

with col10:
    #Gast en oci en el mes seleccionat
    st.metric(label='Oci',
            value='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')),
            delta='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')-gast_mes(bf, last_month, last_year, 'Oci')),
            delta_color='inverse')
with col11:
    #Gast fixe en el mes seleccionat
    st.metric(label='Fixe',
            value='{:,.2f}€'.format(gast_mes(bf, month, year, 'Fixe')),
            delta='{:,.2f}€'.format(gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Fixe')),
            delta_color='inverse')
with col12:
    #Despeses totals del mes seleccionat
    st.metric(label='Despesa mensual',
            value='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')),
            delta='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Oci')-gast_mes(bf, last_month, last_year, 'Fixe')),
            delta_color='inverse')
with col13:
    #Previsió de gast del mes present
    prev = gast_mes(bf, month, year, 'Oci')*num_days/day_actual+gast_mes(bf, month, year, 'Fixe')
    st.metric(label='Previsió gast mensual',
            value='{:,.2f}€'.format(prev),
            delta='{:,.2f}€'.format(gast_mes(bf, last_month, last_year, 'Income')-prev),
            delta_color='normal')

#Gràfiques
col21, col22 = st.columns([6,4])

with col21:
    tab1, tab2 = st.tabs(['Vista anual', 'Històric'])
    with tab1:
        yf = bf.query('Any == @year').groupby(by=['Mes', 'Tipus'], as_index=False, observed=True).sum().sort_values(by=['Mes', 'Tipus'])
        k = 0
        for i in range(1,13):
            for tipus in yf.Tipus.unique():  
                yf.loc[k, 'Mean'] = gast_any(bf,year,tipus) / 12
                k += 1
        mean_gast = yf.query('Tipus != "Income"').groupby(by=['Mes'], as_index=False, observed=True).sum()
        yf['Cost'] = 1
        yf['Cost'] = yf['Cost'].where(yf['Tipus'] == 'Income', -1)
        st.markdown('### Balanç anual %s' % (year))
        fig = px.bar(yf, x='Mes', y='Import', color = 'Tipus', hover_data='Tipus', barmode='group')
        fig.update_traces(hovertemplate='%{customdata} <br>%{value:,.0f} €')
        fig.add_trace(go.Scatter(x=yf.query('Tipus == "Income"')['Mes'], y=yf.query('Tipus == "Income"')['Import'],
                                 name='Income mean', mode = 'lines',
                                 hoveron = 'fills', line={'shape':'linear', 'dash':'dot', 'color':'green'}))
        fig.add_trace(go.Scatter(x=mean_gast['Mes'], y=mean_gast['Import'],
                                 name='Despeses mean', mode = 'lines',
                                 hoveron = 'fills', line={'shape':'linear', 'dash':'dot', 'color':'red'}))
        fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,')
        st.plotly_chart(fig, use_container_width=True)
        if sel_cat is None:
            if sel_tipus == 'Gast':
                st.markdown('### Despeses %s' % ( year))
                zf = bf.query('Any == @year').copy()
                zf_oci = zf[zf.Tipus == 'Oci']
                zf_fixe = zf[zf.Tipus == 'Fixe']
                zf = zf_oci.append(zf_fixe).groupby(by=['Any', 'Mes', 'Tipus'], as_index=False).sum()
                fig = px.bar(zf, x='Mes', y='Import', color = 'Tipus',hover_data='Tipus')
                fig.update_traces(hovertemplate='%{customdata} <br>%{value:,.0f} €')
                fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
                fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,', showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown('### %s %s' % (sel_tipus, year))
                fig = px.bar(bf.query('Any == @year and Tipus == @sel_tipus'), x='Mes', y='Import', color = 'Categoria',hover_data='Categoria')
                fig.update_traces(hovertemplate='%{customdata} <br>%{value:,.0f} €')
                fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
                fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,', showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('### %s %s' % (sel_cat, year))
            fig = px.bar(bf.query('Any == @year and Tipus == @sel_tipus and Categoria == @sel_cat'), x='Mes', y='Import',
                         color = sns.color_palette('hls',bf.query('Any == @year and Tipus == @sel_tipus and Categoria == @sel_cat').count()['Mes']),
                         hover_data='Categoria')
            fig.update_traces(hovertemplate='%{value:,.0f} €', hoverinfo='none')
            fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
            fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,', showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with tab2:
        xf = af.groupby(by=['Any', 'Tipus'], as_index=False, observed=True).sum()
        st.markdown('### Balanç anual')
        fig = px.bar(xf, x='Any', y='Import', color = 'Tipus', hover_data='Tipus', barmode='group')
        fig.update_traces(hovertemplate='%{customdata} <br>%{value:,.0f} €')
        fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,')
        st.plotly_chart(fig, use_container_width=True)

with col22:
    tab10, tab11 = st.tabs(['Bar chart', 'Pie chart'])
    with tab10:
        st.markdown('### Distribució mensual')
        fig = px.bar(bf.query('Any == @year and Mes == @month and Tipus == "Oci"').sort_values(['Import'], ascending=False),
                    y='Categoria', x='Import', orientation ='h', color='Categoria')
        fig.update_traces(hovertemplate='%{value:,.02f} €')
        fig.update_xaxes(title='')
        fig.update_layout(showlegend=False, xaxis_ticksuffix = '€', xaxis_tickformat= ',', separators='.,')
        st.plotly_chart(fig, use_container_width=True)
    with tab11:
        st.markdown('### Distribució mensual')
        fig = px.pie(bf.query('Any == @year and Mes == @month and Tipus == "Oci"'),
                        values='Import', names='Categoria', hole=.3)
        fig.update_traces(hovertemplate='%{label} <br>%{value} €')
        st.plotly_chart(fig, use_container_width=True)
