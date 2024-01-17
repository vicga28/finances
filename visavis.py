import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import calendar
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(layout='wide', initial_sidebar_state='expanded', page_title='Finances', page_icon='📈',
                   menu_items={'About':'Primera versió'})

# '''**Què puc fer si el meu banc no apareix?**<br>\
#                                Estem encara introduïnt diferents bancs, si us plau, tingues paciència. Estem intentant introduir tots els bancs possibles.<br>
#                                **Puc fixar un límit mensual i veure si la meva previsió es troba dins del meu límit?**<br>\
#                                Sí, és una funció que volem implementar. Tingues paciència i aviat la veuràs.'''

#Agafar el excel del Google Drive
url = 'https://docs.google.com/spreadsheets/d/1-KM3qtwtaNIjkozkcwQl0IpO2egAu3-W/edit?usp=sharing&ouid=104408176399032842446&rtpof=true&sd=true'
path = 'https://drive.google.com/uc?export=download&id='+url.split('/')[-2]
df = pd.read_excel(path, sheet_name='DATA')

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

#DataFrame amb despeses per categoria mensuals
bf = df.copy()
bf = bf.filter(['Any', 'Mes', 'Tipus', 'Categoria', 'Import'])
# bf = bf.loc[(bf.Import !=0)]
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
if sel_month is None:
    month = month_actual
    if year is None:
        year = year_actual
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

col10, col11, col12, col13 = st.columns(4)

with col10:
    st.metric(label='Oci',
            value='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')),
            delta='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')-gast_mes(bf, last_month, last_year, 'Oci')),
            delta_color='inverse')
with col11:
    st.metric(label='Fixe',
            value='{:,.2f}€'.format(gast_mes(bf, month, year, 'Fixe')),
            delta='{:,.2f}€'.format(gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Fixe')),
            delta_color='inverse')
with col12:
    st.metric(label='Despesa mensual',
            value='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')),
            delta='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')+gast_mes(bf, month, year, 'Fixe')-gast_mes(bf, last_month, last_year, 'Oci')-gast_mes(bf, last_month, last_year, 'Fixe')),
            delta_color='inverse')
with col13:
    st.metric(label='Previsió gast mensual',
            value='{:,.2f}€'.format(gast_mes(bf, month, year, 'Oci')*num_days/day_actual+gast_mes(bf, month, year, 'Fixe')),
            delta='{:,.2f}€'.format(gast_mes(bf, last_month, last_year, 'Income')-gast_mes(bf, month, year, 'Oci')*num_days/day_actual-gast_mes(bf, month, year, 'Fixe')),
            delta_color='normal')

col21, col22 = st.columns([6,4])

with col21:
    tab1, tab2 = st.tabs(['Vista anual', 'Històric'])
    with tab1:
        yf = bf.query('Any == @year').groupby(by=['Mes', 'Tipus'], as_index=False, observed=True).sum()
        yf['Cost'] = 1
        yf['Cost'] = yf['Cost'].where(yf['Tipus'] == 'Income', -1)
        st.markdown('### Balanç anual %s' % (year))
        # fig = px.bar(yf, x='Cost', y='Import', color = 'Tipus', hover_data='Tipus', barmode='group', facet_col='Mes')
        # fig.update_traces(hovertemplate='%{customdata} <br>%{value:.02f} €')
        # fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        # fig.update_layout(yaxis_ticksuffix='€',yaxis_tickformat=',.')
        # st.plotly_chart(fig, use_container_width=True)
        fig = px.bar(yf, x='Mes', y='Import', color = 'Tipus', hover_data='Tipus', barmode='group')
        fig.update_traces(hovertemplate='%{customdata} <br>%{value:,.0f} €')
        fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig.update_layout(yaxis_ticksuffix='€', yaxis_tickformat=',', separators='.,')
        st.plotly_chart(fig, use_container_width=True)
        if sel_cat is None:
            if sel_tipus == 'Gast':
                st.markdown('### Despeses %s' % ( year))
                zf = bf.query('Any == @year').copy()
                zf_oci = zf[zf.Tipus == 'Oci']
                zf_fixe = zf[zf.Tipus == 'Fixe']
                zf = zf_oci.append(zf_fixe).groupby(by=['Any', 'Mes', 'Tipus'], as_index=False, observed=True).sum()
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