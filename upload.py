import argparse
import urllib3
import config
import pandas as pd
import httplib2
from panopto_folders import PanoptoFolders
from panopto_sessions import PanoptoSessions
from panopto_oauth2 import PanoptoOAuth2
from ucs_uploader import UcsUploader
import re
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
import os
from datetime import datetime
import time
from gspread.models import Cell
import schedule

h = httplib2.Http()


def parse_argument():
    '''
    Argument definition and handling.
    '''
    parser = argparse.ArgumentParser(description='Upload videos to panopto')
    parser.add_argument('--client-id', dest='client_id', required=True, help='Client ID of OAuth2 client')
    parser.add_argument('--client-secret', dest='client_secret', required=True, help='Client Secret of OAuth2 client')
    parser.add_argument('--is-manual', dest='is_manual', required=True)
    parser.add_argument('--is-main', dest='is_main', required=True)
    parser.add_argument('--is-fast', dest='is_fast')
    args = parser.parse_args()
    config.PANOPTO_CLIEND_ID = args.client_id
    config.PANOPTO_SECRET = args.client_secret
    return True if args.is_manual == 'TRUE' else False, True if args.is_main == 'TRUE' else False, \
           True if args.is_fast == 'TRUE' else False


def search(folders, course_id, year, semester):
    results = folders.search_folders(rf'{course_id}')
    id = None
    for result in results:
        m = re.search(rf'{config.YEARS[year]} -> {course_id}', result['Name'])
        if m is None:
            continue
        if result['ParentFolder']['Name'] == f'{config.YEARS[year]} -> {semester}' or \
                result['ParentFolder']['Name'] == f'{config.YEARS[year]} -> Semester 1 or 2' or \
                result['ParentFolder']['Name'] == f'{config.YEARS[year]} -> Semesters 1 or 2' or \
                result['ParentFolder']['Name'] == f'{config.YEARS[year]} -> Semesters 1 and 2' or \
                result['ParentFolder']['Name'] == f'{config.YEARS[year]} -> Summer':
            return result['Id']
    return id


def is_valid_url(url):
    try:
        ret = requests.head(url)
        if ret.status_code < 400:
            return True
        return False
    except (TimeoutError, requests.exceptions.ConnectionError):
        return False


# parse_argument()
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
# uploader = UcsUploader(config.PANOPTO_SERVER_NAME, False, oauth2)
# folders = PanoptoFolders(config.PANOPTO_SERVER_NAME, False, oauth2)
#
#
# def update_folder_structure(children):
#     if not children:
#         return
#     for child in children:
#         if '2017-18 ->' not in child['Name']:
#             if not folders.update_folder_name(child['Id'], f'2017-18 -> {child["Name"]}'):
#                 folders.setup_or_refresh_access_token()
#                 folders.update_folder_name(child['Id'], f'2017-18 -> {child["Name"]}')
#             print(child['Name'])
#         update_folder_structure(folders.get_children(child['Id']))
#
#
# update_folder_structure(folders.get_children('98ead464-9a2a-48ce-bef7-ac5300a34b5a'))
# exit()

def safe_update(sheet: gspread.Spreadsheet.sheet1, row, col, value):
    while True:
        try:
            sheet.update_cell(row, col, value)
            break
        except gspread.exceptions.APIError:
            time.sleep(100)


def safe_get_df(sheet: gspread.Spreadsheet.sheet1):
    while True:
        try:
            return pd.DataFrame(sheet.get_all_records())
        except gspread.exceptions.APIError:
            time.sleep(100)


def safe_read(sheet: gspread.Spreadsheet.sheet1, row, col):
    while True:
        try:
            return sheet.cell(row, col).value
        except:
            time.sleep(100)


def get_urls(cam_url, screen_url):
    fpath_cam = f'/cs/cloudstore/{cam_url.replace("http://", "")}'
    r = requests.get(cam_url, stream=True)
    if os.path.exists(fpath_cam) and os.stat(fpath_cam).st_size == int(r.headers.get('content-length', 0)):
        cam_url = fpath_cam
    if screen_url and type(screen_url) != float:
        fpath_screen = f'/cs/cloudstore/{screen_url.replace("http://", "")}'
        r = requests.get(screen_url, stream=True)
        if os.path.exists(fpath_screen) and os.stat(fpath_screen).st_size == int(r.headers.get('content-length', 0)):
            screen_url = fpath_screen
    return [cam_url, screen_url] if screen_url else [cam_url]


def upload(is_manual: bool, is_main: bool, is_fast: bool):
    global full_data
    '''
    Main method
    '''

    if is_manual:
        manuals = data[data['IS_TICKED'].values == 'TRUE']
        manuals = manuals[manuals['TIME_UPLOADED'].notnull()]
        manuals = full_data[full_data['COURSE_NAME'].isin(manuals['COURSE_NAME'].values)]
        manuals = manuals[manuals['IS_TICKED'].values == 'FALSE']
        full_data = manuals
    if is_fast:
        full_data = full_data[full_data['CAM_URL'].str.contains("132")]
    full_data = full_data[full_data['FOLDER_URL'] != ""]
    for i, ser in full_data.iterrows():
        print(ser['COURSE_NAME'])
        print(ser['TITLE'])
        print(ser['FOLDER_URL'])
        index_ = np.nonzero(course_names == ser['COURSE_NAME'])[0][0]
        if not ser['FOLDER_URL'] or \
                safe_read(sheet_full_data, i + 2, 1) == 'TRUE':  # finish session
            continue
        folder_id = re.search(r'folderID=%22(.*)%22', ser['FOLDER_URL']).group(1)
        urls = get_urls(ser['CAM_URL'], ser['SCREEN_URL'])
        if safe_read(sheet_full_data, i + 2, 15) == 'TRUE' and not is_main:
            # stuck in the middle, only main pc should download
            print(is_main)
            continue
        safe_update(sheet_full_data, i + 2, 15, 'TRUE')
        session_id = uploader.upload_folder(urls, ser['XML'], folder_id)
        # session_url = f'https://huji.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id={session_id}'
        # print(session_url)
        safe_update(sheet_full_data, i + 2, 1, 'TRUE')
        safe_update(sheet_full_data, i + 2, 14, session_id)
        safe_update(sheet, index_ + 2, 1, 'TRUE')
        safe_update(sheet, index_ + 2, 7, datetime.now().isoformat())
        current_data = safe_get_df(sheet_full_data)
        filter_data = current_data[(current_data['COURSE_NAME'] == ser['COURSE_NAME']) &
                                   (current_data['IS_TICKED'] == 'FALSE')]
        if filter_data.empty:
            safe_update(sheet, index_ + 2, 8, datetime.now().isoformat())


def main(is_manual, is_main=True, is_fast=False):
    global data, uploader, course_names, sheet_full_data, sheet, full_data
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_JSON, scope)
    client = gspread.authorize(creds)
    sheet = client.open("StreamitUP to Panopto DB").sheet1
    sheet_full_data = client.open('Full StreamitUP Data').sheet1
    data = safe_get_df(sheet)
    full_data = safe_get_df(sheet_full_data)
    # xml_strs = full_data['XML'].values
    course_names = data['COURSE_NAME'].values
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
    uploader = UcsUploader(config.PANOPTO_SERVER_NAME, False, oauth2)

    upload(is_manual, is_main, is_fast)


if __name__ == '__main__':
    is_manual, is_main, is_fast = parse_argument()
    if is_manual:
        main(is_manual, is_main, is_fast)
        schedule.every(2).minutes.do(main, is_manual, is_main, is_fast)
    else:
        main(is_manual, is_main, is_fast)
    while True:
        schedule.run_pending()

# scope = ['https://spreadsheets.google.com/feeds',
#          'https://www.googleapis.com/auth/drive']
# creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_JSON, scope)
# client = gspread.authorize(creds)
# sheet = client.open("StreamitUP to Panopto DB").sheet1
# sheet_full_data = client.open('Full StreamitUP Data').sheet1
# data = pd.DataFrame(sheet.get_all_records())
# full_data = pd.DataFrame(sheet_full_data.get_all_records())
# cam_links = full_data['CAM_URL'].values
# course_names = data['COURSE_NAME'].values
# folder_urls = data['FOLDER_URL'].values
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
#
# log = pd.read_csv('log_file_new.csv')
# small_cells = []
# big_cells = []
# for i, ser in log.iterrows():
#     index_full = np.nonzero(cam_links == ser['CAM_URL'])[0][0]
#     index_ = np.nonzero(folder_urls == ser['FOLDER_URL'])[0][0]
#     big_cells.append(Cell(row=index_full+2,col=1, value='TRUE'))
#     big_cells.append(Cell(row=index_full+2,col=13, value=ser['SESSION_URL']))
#     # sheet_full_data.update_cell(index_full + 2, 1, 'TRUE')
#     # sheet_full_data.update_cell(index_full + 2, 13, ser['SESSION_URL'])
#     small_cells.append(Cell(row=index_+2, col=1, value='TRUE'))
#     small_cells.append(Cell(row=index_+2, col=7, value=datetime.now().isoformat()))
#     # sheet.update_cell(index_ + 2, 1, 'TRUE')
#     # sheet.update_cell(index_ + 2, 7, datetime.now().isoformat())
#
# while True:
#     try:
#         sheet.update_cells(small_cells)
#         sheet_full_data.update_cells(big_cells)
#         print('woohoo')
#         break
#     except gspread.exceptions.APIError as e:
#         print(e)
#         print('sleeping')
#         time.sleep(100)


# parse_argument()
# scope = ['https://spreadsheets.google.com/feeds',
#          'https://www.googleapis.com/auth/drive']
# creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_JSON, scope)
# client = gspread.authorize(creds)
# sheet = client.open("StreamitUP to Panopto DB").sheet1
# sheet_full_data = client.open('Full StreamitUP Data').sheet1
# data = pd.DataFrame(sheet.get_all_records())
# full_data = pd.DataFrame(sheet_full_data.get_all_records())
# cam_links = full_data['CAM_URL'].values
# course_names = data['COURSE_NAME'].values
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
# uploader = UcsUploader(config.PANOPTO_SERVER_NAME, False, oauth2)
#
# cells = []
# for row in sheet_full_data:
#
#     # filter_data = full_data[(full_data['IS_TICKED'] == 'FALSE')]
#     # if filter_data.empty:
#     #     index_ = np.nonzero(course_names == ser['COURSE_NAME'])[0][0]
#     #     cells.append(Cell(row=index_ + 2, col=8, value=datetime.now().isoformat()))
# while True:
#     try:
#         sheet.update_cells(cells)
#         break
#     except gspread.exceptions.APIError as e:
#         print(e)
#         time.sleep(100)
#
#
# exit(-1)
