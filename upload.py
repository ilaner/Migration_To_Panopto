import argparse
import base64
import pickle
import urllib3
import config
from dateutil import parser
import json
from bs4 import BeautifulSoup
import io
import xml.etree.ElementTree as ET
import httplib2
from panopto_folders import PanoptoFolders
from panopto_oauth2 import PanoptoOAuth2
from ucs_uploader import UcsUploader

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
    config.YEAR = int(args.year)
    config.FOLDER_ID = args.folder_id


def load_full_courses():
    with open("urls.pkl", 'rb') as input:
        decoded = bytes(input.read())
    decoded = base64.b64decode(decoded)
    return pickle.loads(decoded)


def search(folders, course_id, year, semester):
    results = folders.search_folders(rf'{course_id}')
    id = None
    for result in results:
        if config.YEARS[year] in result['Name']:
            if result['ParentFolder']['Name'] == f'{config.YEARS[year]} -> {semester}' or \
                    result['ParentFolder']['Name'] == f'{config.YEARS[year]} => Semester 1 or 2' or \
                    result['ParentFolder']['Name'] == f'{config.YEARS[year]} => Semesters 1 or 2':
                return result['Id']
    return id


def course_id_to_panopto_id(folders):
    lst = []
    dct = load_full_courses()
    lst_of_dcts = []
    if config.COURSE_ID and config.SEMESTER and config.YEAR:
        if not config.FOLDER_ID:
            config.FOLDER_ID = search(folders, config.COURSE_ID, config.SEMESTER, config.COURSE_ID)
        lst_of_dcts = [((config.COURSE_ID, config.YEAR, config.SEMESTER),
                        dct[(config.COURSE_ID, config.YEAR, config.SEMESTER)], config.FOLDER_ID)]
        print(lst_of_dcts)

    else:
        for (course_id, year, semester), courses in dct.items():
            if year == 2018:
                panopto_id = search(folders, course_id, year, semester)
                if panopto_id is None:
                    print(course_id, year, semester, "PROBLEMMMMMMMMM")
                    continue
                lst_of_dcts.append(((course_id, year, semester), courses, panopto_id))
    for (course_id, year, semester), course, panopto_id in lst_of_dcts:
        for name, lessons in course.items():
            lst_of_args = []
            for lesson in lessons:
                current_urls = (lesson['PrimaryVideo'], lesson['SecondaryVideo'])
                resp = h.request(current_urls[1], 'HEAD')
                if not int(resp[0]['status']) < 400:
                    tree = ET.parse(io.StringIO(config.SIMPLE))
                    current_urls = [lesson['PrimaryVideo']]
                else:
                    tree = ET.parse(io.StringIO(config.UCS))
                root = tree.getroot()
                date_str = lesson['CreationDate']
                datetime_object = parser.parse(date_str)
                date_local = config.ISRAEL.localize(datetime_object)
                date_iso = date_local.isoformat(timespec='milliseconds')

                for title in root.iter('Title'):
                    title.text = lesson['Title']
                for description in root.iter('Description'):
                    description.text = lesson['Description']
                for date in root.iter('Date'):
                    date.text = date_iso
                for file, url in zip(root.iter('File'), current_urls):
                    file.text = url.split('/')[-1]

                xml_str = ET.tostring(root, encoding='unicode', method='xml')
                xml_str = xml_str.replace('<Session>', '<?xml version="1.0" encoding="utf-8"?> \n'
                                                       '<Session xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://tempuri.org/UniversalCaptureSpecification/v1">')

                lst_of_args.append(
                    (course_id, semester, year, lesson['Description'], date_str, current_urls, xml_str, panopto_id))

            lst.append(lst_of_args)
            # print(lst)

    with open('mapping.pkl', 'wb') as f:
        pickle.dump(lst, f)
    with open('data.txt', 'w') as outfile:
        json.dump(lst, outfile, ensure_ascii=False, indent=4)


def main():
    '''
    Main method
    '''
    parse_argument()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
    uploader = UcsUploader(config.PANOPTO_SERVER_NAME, False, oauth2)
    folders = PanoptoFolders(config.PANOPTO_SERVER_NAME, False, oauth2)
    course_id_to_panopto_id(folders)
    with open('mapping.pkl', 'rb') as f:
        lst = pickle.load(f)
    with open('uploader.log', 'w') as f:
        for lst_of_args in lst:
            for (course_id, semester, year, title, date, urls, xml, panopto_id) in lst_of_args:
                f.write(f'Uploading course {course_id}, {semester}, {year}, {title} in {date} to id {panopto_id}\n')
                f.flush()
                uploader.upload_folder(urls, xml, panopto_id)
    # for folder in os.listdir(DIRECTORY):


if __name__ == '__main__':
    main()
