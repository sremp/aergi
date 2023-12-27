#!/usr/bin/env python3
""" JIRA Rest API client """

from getpass import getpass
import io
import json
import os
from pprint import pprint
import requests

JIRA_URLS = {
    'prod': 'https://jira.myfuncompany.com',
}

HEADERS = {'content-type': 'application/json'}

TIMEOUT = 60

TEMPO_ACT_TO_INT_MAP = {
  'Design': 'Requirements',
  'Development': 'Design',
  'Testing - Pre Deployment': 'Development',
  'Non-Project meeting': 'Non-Projectmeeting'
}

TEMPO_INT_TO_ACT_MAP = {v: k for k, v in TEMPO_ACT_TO_INT_MAP.items()}



class JiraClient():
    """ JIRA Rest API client class """

    def __init__(self, user=None, passwd=None, url=None,
                 fields=False, test=False, debug=False):
        # pylint: disable=too-many-arguments
        self.debug = debug
        if url is not None:
            self.url = url
        elif 'JIRA_ADDR' in os.environ:
            self.url = os.environ['JIRA_ADDR']
        elif test:
            self.url = JIRA_URLS['test']
        else:
            self.url = JIRA_URLS['prod']
        if url is not None:
            self.url = url
        if 'JIRA_TOKEN' in os.environ:
            self.user_creds = None
            token = os.environ['JIRA_TOKEN']
            HEADERS['Authorization'] = f'Bearer {token}'
        else:
            if user is None:
                user = os.environ['LOGNAME']
            if passwd is None:
                print(f'Using {user} for Jira username. Suggestion: set JIRA_TOKEN')
                passwd = getpass()
            self.user_creds = (user, passwd)
        self.timeout = TIMEOUT
        self.cust_flds = self.get_fields()[0] if fields else []
        if fields and debug:
            pprint(self.cust_flds)

    def get_field(self, name):
        """ Get custom field ID """
        return self.cust_flds[name]

    def link_issues(self, link_type, parent_issue, child_issue):
        """ Used to create a link between two issues """
        payload = {
            'type': {
                'name': link_type
            },
            'inwardIssue': {
                'key': child_issue
            },
            'outwardIssue': {
                'key': parent_issue
            }
        }
        url = self.url + '/rest/api/2/issueLink'
        self._execute('POST', url, payload=payload)

    def create_issue(self, summary, project, issue_type, fields=None):
        """ Create Jira Issue """
        payload = {
            'fields': {
                'project': {
                    'key': project,
                },
                'summary': summary,
                'issuetype': {
                    'name': issue_type,
                }
            }
        }
        if fields:
            payload['fields'].update(fields)
        url = self.url + '/rest/api/2/issue'
        return self._execute('POST', url, payload=payload)

    def get_fields(self):
        """ Get custom/system fields """
        url = self.url + '/rest/api/2/field'
        response = requests.get(url, auth=self.user_creds, headers=HEADERS, timeout=self.timeout)
        self.check_http_response(response)
        fields = response.json()

        system_fields = {}
        custom_fields = {}

        for field in fields:
            if field['custom']:
                custom_fields[field['name']] = field['id']
            else:
                name = field['name'].encode('ascii', 'ignore').decode('ascii')
                system_fields[name] = field['id']

        return custom_fields, system_fields

    def search(self, jql, max_results=100):
        """ JQL to return an issue or list of issues """
        start = 0
        values = []
        url = f'{self.url}/rest/api/2/search?jql={jql}'
        while True:
            paged_url = f'{url}&startAt={start}&maxResults={max_results}'
            response = requests.get(
                paged_url,
                headers=HEADERS,
                auth=self.user_creds,
                timeout=self.timeout)
            self.check_http_response(response)
            data = response.content.decode('ascii', 'ignore')
            found_issues = json.loads(data)
            if len(found_issues['issues']) == 0:
                break
            start += max_results
            values.extend(found_issues['issues'])
        return values

    def get_issue(self, issue):
        """ Get issue detail  """
        url = f'{self.url}/rest/api/2/issue/{issue}?fields&expand=transitions'
        response = requests.get(url, auth=self.user_creds, headers=HEADERS, timeout=self.timeout)
        self.check_http_response(response)
        return response.json()

    def update_issue(self, issue, field, value, payload=None):
        """ Update an issue field """

        url = self.url + '/rest/api/2/issue/' + issue
        if not payload:
            payload = {'fields': {field: value}}
        data = json.dumps(payload)

        response = requests.put(
            url,
            data,
            headers=HEADERS,
            auth=self.user_creds,
            timeout=self.timeout)

        self.check_http_response(response)

    def get_user(self, username):
        """ Get Jira user info """
        #return self.api_call('GET', f'user?username={username}')
        url = f'{self.url}/rest/api/2/user?username={username}'
        response = requests.get(url, headers=HEADERS, timeout=self.timeout)
        self.check_http_response(response)
        return response.json()

    def assign_issue(self, issue, username):
        """ Update an issue field """
        url = self.url + '/rest/api/2/issue/' + issue + '/assignee'
        payload = {'name': username}
        data = json.dumps(payload)

        response = requests.put(
            url,
            data,
            headers=HEADERS,
            auth=self.user_creds,
            timeout=self.timeout)
        self.check_http_response(response)

    def _execute(self, type_, url, payload=None, stream=False):
        """ Carry out get/put/post/delete with data """
        if payload is not None:
            data = json.dumps(payload)
        if type_ == 'GET':
            if payload is not None:
                response = requests.get(url, data, headers=HEADERS, auth=self.user_creds,
                                        timeout=self.timeout, stream=stream)
            else:
                response = requests.get(url, headers=HEADERS, auth=self.user_creds,
                                        timeout=self.timeout)
        elif type_ == 'PUT':
            response = requests.put(
                url,
                data,
                headers=HEADERS,
                auth=self.user_creds,
                timeout=self.timeout
            )
        elif type_ == 'POST':
            response = requests.post(
                url,
                data,
                headers=HEADERS,
                auth=self.user_creds,
                timeout=self.timeout
            )
        elif type_ == 'DELETE':
            response = requests.delete(url, headers=HEADERS, auth=self.user_creds,
                                       timeout=self.timeout)
        else:
            raise RuntimeError('Invalid request type: ' + type_)

        if self.debug:
            print('PAYLOAD')
            print(payload)
            print('Response.text')
            print(response.text)

        try:
            response.raise_for_status()
        except: # pylint: disable=bare-except
            print(response.text)
            raise

        if stream:
            results = response.content
        elif response.status_code >= 200 and response.status_code <= 203:
            results = response.json()
        else:
            results = None
        return results

    @classmethod
    def check_http_response(cls, response):
        """ Will check the response code of the http rest call """
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            status_code = response.status_code
            error = json.dumps(response.text)
            if status_code != 200:
                print(response.text)
                error = json.loads(response.text)
                raise RuntimeError(f'HTTP error {status_code}: {error}') from err

    def api_call(self, type_, params=None, api='api', version='3', endpoint=False, url=None,
                payload=None, stream=False):
        """ Generic api call """
        # pylint: disable=too-many-arguments
        if endpoint:
            url = f'{self.url}/rest/{params}'
        else:
            if url is None:
                url = f'{self.url}/rest/{api}/{version}/{params}'
        return self._execute(type_, url, payload, stream=stream)

    def tempo_api_call(self, path, payload):
        """ Call Tempo API """
        url = f'{self.url}/rest/tempo-timesheets/4/{path}'
        return self.api_call('POST', url=url, payload=payload)

    def attach_file(self, issue, file_name=None, content=None, name='file'):
        """ Attach file to issue """
        url = f'{self.url}/rest/api/2/issue/{issue}/attachments'
        headers = {"X-Atlassian-Token": "nocheck"}

        if file_name:
            file_ = None
            with open(file_name, 'rb') as read:
                file_ = read.read()
            files = {'file': (name, file_)}
        elif content:
            if not name:
                raise RuntimeError('You must provide a name for string to be attached')
            files = {'file': (name, io.BytesIO(str.encode(content)))}

        response = requests.post(
            url,
            auth=self.user_creds,
            files=files,
            headers=headers,
            timeout=self.timeout
        )

        self.check_http_response(response)

    def add_issue_comment(self, issue, comment, role='Users'):
        """ Add comment to an Issue """
        payload = {
            'body': comment,
            'visibility': {
                'type': 'role',
                'value': role
            }
        }
        params = f'issue/{issue}/comment?renderedBody=true'
        self.api_call('POST', params, payload=payload)

    def agile_api_call(self, params=None, url=None, payload=None, stream=False):
        """ Makes an Agile API call """
        if url is None:
            url = f'{self.url}/rest/agile/1.0/{params}'
        return self._execute('GET', url, payload, stream=stream)

    def tempo_log(self, worker, date, log, test=False):
        """ Log time """
        activity = log['activity']
        if activity not in TEMPO_ACT_TO_INT_MAP:
            raise RuntimeError(f'Unable to find activity in internal activity mapping: {activity}')
        act_code = TEMPO_ACT_TO_INT_MAP[activity]
        payload = {
            "attributes": {
                "_ActivityType_": act_code,
            },
            "billableSeconds": int(float(log['hours']) * 3600),
            "endDate": date,
            "originTaskId": log['issue'],
            "started": date,
            "timeSpentSeconds": int(float(log['hours']) * 3600),
            "worker": worker,
            "comment": log['comment'],
        }
        if not test:
            self._execute('POST', f'{self.url}/rest/tempo-timesheets/4/worklogs', payload=payload)

    def tempo_get(self, worker, date1, date2):
        """ Get time """
        payload = {
            "from": date1,
            "to": date2,
            "worker": [worker],
        }
        resp = self.tempo_api_call('worklogs/search', payload=payload)
        period = {}
        for item in resp:
            activity = item['attributes']['_ActivityType_']['value']
            hours = item['timeSpentSeconds']
            comment = item['comment']
            started = item['started'][:10]
            period.setdefault(started, [])
            issue = item['issue']
            period[started].append({
                'id': item['tempoWorklogId'],
                'issue': issue['key'],
                'activity': TEMPO_INT_TO_ACT_MAP[activity],
                'comment': comment,
                'hours': hours/60/60,
                'issue_summary': issue['summary']
            })
        return period

    def tempo_delete(self, id_, test=False):
        """ Delete time entry """
        if not test:
            self._execute('DELETE', f'{self.url}/rest/tempo-timesheets/4/worklogs/{id_}')
