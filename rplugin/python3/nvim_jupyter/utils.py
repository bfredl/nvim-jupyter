import argparse
import logging
import logging.config
from . import config as c


def set_logger(name):
    logging.config.dictConfig(c.logger_config)
    return logging.getLogger(name)


l = set_logger(__name__)


def set_argparser(args_to_set):
    argp = argparse.ArgumentParser(prog='NVimJupyter')
    argps = argp.add_subparsers()
    for command in args_to_set:
        subparser = argps.add_parser(command)
        for arg, opts in args_to_set[command].items():
            subparser.add_argument(*arg, **opts)
    return argp


def get_iopub_msg(kc, msg_id):
    '''Get the iopub socket message after execution
    '''
    msg = {}
    while True:
        iopub_msg = kc.get_iopub_msg()
        l.debug('IOPUB {}'.format(iopub_msg))
        if (
            iopub_msg['parent_header']['msg_id'] == msg_id and
            iopub_msg['msg_type'] in c.msg_types
        ):
            for key in iopub_msg['content']:
                msg[key] = iopub_msg['content'][key]
                if isinstance(msg[key], list):
                    msg[key] = '\n'.join(msg[key])
        if (
            iopub_msg['parent_header']['msg_type'] != 'kernel_info_request' and
            iopub_msg['msg_type'] == 'status' and
            iopub_msg['content']['execution_state'] == 'idle'
        ):
            break
    return msg


def format_msg(msg):
    '''Pretty format the message for output to `neovim` buffer
    '''
    l.debug('FORMAT {}'.format(msg))
    formatted_msg = dict(msg)
    formatted_msg['code'] = (
        msg['code'][:1] +
        '\n{whitespace}...: '
        .format(whitespace=' ' * (2 + len(str(msg['execution_count']))))
        .join(msg['code'][1:].split('\n'))
    )

    for key in c.messages:
        try:
            formatted_msg[key] = (
                c.color_regex.sub('', c.messages[key].format(**formatted_msg))
                .strip().split('\n')
            )
            if key != 'in':
                formatted_msg[key] += ['']
        except KeyError:
            pass
    l.debug('FORMATTED {}'.format(formatted_msg))
    return formatted_msg


def decode_args(nvim, args):
    """Helper function to decode from `bytes` to `str`

    `neovim` has some issues with encoding in Python3.
    """
    encoding = nvim.eval('&encoding')
    return [arg.decode(encoding) if isinstance(arg, bytes) else arg
            for arg in args]
