#!python3
import os
import uuid

import requests
import codecs
import time
from datetime import datetime
import copy
import boto3  # AWS SDK (boto3)
from tqdl import download
from tqdm import tqdm
import concurrent.futures
from boto3.s3.transfer import S3Transfer, TransferConfig
import threading
import sys
import pathlib
from botocore.config import Config
import tempfile

# Size of each part of multipart upload.
# This must be between 5MB and 25MB. Panopto server may fail if the size is more than 25MB.
PART_SIZE = 8 * 1024 * 1024


class UcsUploader:
    def __init__(self, server, ssl_verify, oauth2):
        '''
        Constructor of uploader instance.
        This goes through authorization step of the target server.
        '''
        self.server = server
        self.ssl_verify = ssl_verify
        self.oauth2 = oauth2

        # Use requests module's Session object in this example.
        # This is not mandatory, but this enables applying the same settings (especially
        # OAuth2 access token) to all calls and also makes the calls more efficient.
        # ref. https://2.python-requests.org/en/master/user/advanced/#session-objects
        self.requests_session = requests.Session()
        self.requests_session.verify = self.ssl_verify

        self.__setup_or_refresh_access_token()

    def __setup_or_refresh_access_token(self):
        '''
        This method invokes OAuth2 Authorization Code Grant authorization flow.
        It goes through browser UI for the first time.
        It refreshes the access token after that and no user interfaction is requetsed.
        This is called at the initialization of the class, as well as when 401 (Unaurhotized) is returend.
        '''
        access_token = self.oauth2.get_access_token_authorization_code_grant()
        self.requests_session.headers.update({'Authorization': 'Bearer ' + access_token})

    def __inspect_response_is_retry_needed(self, response):
        '''
        Inspect the response of a requets' call.
        True indicates the retry needed, False indicates success. Othrwise an exception is thrown.
        Reference: https://stackoverflow.com/a/24519419
        This method detects 403 (Forbidden), refresh the access token, and returns as 'is retry needed'.
        This example focuses on the usage of upload API and OAuth2, and any other error handling is not implemented.
        Prodcution code should handle other failure cases and errors as appropriate.
        '''
        if response.status_code // 100 == 2:
            # Success on 2xx response.
            return False

        if response.status_code == requests.codes.forbidden:
            print('Forbidden. This may mean token expired. Refresh access token.')
            self.__setup_or_refresh_access_token()
            return True

        # # Throw unhandled cases.
        # response.raise_for_status()

    def upload_folder(self, urls, xml, folder_id):
        '''
        Main upload method to go through all required steps.
        '''
        # step 1 - Create a session

        session_upload = self.__create_session(folder_id)
        if session_upload['FolderId'] is None or 'ID' not in session_upload:
            return None
        upload_id = session_upload['ID']
        upload_target = session_upload['UploadTarget']

        # step 2 - Enumerate files under the local folder
        # files = self.__enumerate_files(local_folder)

        # step 3 - upload the files
        # file_path = 'unique.xml'
        # with open(file_path, 'w', encoding='utf-8') as f:
        #     f.write(xml)
        file_path = uuid.uuid4().hex + '.xml'
        with open(file_path, 'w') as f:
            f.write(xml)
        self.__multipart_upload(upload_target, file_path)
        os.remove(file_path)
        for url in urls:
            if "http" in url:
                file_path = f'/cs/cloudstore/{url.replace("http://", "")}'
                folder = os.path.dirname(file_path)
                pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
                download(url, file_path)
            else:
                file_path = url
            self.__multipart_upload(upload_target, file_path)
        # step 4 - finish the upload
        self.__finish_upload(session_upload)
        self.__setup_or_refresh_access_token()
        return upload_id
        # step 5 - monitor the progress of processing
        # self.__monitor_progress(upload_id)

    def __create_session(self, folder_id):
        '''
        Create an upload session. Return sessionUpload object.
        '''
        print(folder_id)
        while True:
            print('Calling POST PublicAPI/REST/sessionUpload endpoint')
            url = 'https://{0}/Panopto/PublicAPI/REST/sessionUpload'.format(self.server)
            payload = {'FolderId': folder_id}
            headers = {'content-type': 'application/json'}
            resp = self.requests_session.post(url=url, json=payload, headers=headers)
            if not self.__inspect_response_is_retry_needed(resp):
                break

        session_upload = resp.json()
        print(session_upload)
        # print('  ID: {0}'.format(session_upload['ID']))
        # print('  target: {0}'.format(session_upload['UploadTarget']))
        return session_upload

    def __enumerate_files(self, folder):
        '''
        Return the list of files in the specified folder. Not to traverse sub folders.
        '''
        print('')
        files = []
        for entry in os.listdir(folder):
            path = os.path.join(folder, entry)
            if os.path.isdir(path):
                continue
            files.append(path)
            print('  {0}'.format(path))

        return files

    def get_session_id(self, upload_id):
        while True:
            url = 'https://{0}/Panopto/PublicAPI/REST/sessionUpload/{1}'.format(self.server, upload_id)
            resp = self.requests_session.get(url=url)
            if self.__inspect_response_is_retry_needed(resp):
                # If we get Unauthorized and token is refreshed, ignore the response at this time and wait for next time.
                continue
            session_upload = resp.json()
            return session_upload['SessionId']

    def __multipart_upload(self, upload_target, file_path):
        elements = upload_target.split('/')
        service_endpoint = '/'.join(elements[0:-2:])
        bucket = elements[-2]
        prefix = elements[-1]
        object_key = '{0}/{1}'.format(prefix, os.path.basename(file_path))

        print('')
        print('Upload {0} with multipart upload protocol'.format(file_path))
        print('  endpoint URL: {0}'.format(service_endpoint))
        print('  bucket name : {0}'.format(bucket))
        print('  object key  : {0}'.format(object_key))

        s3 = boto3.session.Session().client(
            service_name='s3',
            endpoint_url=service_endpoint,
            verify=self.ssl_verify,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy')

        if os.path.getsize(file_path) < 2*PART_SIZE:
            mpu = s3.create_multipart_upload(Bucket=bucket, Key=object_key)
            mpu_id = mpu['UploadId']

            # Iterate through parts
            parts = []

            uploaded_bytes = 0

            total_bytes = os.stat(file_path).st_size
            with open(file_path, 'rb') as f:
                i = 1
                while True:
                    data = f.read(PART_SIZE)
                    if not len(data):
                        break
                    part = s3.upload_part(Body=data, Bucket=bucket, Key=object_key, UploadId=mpu_id, PartNumber=i)
                    parts.append({'PartNumber': i, "ETag": part['ETag']})
                    uploaded_bytes += len(data)
                    print('  -- {0} of {1} bytes uploaded'.format(uploaded_bytes, total_bytes))
                    i += 1

            # Copmlete
            result = s3.complete_multipart_upload(Bucket=bucket, Key=object_key, UploadId=mpu_id,
                                                  MultipartUpload={"Parts": parts})
        else:
            config = TransferConfig(
                multipart_threshold=PART_SIZE,
                max_concurrency=100,
                num_download_attempts=10,
                use_threads=True
            )

            transfer = S3Transfer(s3, config)
            transfer.upload_file(file_path, bucket, object_key, callback=ProgressPercentage(file_path))


    def __finish_upload(self, session_upload):
        '''
        Finish upload.
        '''
        upload_id = session_upload['ID']
        upload_target = session_upload['UploadTarget']

        print('')
        while True:
            print('Calling PUT PublicAPI/REST/sessionUpload/{0} endpoint'.format(upload_id))
            url = 'https://{0}/Panopto/PublicAPI/REST/sessionUpload/{1}'.format(self.server, upload_id)
            payload = copy.copy(session_upload)
            payload['State'] = 1  # Upload Completed
            headers = {'content-type': 'application/json'}
            resp = self.requests_session.put(url=url, json=payload, headers=headers)
            if not self.__inspect_response_is_retry_needed(resp):
                break
        print('  done')

    def __monitor_progress(self, upload_id):
        '''
        Polling status API until process completes.
        '''
        print('')
        while True:
            time.sleep(100)
            print('Calling GET PublicAPI/REST/sessionUpload/{0} endpoint'.format(upload_id))
            url = 'https://{0}/Panopto/PublicAPI/REST/sessionUpload/{1}'.format(self.server, upload_id)
            resp = self.requests_session.get(url=url)
            if self.__inspect_response_is_retry_needed(resp):
                # If we get Unauthorized and token is refreshed, ignore the response at this time and wait for next time.
                continue
            session_upload = resp.json()
            print('  State: {0}'.format(session_upload['State']))

            if session_upload['State'] == 4:  # Complete
                break


# def __multipart_upload_single_file(self, upload_target, file_path):
#     '''
#     Upload a single file by using Multipart upload protocol.
#     We use AWS SDK (boto3) underneath for this step.
#     '''
#     # Upload target which is returned by sessionUpload API consists of:
#     # https://{service endpoint}/{bucket}/{prefix}
#     # where {bucket} and {prefix} are single element (without delimiter) individually.
#     elements = upload_target.split('/')
#     service_endpoint = '/'.join(elements[0:-2:])
#     bucket = elements[-2]
#     prefix = elements[-1]
#     object_key = '{0}/{1}'.format(prefix, os.path.basename(file_path))
#
#     print('')
#     print('Upload {0} with multipart upload protocol'.format(file_path))
#     print('  endpoint URL: {0}'.format(service_endpoint))
#     print('  bucket name : {0}'.format(bucket))
#     print('  object key  : {0}'.format(object_key))
#
#     # Create S3 client with custom endpoint on Panopto server.
#     # Panopto server does not refer access key or secret, but the library needs
#     # some values to start, otherwise no credentials error is thrown.
#     s3 = boto3.session.Session().client(
#         service_name='s3',
#         endpoint_url=service_endpoint,
#         verify=self.ssl_verify,
#         aws_access_key_id='dummy',
#         aws_secret_access_key='dummy')
#
#     # Initiate multipart upload.
#     mpu = s3.create_multipart_upload(Bucket=bucket, Key=object_key)
#     mpu_id = mpu['UploadId']
#
#     # Iterate through parts
#     parts = []
#     uploaded_bytes = 0
#     total_bytes = os.stat(file_path).st_size
#     with open(file_path, 'rb') as f:
#         i = 1
#         while True:
#             data = f.read(PART_SIZE)
#             if not len(data):
#                 break
#             part = s3.upload_part(Body=data, Bucket=bucket, Key=object_key, UploadId=mpu_id, PartNumber=i)
#             parts.append({'PartNumber': i, "ETag": part['ETag']})
#             uploaded_bytes += len(data)
#             print('  -- {0} of {1} bytes uploaded'.format(uploaded_bytes, total_bytes))
#             i += 1
#
#     # Copmlete
#     result = s3.complete_multipart_upload(Bucket=bucket, Key=object_key, UploadId=mpu_id,
#                                           MultipartUpload={"Parts": parts})
#     print('  -- complete called.')


class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()
