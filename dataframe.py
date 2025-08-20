import pandas as pd
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from datetime import date
from itertools import product

from auth import get_gspread_auth, load_data

id_tipus = ['Despesa', 'Estalvi', 'Ingressos']
id_tipus_gast = ['Fixe', 'Oci']

def write_to_sheet(sheet_name, df, spreadsheet_id, credentials):
        gc = get_gspread_auth(credentials)
        output_sh = gc.open_by_key(spreadsheet_id)
        try:
            ws = output_sh.worksheet(sheet_name)
        except:
            ws = output_sh.add_worksheet(title=sheet_name, rows=1000, cols=20)
        ws.clear()
        set_with_dataframe(ws, df)
        return

def process_dataframe(df):
    df_date = df.copy()
    id_tip = df['Tipus'].unique()
    id_cat = df.query('Tipus == "Oci"')['Categoria'].unique()
    id_fixe = df.query('Tipus == "Fixe"')['Categoria'].unique()
    dict_gast = {'Oci':id_cat, 'Fixe':id_fixe}
    year_actual = date.today().year
    df_date['Data'] = df['Any'].astype('string') + '-' + df['Mes'].astype('string') + '-' + df['Dia'].astype('string')
    df_date = df_date.filter(['Data', 'Tipus', 'Categoria', 'Import']).groupby(['Data', 'Tipus', 'Categoria'], as_index=False).sum()
    df_date['Data'] = pd.to_datetime(df_date['Data'], dayfirst=True, format='%Y-%m-%d')
    last_date = df_date.sort_values('Data')['Data'].iloc[-1]
    df['row_number'] = df.index
    last_row = df['row_number'].max()

    first_day = df_date['Data'].min()
    last_day = date(year_actual, 12, 31)
    time_series = pd.date_range(start=first_day, end=last_day)

    records = []
    for data, tipus in product(time_series, id_tip):
        if tipus in id_tipus_gast:
            for cat in dict_gast[tipus]:
                records.append((data, tipus, cat, 0))
        else:
            records.append((data, tipus, '', 0))
    df_zero = pd.DataFrame(records, columns=['Data', 'Tipus', 'Categoria', 'Import'])

    bf = df_zero.merge(df_date, on=['Data', 'Tipus', 'Categoria'], how='left')
    bf = bf.fillna(0).drop(columns='Import_x').rename(columns={'Import_y':'Import'})
    bf['Any'] = bf['Data'].dt.year
    bf['Mes'] = bf['Data'].dt.month

    bf = bf.groupby(['Any', 'Mes', 'Tipus', 'Categoria'], as_index=False, observed=True)['Import'].sum()
    af = bf.groupby(['Any', 'Tipus', 'Categoria'], as_index=False, observed=True)['Import'].sum()
    return bf, af

# @st.cache_data(show_spinner="Generant taula de dades...")
def generate_dataframe_with_gsheet(input_spreadsheet_id, output_spreadsheet_id, credentials, bf_sheet_name='bf', af_sheet_name='af'):
    # Agafar dades del Google Spreadsheet original i processar dades
    df = load_data(credentials, input_spreadsheet_id, sheet_name='DATA')
    bf, af = process_dataframe(df)
    # Obtenir última fila processada
    df['row_number'] = df.index
    last_row = df['row_number'].max()
    # Escriure DataFrame generats en Google Spreadsheet auxiliar
    write_to_sheet(bf_sheet_name, bf, output_spreadsheet_id, credentials)
    write_to_sheet(af_sheet_name, af, output_spreadsheet_id, credentials)
    write_to_sheet('last_row', pd.DataFrame([[last_row]]), output_spreadsheet_id, credentials)
    return bf, af

# @st.cache_data(show_spinner="Actualitzant taula de dades...")
def update_cached_dataframe_with_gsheet(input_spreadsheet_id, output_spreadsheet_id, credentials, bf_sheet_name='bf', af_sheet_name='af', last_row_sheet_name='last_row'):
    gc = get_gspread_auth(credentials)
    output_sh = gc.open_by_key(output_spreadsheet_id)

    df_new = load_data(credentials, input_spreadsheet_id, sheet_name='DATA')
    df_new['row_number'] = df_new.index

    try:
        bf_old = load_data(credentials, spreadsheet_id=output_spreadsheet_id, sheet_name='bf')
        af_old = load_data(credentials, spreadsheet_id=output_spreadsheet_id, sheet_name='af')
        df_last_row = get_as_dataframe(output_sh.worksheet('last_row')).dropna(how="all")
        last_row = int(df_last_row.iloc[0,0])
    except Exception as e:
        print(f"[INFO] Regenerant tot des de zero per error: {e}")
        return generate_dataframe_with_gsheet(input_spreadsheet_id, output_spreadsheet_id, credentials, bf_sheet_name=bf_sheet_name, af_sheet_name=af_sheet_name)

    if bf_old.empty or af_old.empty:
        return generate_dataframe_with_gsheet(input_spreadsheet_id, output_spreadsheet_id, credentials, bf_sheet_name=bf_sheet_name, af_sheet_name=af_sheet_name)

    df_new_unique = df_new[df_new['row_number'] > last_row]

    if df_new_unique.empty:
        print("[INFO] No hi ha files noves per afegir.")
        return bf_old, af_old

    bf_new, af_new = process_dataframe(df_new_unique)

    bf_concat = pd.concat([bf_old, bf_new], ignore_index=True).groupby(['Any', 'Mes', 'Tipus', 'Categoria'], as_index=False)['Import'].sum()
    af_concat = pd.concat([af_old, af_new], ignore_index=True).groupby(['Any', 'Tipus', 'Categoria'], as_index=False)['Import'].sum()
    
    write_to_sheet(bf_sheet_name, bf_concat, output_spreadsheet_id, credentials)
    write_to_sheet(af_sheet_name, af_concat, output_spreadsheet_id, credentials)

    # Actualitzar l'últim row_number processat
    new_last_row = df_new['row_number'].max()
    write_to_sheet(last_row_sheet_name, pd.DataFrame([[new_last_row]]), output_spreadsheet_id, credentials)

    return bf_concat, af_concat
