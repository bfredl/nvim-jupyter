"""
# nvim-jupyter (_testing_)

Flexible [neovim] - [jupyter] kernel interaction. Outputs the following
functionality to [neovim]:

- `(c) JConnect [--existing filehint]`

  connect to new or existing kernel (using the `[--existing filehint]`)
  argument, where `[filehint]` is either the `*` (star) in `kernel-*.json`
  or the absolute path of the connection file.

- `(c) [range]JExecute`

  Send current line to be executed by the kernel or if `[range]` is given
  execute the appropriate lines.

Legend `(c)` = command

Stay tuned, more to come!

[neovim]: http://neovim.io/
[jupyter]: https://jupyter.org/
"""
import argparse
import jupyter_client as jc
import logging
import logging.config
import neovim as nv
import os.path as osp


# set up logger
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
        """Initialize NVimJupyter plugin

        Paramters
        ---------
        nvim: object
            The `neovim` communication channel.
        """
        self.nvim = nvim.with_hook(nv.DecodeHook())
        self.new_kernel_started = None
        self.buffer = None
        self.kc = None
        self._argp = None

    @property
    def argp(self):
        """ArgumentParser instance

        This is used for accessing arguments for `neovim` commands. It offers a
        very powerful interface for doing that (yet to be put to the test).
        """
        if self._argp is None:
            args_to_set = {
                ('--existing',): {'nargs': 1}
            }
            self._argp = argparse.ArgumentParser('NVimJupyter')
            for a, kw in args_to_set.items():
                self._argp.add_argument(*a, **kw)
        return self._argp

    def _set_buffer(self):
        """Create new scratch buffer in neovim for feedback from kernel

        Returns
        -------
        buffer: `neovim` buffer
            The newly created buffer object.
        """
        self.nvim.command('5new')
        self.nvim.current.buffer.name = '[IPython]'
        self.nvim.current.buffer.options['buftype'] = 'nofile'
        self.nvim.current.buffer.options['bufhidden'] = 'hide'
        self.nvim.current.buffer.options['swapfile'] = False
        self.nvim.current.buffer.options['readonly'] = True
        buffer = self.nvim.current.buffer
        self.nvim.command('wincmd j')
        return buffer

    @nv.command('JConnect', nargs='*', sync=True)
    def connect_handler(self, args):
        """`neovim` command for connecting to new or existing kernel

        Parameters
        ----------
        args: list of str
            Arguments passed from `neovim`.

        Notes
        -----
        There's a problem: `neovim` passes a `list` of `bytes` instead of
        `str`. Need to manually decode them.
        """
        args = self._decode_args(args)
        args = self.argp.parse_args(args)
        if args.existing:
            self.kc = self._connect_to_existing_kernel(args.existing[0])
            self.new_kernel_started = False
        else:
            self.kc = self._connect_to_new_kernel(args)
            self.new_kernel_started = True
        if self.buffer is None:
            self.buffer = self._set_buffer()
        l.debug('kernel started: {}'.format(self.kc.get_shell_msg()))

    @nv.command('JExecute', range='')
    def execute_handler(self, r):
        """`neovim` command for executing code

        It either executes current line or the visual selection.

        Parameters
        ----------
        r: list
            A list of two numbers representing the beginning and finish of the
            `neovim` range object.
        """
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
        """Don't know what this hook does...
        """
        l.debug('shutdown hook')
        if self.new_kernel_started is True:
            self.kc.shutdown()

    def _connect_to_existing_kernel(self, filehint):
        """Connect to existing `jupyter` kernel

        Parameters
        ----------
        filehint: str
            The `*` (star) in `kernel-*.json` or the absolute file path to the
            kernel connection file.

        Returns
        -------
        kc: jupyter_client.KernelClient
            The kernel client in charge of negotiating communication between
            `neovim` and the `jupyter` kernel.
        """
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
        """Start and connect to new `jupyter` kernel

        Parameters
        ----------
        args: argparse.ArgumentParser parsed arguments
            Arguments given to `JConnect` command through `neovim`.

        Returns
        -------
        kc: jupyter_client.KernelClient
            The kernel client in charge of negotiating communication between
            `neovim` and the `jupyter` kernel.
        """
        km = jc.KernelManager()
        km.start_kernel()
        kc = km.client()
        kc.start_channels()
        return kc

    def _print_to_buffer(self, response):
        self.buffer.append('Out[{execution_count}]:'
                           .format(**response['content']))

    def _decode_args(self, args):
        """Helper function to decode from `bytes` to `str`

        `neovim` has some issues with encoding in Python3.
        """
        encoding = self.nvim.eval('&encoding')
        return [arg.decode(encoding) if isinstance(arg, bytes) else arg
                for arg in args]
