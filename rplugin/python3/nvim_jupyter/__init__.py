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

import neovim as nv
from . import config as c
from . import utils as u


l = u.set_logger(__name__)


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
        self.argp = u.set_argparser(c.args_to_set)
        self.new_kernel_started = None
        self.buffer = None
        self.window = None
        self.kc = None

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
        args = u.decode_args(self.nvim, args)
        args = self.argp.parse_args(['JConnect'] + args)
        if args.existing:
            self.kc = u.connect_to_existing_kernel(args.existing[0])
            self.new_kernel_started = False
        else:
            self.kc = u.connect_to_new_kernel(args)
            self.new_kernel_started = True
        if self.buffer is None:
            self.buffer, self.window = u.set_buffer(self.nvim)
        # consume first iopub message (starting)
        self.kc.get_iopub_msg()
        msg = self.kc.get_shell_msg()['content']
        self._print_to_buffer(
            ['Jupyter {implementation_version} /'
             ' Python {language_info[version]}'.format(**msg),
             '']
        )

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
        msg = u.get_iopub_msg(self.kc, msg_id)
        self._print_to_buffer(msg)

    @nv.shutdown_hook
    def shutdown(self):
        """Don't know what this hook does...
        """
        l.debug('shutdown hook')
        if self.new_kernel_started is True:
            self.kc.shutdown()

    def _print_to_buffer(self, msg):
        self.buffer.options['readonly'] = False
        if isinstance(msg, (str, list)):
            self.buffer.append(msg)
        else:
            self.buffer[len(self.buffer)] = None
            msg = u.format_msg(msg)
            for key in c.messages:
                try:
                    self.buffer.append(msg[key])
                except KeyError:
                    pass
        self.buffer.append('In []')
        self.buffer.options['readonly'] = True
        self.window.cursor = len(self.buffer), 0
