import argparse
import base64
import pickle
import urllib3
import config
from dateutil import parser
import json
from bs4 import BeautifulSoup
from panopto_folders import PanoptoFolders
from panopto_oauth2 import PanoptoOAuth2
from ucs_uploader import UcsUploader


def parse_argument():
    '''
    Argument definition and handling.
    '''
    parser = argparse.ArgumentParser(description='Upload videos to panopto')
    parser.add_argument('--client-id', dest='client_id', required=True, help='Client ID of OAuth2 client')
    parser.add_argument('--client-secret', dest='client_secret', required=True, help='Client Secret of OAuth2 client')
    args = parser.parse_args()
    if args.client_id is None or args.client_secret is None:
        print('Usage: upload.py --client-id <panopto_client-id> --client-secret <panopto_client-secret>')
        exit(1)
    config.PANOPTO_CLIEND_ID = args.client_id
    config.PANOPTO_SECRET = args.client_secret


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
    for (course_id, year, semester), courses in dct.items():
        panopto_id = search(folders, course_id, year, semester)
        if panopto_id is None:
            print(course_id, year, semester, "PROBLEMMMMMMMMM")
            continue
        for name, lessons in courses.items():
            lst_of_args = []
            for lesson in lessons:
                current_urls = (lesson['PrimaryVideo'], lesson['SecondaryVideo'])
                soup = BeautifulSoup(config.xml, 'xml')
                datetime_object = parser.parse(lesson['CreationDate'])
                date_iso = config.ISRAEL.localize(datetime_object).isoformat(timespec='milliseconds')
                new_title = lesson['Title'].replace('</div>', '').strip()
                new_title = config.REGEX.sub(' ', new_title)
                for title in soup.find_all('Title'):
                    title.string = new_title
                for description in soup.find_all('Description'):
                    new_description = lesson['Description'].replace('</div>', '').replace('\ufeff', '').strip()
                    new_description = config.REGEX.sub(' ', new_description)
                    description.string = new_description
                for date in soup.find_all('Date'):
                    date.string = date_iso
                for file, url in zip(soup.find_all('File'), current_urls):
                    file.string = url.split('/')[-1]
                xml = soup.prettify().replace()  # todo

                lst_of_args.append(
                    (course_id, semester, year, new_title, lesson['CreationDate'], current_urls, xml, panopto_id))
            lst.append(lst_of_args)
            print(lst)

    with open('mapping.pkl', 'wb') as f:
        pickle.dump(lst, f)
    with open('data.txt', 'w') as outfile:
        json.dump(lst, outfile, indent=4)


def main():
    '''
    Main method
    '''

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
        uploader = UcsUploader(config.PANOPTO_SERVER_NAME, False, oauth2)
        folders = PanoptoFolders(config.PANOPTO_SERVER_NAME, False, oauth2)
        # get_lists(folders)
        with open('mapping.pkl', 'rb') as f:
            lst = pickle.load(f)
        with open('uploader.log', 'w') as f:
            for lst_of_args in lst:
                for (course_id, semester, year, title, date, urls, xml, panopto_id) in lst_of_args:
                    f.write(f'Uploading course {course_id}, {semester}, {year}, {title} in {date} to id {panopto_id}\n')
                    f.flush()
                    uploader.upload_folder(urls, xml, panopto_id)
    except:
        print('Can"t authorize, check your credentials. Remember to save!')
        exit(1)
    # for folder in os.listdir(DIRECTORY):


if __name__ == '__main__':
    main()
