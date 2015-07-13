from collections import OrderedDict
import os.path as osp
import re
import sys


MAX_I = 2147483647


logger_config = {
    'version': 1,
    'handlers': {'file': {'class': 'logging.FileHandler',
                          'level': 'DEBUG',
                          'filename': osp.join(
                              osp.dirname(sys.modules[__name__].__file__),
                              'nvim_jupyter.log'
                          )}},
    'loggers': {'': {'handlers': ['file'],
                     'level': 'DEBUG'}},
    'disable_existing_loggers': False
}


args_to_set = {
    'JConnect': {('--existing',): {'nargs': 1}}
}

messages = OrderedDict(
    [('in', 'In [{execution_count}]: {code}'),
     ('out', 'Out[{execution_count}]: {data[text/plain]}'),
     ('stdout', '{text}'),
     ('err', '{traceback}')]
)

msg_types = ['error', 'execute_input', 'execute_result', 'stream']

color_regex = re.compile(r'\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|k]',
                         re.IGNORECASE)
