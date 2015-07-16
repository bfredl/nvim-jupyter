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


def format_msg(msg):
    '''Pretty format the message for output to `neovim` buffer
    '''
    l.debug('FORMAT {}'.format(msg))
    formatted_msg = dict(msg)
    formatted_msg['code'] = (
        msg['code'][:1] +
        '\n{whitespace}...: '
        .format(whitespace=' ' * (2 + len(str(msg['execution_count']))))
        .join(msg['code'][1:].splitlines())
    )

    for key in c.messages:
        try:
            formatted_msg[key] = (
                c.color_regex.sub('', c.messages[key].format(**formatted_msg))
                .strip().splitlines()
            )
            if key != 'in':
                formatted_msg[key] += ['']
        except KeyError:
            pass
    l.debug('FORMATTED {}'.format(formatted_msg))
    return formatted_msg

