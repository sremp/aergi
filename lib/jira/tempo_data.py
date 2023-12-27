#!/usr/bin/env python3
""" Tempo timesheet manipulation """

import json
import os
import re
from pprint import pprint # pylint: disable=unused-import
import yaml


COMMENT_TO_ACT_MAP = 'comment-to-act.json'
WORK_MAP = 'work.json'
WORK_MAP_CUSTOM = 'work-custom.json'
ACTIVITY_MAP = 'activity.json'
ISSUE_SUMMARY_MAP = 'issues.json'


class TempoData:
    """ Tempo time entries """
    def __init__(self):
        self.home = os.environ['TEMPI_HOME']
        self.c2a = self.get_config(COMMENT_TO_ACT_MAP)
        self.cfg = self.get_config(WORK_MAP)
        self.cfg.update(self.get_config_custom(WORK_MAP_CUSTOM))
        self.activity_map = self.get_config(ACTIVITY_MAP)
        self.issues = self.get_config(ISSUE_SUMMARY_MAP)
        self.entries = {}

    def get_config(self, file):
        """ Get config file """
        path = f'{self.home}/config/{file}'
        with open(path, encoding='utf-8') as inf:
            data = json.load(inf)
        return data

    @staticmethod
    def get_config_custom(file):
        """ Get custom config file, optional """
        if os.path.isfile(file):
            with open(file, encoding='utf-8') as inf:
                data = json.load(inf)
        else:
            data = {}
        return data

    def diff(self, other):
        """ Compare with another instance of tempo data """
        results = {}
        dates = set(list(self.entries.keys()) + list(other.entries.keys()))
        for date in dates:
            results.setdefault(date, {'+': [], '-': []})
            if date in self.entries:
                for log in self.entries[date]:
                    if not other.log_exists(date, log):
                        results[date]['+'].append(log)
            if date in other.entries:
                for log in other.entries[date]:
                    if not self.log_exists(date, log):
                        results[date]['-'].append(log)
        return results

    def log_exists(self, date, log):
        """ Check whether log exists for date """
        exists = False
        if date in self.entries:
            for entry_log in self.entries[date]:
                if self.log_matches(entry_log, log):
                    exists = True
                    break
        return exists

    def log_matches(self, log1, log2):
        """ Check whether 2 logs match """
        matches = True
        for key in ['hours', 'issue', 'activity', 'comment']:
            if log1[key] != log2[key]:
                matches = False
                break
        return matches

    def from_file(self, file_name):
        """ Parse input file """
        with open(file_name, encoding='utf-8') as inf:
            file_data = yaml.safe_load(inf)
            for date, logs in (sorted(file_data.items())):
                self.parse_file_date_entries(str(date), logs)

    def from_jira(self, jira, worker, date_from, date_to):
        """ Get data from jira """
        self.entries = jira.tempo_get(worker, date_from, date_to)

    def parse_file_date_entries(self, date, logs):
        """ Parse time logs for a particular date """
        self.entries.setdefault(date, [])
        if logs is not None:
            for line in logs:
                if line:
                    line = line.strip()
                    if not line.startswith('#'):
                        self.parse_file_log_entry(date, line)

    def parse_file_log_entry(self, date, line):
        """ Parse single time log entry line """
        spl = line.strip().split(' ', 2)
        hours, work_item = spl[:2]
        comment = None
        if len(spl) == 3:
            comment = spl[2]

        if work_item not in self.cfg:
            if re.match('[A-Z0-9]+-[0-9]+$', work_item):
                issue = work_item
                if comment is None:
                    raise RuntimeError('Ticket number specified as work item, '
                                       'but no comment has been provided')
                activity = self.comment_to_activity(comment)
            else:
                raise RuntimeError('Work item not found and is not a ticket: '
                                   f'{work_item}. See {self.home}/config/{WORK_MAP} '
                                   f'and ./{WORK_MAP_CUSTOM}')
        else:
            issue = self.cfg[work_item]['issue']
            if 'activity' in self.cfg[work_item]:
                activity = self.cfg[work_item]['activity']
            else:
                activity = self.comment_to_activity(comment)

        use_comment = work_item
        if comment is not None:
            use_comment += f' - {comment}'
        entry = {
            'hours': float(hours),
            'issue': issue,
            'activity': self.activity_map[activity],
            'comment': use_comment,
            'debug_work_item': work_item,
        }
        if entry['issue'] in self.issues:
            entry['issue_summary'] = self.issues[entry['issue']]
        self.entries[date].append(entry)

    def comment_to_activity(self, comment):
        """ Convert comment to activity """
        activity = None
        for val in self.c2a['same']:
            if val in comment:
                activity = val
                break
        if activity is None:
            for key, val in self.c2a['map']:
                if re.search(key, comment):
                    activity = val
                    break
        return activity

    def get_from_to_dates(self):
        """ Get min and max dates from the Tempo data """
        dates = sorted(self.entries.keys())
        return dates[0], dates[-1]
