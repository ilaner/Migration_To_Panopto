import argparse
import base64
import pickle
import urllib3
import config
from dateutil import parser
import json
from bs4 import BeautifulSoup
import pandas as pd
import io
import xml.etree.ElementTree as ET
import httplib2
from panopto_folders import PanoptoFolders
from panopto_sessions import PanoptoSessions
from panopto_oauth2 import PanoptoOAuth2
from ucs_uploader import UcsUploader
import re
import requests

h = httplib2.Http()


def parse_argument():
    '''
    Argument definition and handling.
    '''
    parser = argparse.ArgumentParser(description='Upload videos to panopto')
    parser.add_argument('--client-id', dest='client_id', required=True, help='Client ID of OAuth2 client')
    parser.add_argument('--client-secret', dest='client_secret', required=True, help='Client Secret of OAuth2 client')
    parser.add_argument('--course-id', dest='course_id', required=False)
    parser.add_argument('--semester', dest='semester', required=False)
    parser.add_argument('--year', dest='year', required=False, help='Starting year of the course')
    parser.add_argument('--folder-id', dest='folder_id', required=False, help='Panopto folder id of the destination')
    args = parser.parse_args()
    config.PANOPTO_CLIEND_ID = args.client_id
    config.PANOPTO_SECRET = args.client_secret
    config.COURSE_ID = str(args.course_id)
    config.SEMESTER = args.semester
    if config.YEAR:
        config.YEAR = int(args.year)
    config.FOLDER_ID = args.folder_id


def load_full_courses():
    with open("better_urls_fix.pkl", 'rb') as input:
        decoded = bytes(input.read())
    decoded = base64.b64decode(decoded)
    return pickle.loads(decoded)


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




def main():
    '''
    Main method
    '''
    parse_argument()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
    uploader = UcsUploader(config.PANOPTO_SERVER_NAME, False, oauth2)
    folders = PanoptoFolders(config.PANOPTO_SERVER_NAME, False, oauth2)
    # course_id_to_panopto_id(folders)


if __name__ == '__main__':
    main()
