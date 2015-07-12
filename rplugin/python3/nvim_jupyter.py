import argparse
import jupyter_client as jc
import logging
import logging.config
import neovim as nv
import os.path as osp


logging.config.dictConfig({
    'version': 1,
    'handlers': {'file': {'class': 'logging.FileHandler',
                          'level': 'DEBUG',
                          'filename': 'nvim_jupyter.log'}},
    'loggers': {'': {'handlers': ['file'],
                     'level': 'DEBUG'}}
})
l = logging.getLogger(__name__)


@nv.plugin
class NVimJupyter:
    def __init__(self, con_nvim):
        self._con_nvim = con_nvim.with_hook(nv.DecodeHook())
        self._argp = self._set_argparser(
            prog='NVimJupyter', args_to_set={
                ('--existing',): {'nargs': 1}
            }
        )
        self._new_kernel_started = self._km = self._kc = None

    @nv.command('JConnect', nargs='*', sync=True)
    def connect_handler(self, args):
        args = list(map(bytes.decode, args))
        args = self._argp.parse_args(args)
        try:
            self._kc = self._connect_to_existing_kernel(args.existing[0])
            self._new_kernel_started = False
        except AttributeError:
            self._kc = self._connect_to_new_kernel(args)
            self._new_kernel_started = True
        l.debug('kernel started: {}'.format(self._kc.kernel_info()))

    @nv.function('JExecute')
    def execute_handler(self, args):
        l.debug('execute: {}'.args)

    @nv.shutdown_hook
    def shutdown(self):
        l.debug('shutdown hook')
        if self._new_kernel_started is True:
            self._kc.shutdown()

    def _set_argparser(self, prog='DummyProg', args_to_set={}):
        argp = argparse.ArgumentParser(prog=prog)
        for a, kw in args_to_set.items():
            argp.add_argument(*a, **kw)
        return argp

    def _connect_to_existing_kernel(self, filehint):
        connection_file = (filehint
                           if osp.sep in filehint
                           else jc.find_connection_file(filehint))
        l.debug('con_file: {}'.format(connection_file))
        km = jc.KernelManager(connection_file=connection_file)
        km.load_connection_file()
        kc = km.client()
        kc.start_channels()
        return kc

    def _connect_to_new_kernel(self, args):
        km = jc.KernelManager()
        km.start_kernel()
        kc = km.client()
        km.start_channels()
        return kc

    def _execute(self, code):
        msg_id = self._kc.execute(code)
        while True:
            msg = self._kc.get_shell_msg(timeout=1)
            if msg['parent_header']['msg_id'] == msg_id:
                break
        l.debug('execute: {}, response: {}'.format(code, msg))
        return msg
