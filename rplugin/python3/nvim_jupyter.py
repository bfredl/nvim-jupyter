'''
# nvim-jupyter (_testing_)

Flexible [neovim] - [jupyter] kernel interaction. Outputs the following
functionality to [neovim]:

(c) `jconnect [--existing filehint]`
    connect to new or existing kernel (using the `[--existing filehint]`)
    argument, where `[filehint]` is either the `*` (star) in `kernel-*.json`
    or the absolute path of the connection file.
(c) `[range]jexecute`
    Send current line to be executed by the kernel or if `[range]` is given
    execute the appropriate lines.

Legend (c) = command

Stay tuned, more to come!

[neovim]: http://neovim.io/
[jupyter]: https://jupyter.org/
'''
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
    def __init__(self, nvim):
        self.nvim = nvim.with_hook(nv.DecodeHook())
        self.new_kernel_started = None
        self.kc = None
        self._argp = None
        self._buffer = None

    @property
    def argp(self):
        if self._argp is None:
            args_to_set = {
                ('--existing',): {'nargs': 1}
            }
            self._argp = argparse.ArgumentParser('NVimJupyter')
            for a, kw in args_to_set.items():
                self._argp.add_argument(*a, **kw)
        return self._argp

    @property
    def buffer(self):
        if self._buffer is None:
            self.nvim.command('5new')
            self.nvim.current.buffer.name = '[IPython]'
            self.nvim.current.buffer.options['buftype'] = 'nofile'
            self.nvim.current.buffer.options['bufhidden'] = 'hide'
            self.nvim.current.buffer.options['swapfile'] = False
            self.nvim.current.buffer.options['readonly'] = True
            self._buffer = self.nvim.current.buffer
            # self.nvim.command('wincmd j')
        return self._buffer

    @nv.command('jconnect', nargs='*', sync=True)
    def connect_handler(self, args):
        args = self._decode_args(args)
        args = self.argp.parse_args(args)
        if args.existing:
            self.kc = self._connect_to_existing_kernel(args.existing[0])
            self.new_kernel_started = False
        else:
            self.kc = self._connect_to_new_kernel(args)
            self.new_kernel_started = True
        l.debug('kernel started: {}'.format(self.kc.get_shell_msg()))

    @nv.command('jexecute', range='')
    def execute_handler(self, r):
        r0, r1 = r
        lines = '\n'.join(self.nvim.current.buffer[r0 - 1:r1])
        msg_id = self.kc.execute(lines)
        response = self.kc.get_shell_msg()
        if msg_id != response['parent_header']['msg_id']:
            l.debug('execute_handler: something not right!')
        l.debug('{} - {}'.format(msg_id, response))
        l.debug('execute_handler: {}'.format(lines))
        self._print_to_buffer(response)

    @nv.shutdown_hook
    def shutdown(self):
        l.debug('shutdown hook')
        if self.new_kernel_started is True:
            self.kc.shutdown()

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

    def _print_to_buffer(self, response):
        self.buffer.append('Out[{execution_count}]:\n'
                           .format(**response['content']))

    def _decode_args(self, args):
        encoding = self.nvim.eval('&encoding')
        return [arg.decode(encoding) if isinstance(arg, bytes) else arg
                for arg in args]
