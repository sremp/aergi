#!/usr/bin/env python3
""" PE Library module """

# pylint: disable=consider-using-f-string, logging-format-interpolation


import hashlib
import json
import logging
import os
import pickle
import re
import socket
import subprocess
import sys
import time


# pylint: disable=too-few-public-methods, import-outside-toplevel
class DispatchingFormatter:
    """ Used for logging """

    def __init__(self, formatters, default_formatter):
        self._formatters = formatters
        self._default_formatter = default_formatter

    def format(self, record):
        """ Format record """
        formatter = self._formatters.get(record.name, self._default_formatter)
        return formatter.format(record)


SDE_CONFIG = {
    'logger': None,
    'debug': True
}
FORMATTER_NO_TSTAMP = logging.Formatter('%(message)s')


def sde_debug(debug=None):
    """ Either set or get debug level """
    if debug is not None:
        # pylint: disable=global-statement
        SDE_CONFIG['debug'] = debug
    return SDE_CONFIG['debug']


def get_req_var(var):
    """ Get required env var """
    if var not in os.environ:
        raise RuntimeError(f'Variable not set: {var}')
    return os.environ[var]


def sde_get_log_dir(subdir=None):
    """ Get log directory """
    log_dir = os.getenv('SDE_LOG_DIR') or os.environ['HOME'] + '.sde-local/logs'
    if not subdir is None:
        log_dir += '/' + subdir
    return log_dir


def init_logging(name=None, dir='sde', stdout_only=False, command=None,
                 debug=True, quiet=False, use_tstamp=True):
    """ Initialize logging """
    # pylint: disable=too-many-arguments,redefined-builtin
    if name is None:
        name = os.path.basename(sys.argv[0])
        if name.endswith('.py'):
            name = name.replace('.py', '')

    sde_debug(debug)

    # pylint: disable=global-statement
    SDE_CONFIG['logger'] = logging.getLogger()
    SDE_CONFIG['logger'].setLevel(logging.DEBUG)

    formatter = set_logging_formatter(use_tstamp)
    log_file = setup_log_file(name, command, dir, formatter, stdout_only)
    set_logging_handler(stdout_only, formatter)

    if log_file is not None and not quiet:
        iprint('Log file: ' + log_file)

    if debug:
        dprint(sys.argv)

    if stdout_only:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    return log_file


def set_logging_formatter(use_tstamp):
    """ Set logging formatter with or without time stamp """
    if use_tstamp:
        formatter = logging.Formatter(
            '%(levelname).1s %(asctime)s %(message)s',
            datefmt='%Y%m%d_%H%M%S')
    else:
        formatter = FORMATTER_NO_TSTAMP
    return formatter


def setup_log_file(name, command, dir_, formatter, stdout_only):
    """ Set up log file """
    if not stdout_only:
        log_dir_var = 'SDE_LOG_DIR'
        log_dir = '{}/{}'.format(os.environ[log_dir_var], dir_)
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        if command is None:
            log_file = '%s/%s_%s.log' % (
                log_dir, tstamp(), name)
        else:
            log_file = '%s/%s_%s_%s.log' % (
                log_dir, tstamp(), name, command)
        lfh = logging.FileHandler(log_file)
        lfh.setLevel(logging.DEBUG)
        lfh.setFormatter(DispatchingFormatter(
            {'no_tstamp': FORMATTER_NO_TSTAMP,},
            formatter,
        ))
        SDE_CONFIG['logger'].addHandler(lfh)
    else:
        log_file = None
    return log_file


def set_logging_handler(stdout_only, formatter):
    """" Set up logging handler """
    lch = logging.StreamHandler(sys.__stdout__)

    if stdout_only is True:
        lch.setLevel(logging.DEBUG)
    else:
        lch.setLevel(logging.INFO)

    lch.setFormatter(DispatchingFormatter(
        {'no_tstamp': FORMATTER_NO_TSTAMP,},
        formatter,
    ))
    SDE_CONFIG['logger'].addHandler(lch)


def source_file(file_=os.environ['SDE_CONFIG'], blank_env=False, add_env=None):
    """ Source profile """
    if blank_env:
        env = {
            'PATH': os.environ['PATH'],
            'LOGNAME': os.environ['LOGNAME'],
            'HOME': os.environ['HOME'],
        }
    else:
        env = os.environ

    if add_env is not None:
        env.update(add_env)

    source = 'source {}'.format(file_)
    dump = f'{sys.executable} -c "import sys,os,pickle; ' \
            'sys.stdout.buffer.write(pickle.dumps(dict(os.environ)))"'
    output = subprocess.check_output(
        '%s && %s' %
        (source, dump), shell=True, stdin=subprocess.PIPE, env=env, executable=os.environ['SHELL'])
    try:
        env_result = pickle.loads(output)
    except pickle.UnpicklingError:
        eprint('Error while pickle.loads:\n{}'.format(output))
        raise
    if blank_env:
        for var in ['_', 'SHLVL', 'HOME', 'LOGNAME', 'PWD', 'PATH']:
            if var in env_result:
                del env_result[var]
    return env_result


def dprint(msg, data=None):
    """ Debug print, including tstamp """
    if SDE_CONFIG['debug'] and msg is not None and msg != '' and SDE_CONFIG['logger'] is not None:
        SDE_CONFIG['logger'].debug((str(msg)).encode('ascii', 'ignore').decode('ascii'))
        if data is not None:
            for key, value in sorted(data.items()):
                line = f'  - {key}: {value}'
                SDE_CONFIG['logger'].debug(line.encode('ascii', 'ignore').decode('ascii'))


def iprint(msg, data=None):
    """ Informational print, including tstamp """
    if msg is not None and msg != '':
        SDE_CONFIG['logger'].info((str(msg)).encode('ascii', 'ignore').decode('ascii'))
        if data is not None:
            for key, value in sorted(data.items()):
                line = f'  - {key}: {value}'
                SDE_CONFIG['logger'].info(line.encode('ascii', 'ignore').decode('ascii'))


def wprint(msg, data=None):
    """ Warning print, including tstamp """
    if msg is not None and msg != '':
        SDE_CONFIG['logger'].warning((str(msg)).encode('ascii', 'ignore').decode('ascii'))
        if data is not None:
            for key, value in sorted(data.items()):
                line = f'  - {key}: {value}'
                SDE_CONFIG['logger'].warning(line.encode('ascii', 'ignore').decode('ascii'))


def eprint(msg, data=None):
    """ Error print, including tstamp """
    if msg is not None and msg != '':
        SDE_CONFIG['logger'].error((str(msg)).encode('ascii', 'ignore').decode('ascii'))
        if data is not None:
            for key, value in sorted(data.items()):
                line = f'  - {key}: {value}'
                SDE_CONFIG['logger'].error(line.encode('ascii', 'ignore').decode('ascii'))


def tstamp(val=None, form=1, show_time=True, milli=False):
    """ Return either current, or specified tstamp string """
    if val is None:
        ttt = time.localtime()
    else:
        ttt = time.localtime(val)
    if form == 1:
        if show_time:
            result = time.strftime('%Y%m%d_%H%M%S', ttt)
        else:
            result = time.strftime('%Y%m%d', ttt)
    else:
        if show_time:
            result = time.strftime('%Y/%m/%d %H:%M:%S', ttt)
        else:
            result = time.strftime('%Y/%m/%d', ttt)
    if milli:
        cur = time.time()
        ms_ = ((cur - int(cur)) * 1000)
        result = '{}.{}'.format(result, ms_)
    return result


def exec_cmd(cmd, msg=None, echo=False, show=False, save=False,
             ignore_errors=False, show_tstamp=True, log=True, json_output=False):
    """ Execute command """
    # pylint: disable=too-many-arguments
    _, ret = _sde_exec_cmd(cmd=cmd,
                           msg=msg,
                           echo=echo,
                           show=show,
                           save=save,
                           ignore_errors=ignore_errors,
                           show_tstamp=show_tstamp,
                           log=log,
                           json_output=json_output)
    return ret


def exec_cmd_w_rc(cmd, msg=None, echo=False, show=False, save=False,
                  ignore_errors=False, show_tstamp=True, log=True, json_output=False):
    """ Execute command """
    # pylint: disable=too-many-arguments
    return _sde_exec_cmd(cmd, msg, echo, show, save, ignore_errors, show_tstamp, log, json_output)


def _sde_exec_cmd(cmd, msg=None, echo=False, show=False,
                  save=False, ignore_errors=False, show_tstamp=True, log=True, json_output=False):
    """ Execute command """
    # pylint: disable=too-many-arguments,too-many-branches,too-many-locals
    if msg:
        dprint(msg)

    if echo:
        iprint('Executing: ' + cmd)

    if log and SDE_CONFIG['logger']:
        dprint('Executing: ' + cmd + ', in directory: ' + os.getcwd())

    # pylint: disable=consider-using-with
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=os.environ)

    output = []
    for line in proc.stdout:
        str_ = line.decode('utf-8', 'ignore').rstrip()
        if show:
            if str_ is not None and str_ != '':
                if show_tstamp:
                    SDE_CONFIG['logger'].info(str_)
                else:
                    logging.getLogger('no_tstamp').info(str_)
        else:
            if str_ is not None and str_ != '' and SDE_CONFIG['logger']:
                if show_tstamp:
                    dprint(str_)
                else:
                    logging.getLogger('no_tstamp').info(str_)
        output.append(str_)
    retval = proc.wait()

    if save:
        if not json_output:
            ret = output
        else:
            ret = json.loads('\n'.join(output))
    else:
        ret = None

    if not ignore_errors and retval != 0:
        if not show and not save:
            for line in output:
                print(line)
        if len(output) > 0:
            last_line = output[-1]
        else:
            last_line = 'N/A'
        raise RuntimeError('Execution failed: {} ({}, {})'.format(cmd, retval, last_line))

    proc.stdout.close()
    return retval, ret


def md5_digest(file=None, data=None):
    """ Return either file or data md5 digest """
    if data is None:
        with open(file, 'rb') as ifp:
            data = ifp.read()
    digest = hashlib.md5(data).hexdigest()
    return digest


def sha256_digest(file):
    """ Return either file or data sha256 digest """
    with open(file, 'rb') as ifp:
        data = ifp.read()
        digest = hashlib.sha256(data).hexdigest()
    return digest


def check_server_port(host, port):
    """ Check whether server port is connect-able """
    sock = socket.socket()
    result = True
    try:
        sock.connect((host, int(port)))
    except: # pylint: disable=bare-except
        result = False
    sock.close()
    return result


def set_export(file_, dict_):
    """ Add export var to a sub-profile """
    if '/' not in file_:
        file_ = os.environ['HOME'] + '/' + file_
    with open(file_, 'r', encoding='utf-8') as ifp:
        cont = ifp.readlines()

    found = []
    new_content = []
    for line in cont:
        new_line = line
        for name, value in dict_.items():
            matched = re.search(r'(\s*export {}=).*'.format(name), line)
            if matched:
                if value is None:
                    new_line = None
                else:
                    new_line = '{}"{}"\n'.format(matched.group(1), value)
                    found.append(name)
        if new_line is not None:
            new_content.append(new_line)

    for name, value in sorted(dict_.items()):
        dprint('Setting {}={}'.format(name, value))
        if name not in found and value is not None:
            new_content.append('export {}="{}"\n'.format(name, value))

    with open(file_, 'w', encoding='utf-8') as ofp:
        for line in new_content:
            ofp.write(line)


def handle_error(print_error=True, exit_code=None):
    """ Handle error """
    if print_error:
        error = str(sys.exc_info()[1])
        eprint(error)
        SDE_CONFIG['logger'].debug("The following error has occured:", exc_info=sys.exc_info())
    sys.exit(exit_code or 1)


def is_json(text):
    """ Test if string is json """
    result = True
    try:
        _ = json.loads(text)
    except json.decoder.JSONDecodeError:
        result = False
    return result


def validate_json(file_name, quiet=False):
    """ Validate json file """
    valid = True
    try:
        with open(file_name, encoding='utf-8') as inf:
            _ = json.load(inf)
    except FileNotFoundError:
        valid = False
        if not quiet:
            print('File not found: {}'.format(file_name), file=sys.stderr)
    except json.decoder.JSONDecodeError:
        valid = False
        if not quiet:
            print('Json file is not valid: {}'.format(file_name), file=sys.stderr)
    if valid and not quiet:
        print('Json file is valid: {}'.format(file_name))
    return valid
