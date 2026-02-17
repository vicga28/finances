import math
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from datetime import date

from style import format_titol

dict_month = {1:'Gener', 2:'Febrer', 3:'Març', 4:'Abril', 5:'Maig', 6:'Juny',
7:'Juliol', 8:'Agost', 9:'Setembre', 10:'Octubre', 11:'Novembre', 12:'Desembre'}

month_actual = date.today().month
year_actual = date.today().year

#Triant els colors de les gràfiques
palette = px.colors.qualitative.T10
dict_color = {'Income':palette[4], 'Oci':palette[2], 'Fixe':palette[1], 'Estalvi':palette[9]}
bold = px.colors.qualitative.Bold
vivid = px.colors.qualitative.Vivid
col_cat = {'Transport':vivid[10], 'Tabac':vivid[0], 'Beguda':vivid[7], 'Restaurant':vivid[9], 'Entrades':vivid[2],
           'Subscripcions':vivid[3], 'Supermercat':vivid[5], 'Compres':vivid[6], 'Altres':vivid[1]}
# dict_order = {'Tipus':['Income', 'Oci', 'Fixe', 'Estalvi'], 'Categoria':id_cat}
set1 = px.colors.qualitative.Set1
col_fixe = {'Lloguer': vivid[10], 'Serveis':vivid[1]}
col_serveis = {}
col_lloguer ={}

def format_ytick(df, spacing=500, mode='group', x='Mes'):
    min_y = 0
    if mode == 'group':
        max_y = math.ceil(df['Import'].max()/spacing)*spacing
    else:
        if x == 'Mes':
            max_y = math.ceil(df.groupby(by=['Mes']).sum()['Import'].max()/spacing)*spacing
        else:
            max_y = math.ceil(df.groupby(by=['Any']).sum()['Import'].max()/spacing)*spacing
    num_div = int(max_y/spacing)+1
    yticks = np.linspace(min_y, max_y, num_div)
    yticktext = [format_titol(y) for y in yticks]
    return yticks, yticktext

def generate_plot(df, x, level, spacing, year, tipus=''):
    df = df.copy()
    x = x.lower().capitalize()
    level = level.lower().capitalize()
    if level == 'Tipus':
        barmode = 'group'
        color_map = dict_color
        category_orders = {}
        # category_orders = dict_order
        mode = 'group'
    elif level == 'Categoria':
        barmode = 'relative'
        mode = 'relative'
        category_orders = {}
        if (df['Tipus'] == 'Fixe').all():
            color_map = col_fixe
        elif (df['Tipus'] == 'Oci').all():
            color_map = col_cat
        else:
            st.write(False)
            color_map = dict(zip(df['Concepte'].unique(), vivid[0:len(df['Concepte'].unique())]))
    else:
        barmode = 'relative'
        mode = 'relative'
        color_map = {}
        if tipus == 'Serveis':
            category_orders = {'Concepte':['WiFi', 'Electricitat', 'Aigua', 'Gas']}
        elif tipus == 'Lloguer':
            category_orders = {'Concepte':['EVO Banc', 'Reformes', 'Comunitat veïns', 'Ajuntament de Barcelona', 'Seguro hogar']}
        else:
            category_orders = {}
    df['Import_format'] = df['Import'].apply(lambda x: format_titol(x))
    if x in ['Mes', 'Any'] and level in ['Tipus', 'Categoria', 'Concepte']:
        if x == 'Any' and level == 'Concepte':
            x_axis = sorted(df.index)
        else:
            x_axis = x
        fig = px.bar(df, x=x_axis, y='Import', color=level, hover_data=level, barmode=barmode, color_discrete_map=color_map, category_orders=category_orders)
        for trace in fig.data:
            tipus = trace.name
            df_tipus = df[df[level] == tipus]
            trace.customdata = df_tipus[['Import_format']].to_numpy()
            trace.hovertemplate=f'{tipus}<br>%{{customdata[0]}}<extra></extra>'
        if level == 'Tipus':
            income = df.query('Tipus == "Income"')
            cost = df.query('Tipus != "Income"').groupby(by=[x]).sum().get('Import').reset_index()
            benefici = income.merge(cost, on=x, suffixes=('_income', '_gast'))
            benefici['Benefici'] = benefici['Import_income'] - benefici['Import_gast']
            # benefici = benefici.sort_values('Any')
            benefici['Benefici_acumulat'] = benefici['Benefici'].cumsum()
            if x == 'Mes':
                df['Mes'] = df['Mes'].astype(str)
                if year == year_actual:
                    month_range = range(1,month_actual+1)
                else:
                    month_range = range(1,13)
                income = income.query('Mes in @month_range')
                cost = cost.query('Mes in @month_range')
                benefici = benefici.query('Mes in @month_range')
            fig.add_trace(go.Scatter(x=income[x], y=income['Import'],
                                        name='Income mean', mode = 'lines', line={'shape':'spline', 'dash':'dot', 'color':'green'},
                                        showlegend=False, hoverinfo='none'))
            fig.add_trace(go.Scatter(x=cost[x], y=cost['Import'],
                                        name='Despeses mean', mode = 'lines', hoverinfo='none',
                                        hoveron = 'fills', line={'shape':'spline', 'dash':'dot', 'color':'red'}, showlegend=False))
            fig.add_trace(go.Scatter(x=benefici[x], y=benefici['Benefici_acumulat'],
                                        name='Benefici', mode='lines', line={'shape':'spline', 'dash':'dot', 'color':'gold'}, showlegend=True, hoverinfo=benefici['Benefici_acumulat']))
        yticks, yticktext = format_ytick(df, spacing, mode, x=x)
        fig.update_yaxes(tickmode='array', tickvals=yticks, ticktext=yticktext)
        if x == 'Any' and level == 'Concepte':
            fig.update_xaxes(title='', type='category')
        else:
            fig.update_xaxes(labelalias=dict_month, tickangle=-30, showticklabels=True, type='category', title='')
        fig.update_layout(legend = dict(title=None, orientation='h',yanchor='bottom', y=1, xanchor='left', x=0))
    else:
        print("Combinació de paràmetres no vàlida per a generar el gràfic.")
        return None

    return fig














