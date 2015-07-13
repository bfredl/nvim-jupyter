"""
Flexible [neovim] - [Jupyter] kernel interaction. Augments [neovim] with the following
functionality:

- `(c) JConnect [--existing filehint]` - **first connect to kernel**

  connect to new or existing kernel (using the `[--existing filehint]`)
  argument, where `[filehint]` is either the `*` (star) in `kernel-*.json`
  or the absolute path of the connection file.

- `(c) [range]JExecute`

  send current line to be executed by the kernel or if `[range]` is given
  execute the appropriate lines. This also works with visual selections
  (including block selections). Example:
  ```
  bla bla bla print('test') more bla
  some bla    test = 5; test
  ```
  it is possible here (for whatever reason) to select the text made out of
  `print('test')` and `test = 5; test` and it will execute as if it were
  two lines of code (think of `IPython`). This works because the selection
  doesn't have any leading whitespace. In the more usual case, `print('test')`
  and `test = 5; test` can be selected one at a time and the execution proceeds
  as expected. _This upgrade of `JExecute` doesn't add new functions or
  commands to [neovim] so it is quite natural to use_

Legend `(c)` = command

[neovim]: http://neovim.io/
[Jupyter]: https://jupyter.org/
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
        self.r = None
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
        self._print_to_buffer(
            ['Jupyter {implementation_version} /'
             ' Python {language_info[version]}'
             .format(**self.kc.get_shell_msg()['content']),
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
        (x0, y0), (x1, y1) = (self.nvim.current.buffer.mark('<'),
                              self.nvim.current.buffer.mark('>'))
        y0, y1 = min(y0, y1), max(y0, y1)
        if x0 == y0 == x1 == y1 == 0:
            (x0, x1), (y0, y1) = r, (0, c.MAX_I)
        code = '\n'.join(line[y0:y1 + 1]
                         for line in self.nvim.current.buffer[x0 - 1:x1])
        msg_id = self.kc.execute(code)
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
        self.buffer.append('In [ ]')
        self.buffer.options['readonly'] = True
        self.window.cursor = len(self.buffer), 0
