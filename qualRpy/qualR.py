import requests
import pkg_resources
import pandas as pd
import datetime as dt
from bs4 import BeautifulSoup
from itertools import product as iter_product
import os


def cetesb_aqs():
    '''
    Return a dataframe with the air quality stations (AQS) names and codes 
    required to use cetesb_data_download, all_pol, and all_met functions.

    It contains these fields:
        name : AQS name
        code : AQS code
        lat  : AQS latitude
        lon  : AQS longitude
    '''
    aqs_stream = pkg_resources.resource_stream(__name__, "data/cetesb_lat_lon.csv")
    return pd.read_csv(aqs_stream)


def cetesb_param():
    '''
    Return a dataframe with parameters and their codes required to use
    cetesb_data_download function.

    It contains these fields:
        name : Parameter name
        code : Parameter code
    '''
    param_stream = pkg_resources.resource_stream(__name__, "data/cetesb_param.csv")
    return pd.read_csv(param_stream)


def my_to_datetime(date_str):
    '''
    Transform dates
    with with 01 - 24 hours to 00 - 23 hours.
    It is based on this question on stackwoverflow:
        https://stackoverflow.com/questions/43359479/pandas-parsing-2400-instead-of-0000

    Parameters
    ----------
    date_str : str
        string with date.

    Returns
    -------
    Timestamp
        date as Timestamp.

    '''
    if date_str[11:13] != '24':
        return pd.to_datetime(date_str, format='%d/%m/%Y_%H:%M')

    date_str = date_str[0:11] + '00' + date_str[13:]
    return pd.to_datetime(date_str, format='%d/%m/%Y_%H:%M') + \
        dt.timedelta(days=1)


def cetesb_retrieve(cetesb_login: str, cetesb_password: str,
                    start_date: str, end_date: str,
                    parameter, station, csv: bool = False,
                    all_dates: bool = True, verbose: bool = False) -> pd.DataFrame:
    """
    Download a parameter for one Air Quality Station station
    from CETESB AQS network. Passing lists of integers to parameter and/or stations
    generate duplicated indexes.

    Parameters
    ----------
    cetesb_login : str
        cetesb qualar username.
    cetesb_password : str
        cetesb qualar username's password.
    start_date : str
        date to start download in %dd/%mm/%YYYY.
    end_date : str
        date to end download in %dd/%mm/%YYYY.
    parameter : int or list of int
        parameter code.
    station : int or list of int
        AQS code.
    csv : Bool, optional
        Export to csv file. The default is False.
    all_dates : Bool, optional
        Make a complete df with all dates. Setting as false can reduce the output size.
        The default is True.

    Returns
    -------
    dat_complete : pandas DataFrame
        DataFrame with a column with date and parameter values.
    """

    login_url = "https://qualar.cetesb.sp.gov.br/qualar/autenticador"
    request_url = 'https://qualar.cetesb.sp.gov.br/qualar/exportaDados.do?method=pesquisar'

    login_data = {
        'cetesb_login': cetesb_login,
        'cetesb_password': cetesb_password
    }

    search_data_list = []
    search_data_proto = {
        'irede': 'A',
        'dataInicialStr': start_date,
        'dataFinalStr': end_date,
        'iTipoDado': 'P'
    }

    if type(station) is not list:
        station = [station]
    if type(parameter) is not list:
        parameter = [parameter]

    for station_number, parameter_number in iter_product(station, parameter):
        search_data_station = search_data_proto.copy()
        search_data_station['estacaoVO.nestcaMonto'] = station_number
        search_data_station['parametroVO.nparmt'] = parameter_number
        search_data_list.append(search_data_station)

    soup_list = []
    with requests.Session() as s:

        if verbose:
            print('Loggin in...')

        _ = s.post(login_url, data=login_data)

        if verbose:
            print('Loggin success.')
            print('Requesting data...')

        for search_data in search_data_list:

            r = s.post(request_url, data=search_data)
            soup_list.append(BeautifulSoup(r.content, 'lxml'))

        if verbose:
            print('Request success.')

    if all_dates:
        day1 = pd.to_datetime(start_date, format='%d/%m/%Y')
        day2 = pd.to_datetime(end_date, format='%d/%m/%Y') + dt.timedelta(days=1)
        all_date = pd.DataFrame(index=pd.date_range(day1.strftime('%m/%d/%Y'),
                                                    day2.strftime('%m/%d/%Y'),
                                                    freq='H'))

    if verbose:
        print('Cleaning data...')

    # Scrapping cleaning
    dat_list = []
    for soup in soup_list:
        data = []
        table = soup.find('table', attrs={'id': 'tbl'})

        if type(table) is None:
            continue

        rows = table.find_all('tr')
        row_data = rows[2:]
        for row in row_data:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele])

        dat = pd.DataFrame(data)

        if len(dat) <= 1:
            continue

        dat = dat[[3, 4, 6, 7, 8, 9]]
        dat.columns = ['day', 'hour', 'name', 'pol_name', 'units', 'val']

        dat['date'] = dat.day + '_' + dat.hour

        # Changing date type to string to datestamp
        dat['date'] = dat.date.apply(my_to_datetime)

        # Changing val type from string/object to numeric
        dat['val'] = dat.val.str.replace(',', '.').astype(float)

        if all_dates:
            dat = all_date.join(dat.set_index('date')).dropna(how='all')

        dat_list.append(dat)

    if verbose:
        print('Cleaning complete.')

    if len(dat_list) == 0:
        if verbose:
            print('Warning: Empty dataset! Please check if the stations has the parameters available in the timeframe.')
        return pd.DataFrame(columns=['day', 'hour', 'name', 'pol_name', 'units', 'val', 'date'])

    dat_complete = pd.concat(dat_list, axis=0)

    if csv:
        file_name = str(parameter) + '_' + str(station) + '.csv'
        dat_complete.to_csv(file_name, index_label='date')

    if verbose:
        print('Retrieve complete.')

    return dat_complete


def cetesb_retrieve_robust(cetesb_login: str, cetesb_password: str,
                           start_date: str, end_date: str,
                           parameter, station,
                           save_path: str,
                           max_iter: int = 100, verbose=False):
    """
    Robust version of cetesb_retrieve for large datasets.
    Download parameter(s) for Air Quality station(s) from CETESB AQS network.
    This function returns a report of the successiful and failed imports.
    The dataset and reports are saved in a file each iteration.

    Parameters
    ----------
    cetesb_login : str
        cetesb qualar username.
    cetesb_password : str
        cetesb qualar username's password.
    start_date : str
        date to start download in %dd/%mm/%YYYY.
    end_date : str
        date to end download in %dd/%mm/%YYYY.
    parameter : int or list of int
        parameter code.
    station : int or list of int
        AQS code.
    save_path : str
        File path.
    max_iter : positive int
        Max number of requests in case of failure.
    verbose : bool

    Returns
    -------
    report : tuple[
    list[list[str | int | list[int]]], list[list[str | int | list[int]]]]
        A tuple with lists of station_parameter combinations of successifull and unsuccessiful downloads.
    """

    # Assert types
    if type(station) is not list:
        station = [station]
    if type(parameter) is not list:
        parameter = [parameter]

    # Make headers
    successes_path = os.path.splitext(save_path)[0] + '_successes.csv'
    failures_path = os.path.splitext(save_path)[0] + '_failures.csv'
    pd.DataFrame(columns=['station', 'parameter']).to_csv(successes_path)
    pd.DataFrame(columns=['station', 'parameter']).to_csv(failures_path)
    pd.DataFrame(columns=['day', 'hour', 'name',
                          'pol_name', 'units', 'val', 'date']).to_csv(save_path, index=False)

    # Make scrappers` inputs
    login_url = "https://qualar.cetesb.sp.gov.br/qualar/autenticador"
    request_url = 'https://qualar.cetesb.sp.gov.br/qualar/exportaDados.do?method=pesquisar'

    login_data = {
        'cetesb_login': cetesb_login,
        'cetesb_password': cetesb_password
    }
    search_data_list = []
    search_data_proto = {
        'irede': 'A',
        'dataInicialStr': start_date,
        'dataFinalStr': end_date,
        'iTipoDado': 'P'
    }
    for station_number, parameter_number in iter_product(station, parameter):
        search_data_station = search_data_proto.copy()
        search_data_station['estacaoVO.nestcaMonto'] = station_number
        search_data_station['parametroVO.nparmt'] = parameter_number
        search_data_list.append(search_data_station)

    def clean_scrap(scrap_data):
        data = []
        table = scrap_data.find('table', attrs={'id': 'tbl'})

        if table is None:
            return None

        rows = table.find_all('tr')
        row_data = rows[2:]
        for row in row_data:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele])
        dat = pd.DataFrame(data)

        if len(dat) <= 1:
            return None

        dat = dat[[3, 4, 6, 7, 8, 9]]
        dat.columns = ['day', 'hour', 'name', 'pol_name', 'units', 'val']
        dat['date'] = dat.day + '_' + dat.hour
        dat['date'] = dat.date.apply(my_to_datetime)
        dat['val'] = dat.val.str.replace(',', '.').astype(float)

        return dat

    def scrap_table(search):
        for _ in range(1, max_iter):
            if verbose:
                print('Trying scrap request')
            request = s.post(request_url, data=search)
            if verbose:
                print('Scrap request success')
            if request is None:
                if verbose:
                    print('request returned None')
                continue
            cleaned_scrap = clean_scrap(BeautifulSoup(request.content, 'lxml'))
            if cleaned_scrap is not None:
                break
            if verbose:
                print('Empty scrap')

        return cleaned_scrap

    def report(failure: bool = False):
        report_path = successes_path
        if failure:
            report_path = failures_path
        if verbose:
            print(search_data['estacaoVO.nestcaMonto'], search_data['parametroVO.nparmt'])
        pd.DataFrame({'station': search_data['estacaoVO.nestcaMonto'],
                      'parameter': search_data['parametroVO.nparmt']},
                     index=[0]).to_csv(report_path, mode='a', header=False)

    successes = []
    failures = []
    with requests.Session() as s:
        if verbose:
            print('Trying login')
        # Login
        _ = s.post(login_url, data=login_data)
        if verbose:
            print('Login successful')
        # Request
        for search_data in search_data_list:
            scrap = scrap_table(search_data)
            if scrap is None:
                if verbose:
                    print('Scrap fail')
                failures.append([search_data['estacaoVO.nestcaMonto'], search_data['parametroVO.nparmt']])
                report(failure=True)
                continue
            if verbose:
                print('Scrap success')
            scrap.to_csv(save_path, mode='a', header=False)
            successes.append([search_data['estacaoVO.nestcaMonto'], search_data['parametroVO.nparmt']])
            report()

    return successes, failures


def cetesb_retrieve_pol(cetesb_login, cetesb_password,
                        start_date, end_date, station,
                        csv=False, voc=False):
    '''
    Download photochemical pollutants 

    Parameters
    ----------
    cetesb_login : str
        cetesb qualar username.
    cetesb_password : str
        cetesb qualar username's password.
    start_date : str
        date to start download in %dd/%mm/%YYYY.
    end_date : str
        date to end download in %dd/%mm/%YYYY.
    station : int
        AQS code.
    csv_photo : Bool, optional
        Export to csv file. The default is False.

    Returns
    -------
    all_photo_df : pandas DataFrame
        Data Frame with date index (America/Sao_Paulo),
        O3, NO, NO2, CO, PM10, PM2.5 columns.

    '''
    o3 = cetesb_retrieve(cetesb_login, cetesb_password,
                         start_date, end_date, 63, station)
    no = cetesb_retrieve(cetesb_login, cetesb_password,
                         start_date, end_date, 17, station)
    no2 = cetesb_retrieve(cetesb_login, cetesb_password,
                          start_date, end_date, 15, station)
    nox = cetesb_retrieve(cetesb_login, cetesb_password,
                          start_date, end_date, 18, station)
    co = cetesb_retrieve(cetesb_login, cetesb_password,
                         start_date, end_date, 16, station)
    so2 = cetesb_retrieve(cetesb_login, cetesb_password,
                          start_date, end_date, 13, station)
    pm10 = cetesb_retrieve(cetesb_login, cetesb_password,
                           start_date, end_date, 12, station)
    pm25 = cetesb_retrieve(cetesb_login, cetesb_password,
                           start_date, end_date, 57, station)

    all_photo_df = pd.DataFrame({
        'o3': o3.val,
        'no': no.val,
        'no2': no2.val,
        'nox': nox.val,
        'co': co.val,
        'so2': so2.val,
        'pm10': pm10.val,
        'pm25': pm25.val
    }, index=o3.index)

    if voc:
        tol = cetesb_retrieve(cetesb_login, cetesb_password,
                              start_date, end_date, 62, station)
        ben = cetesb_retrieve(cetesb_login, cetesb_password,
                              start_date, end_date, 61, station)
        all_photo_df["tol"] = tol.val
        all_photo_df["ben"] = ben.val

    all_photo_df.index = all_photo_df.index.tz_localize('America/Sao_Paulo')

    if csv:
        all_photo_df.to_csv('all_pol_' + str(station) + '.csv',
                            index_label='date')
    else:
        return all_photo_df


def cetesb_retrieve_met(cetesb_login, cetesb_password,
                        start_date, end_date, station,
                        in_k=False, rm_flag=True,
                        csv=False):
    '''
    Download meteorological parameters

    Parameters
    ----------
    cetesb_login : str
        cetesb qualar username.
    cetesb_password : str
        cetesb qualar username's password.
    start_date : str
        date to start download in %dd/%mm/%YYYY.
    end_date : str
        date to end download in %dd/%mm/%YYYY.
    station : int
        AQS code.
    in_k : Bool, optional
        Temperature in Kelvin. The default is False.
    rm_flag : Bool, optional
        Filter wind calm and no values wind direction. The default is True.
    csv_met : Bool, optional
        Export to csv file. The default is False.

    Returns
    -------
    all_met_df : pandas DataFrame
        Data Frame with date index  (America/Sao_Paulo), 
        TC, RH, WS and WD columns.

    '''
    tc = cetesb_retrieve(cetesb_login, cetesb_password,
                         start_date, end_date, 25, station)
    rh = cetesb_retrieve(cetesb_login, cetesb_password,
                         start_date, end_date, 28, station)
    ws = cetesb_retrieve(cetesb_login, cetesb_password,
                         start_date, end_date, 24, station)
    wd = cetesb_retrieve(cetesb_login, cetesb_password,
                         start_date, end_date, 23, station)
    if in_k:
        K = 273.15
    else:
        K = 0

    all_met_df = pd.DataFrame({
        't2': tc.val + K,
        'rh2': rh.val,
        'ws': ws.val,
        'wd': wd.val
    }, index=tc.index)

    all_met_df.index = all_met_df.index.tz_localize('America/Sao_Paulo')

    # Filtering 777 and 888 values
    if rm_flag:
        filter_flags = all_met_df['wd'] <= 360
        all_met_df['wd'].where(filter_flags, inplace=True)

    # Export to csv
    if csv:
        all_met_df.to_csv('all_met_' + str(station) + '.csv',
                          index_label='date')
    else:
        return all_met_df
