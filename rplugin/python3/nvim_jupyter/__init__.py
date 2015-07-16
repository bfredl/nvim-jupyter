"""
Flexible [neovim] - [Jupyter] kernel interaction. Augments [neovim] with the
following functionality:

- `(c) JKernel [-e/--existing [filehint]]` - **first connect to kernel**

  connect to new or existing kernel (using the `[-e/--existing [filehint]]`)
  argument, where `[filehint]` is either the `*` (star) in `kernel-*.json`
  or the absolute path of the connection file. If `JKernel` is used without any
  arguments then it starts a new kernel. If `-e/--existing` is provided
  (without the optional [filehint]) then an attempt to connect to an existing
  kernel is made. If kernel is not found then it doesn't create a new kernel.
  If [filehint] is given and not found, again, it doesn't create a kernel.

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

import jupyter_client as jc
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
        self.nvim = nvim
        self.argp = u.set_argparser(c.args_to_set)
        self.new_kernel_started = None
        self.buffer = None
        self.window = None
        self.kc = None

    @nv.command('JKernel', nargs='*', sync=True)
    def connect_handler(self, args):
        """`neovim` command for connecting to new or existing kernel

        Parameters
        ----------
        args: list of str
            Arguments passed from `neovim`.
        """
        # allow only one connection
        if self.kc is not None:
            return

        args = self.argp.parse_args(['JKernel'] + args)
        try:
            l.debug('KERNEL START')
            self.kc, self.new_kernel_started = self._connect_to_kernel(args)
            l.debug('KERNEL BUFF')
            # this should be executed once only anyway
            self.buffer, self.window = self._set_buffer_and_window()
            # consume first iopub message (starting)
            self.kc.get_iopub_msg()
            l.debug('KERNEL BEFORE SHELL {}', self.new_kernel_started)
            self._print_to_buffer(
                ['Jupyter {implementation_version} /'
                 ' Python {language_info[version]}'
                 .format(**self.kc.get_shell_msg()['content']),
                 '']
            )
        except (OSError, FileNotFoundError):
            self._error(msg='Could not find connection file. Not connected!',
                        prefix='[JKernel]: ')
            l.debug('KERNEL EXCEPT')

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
        (y0, x0), (y1, x1) = (self.nvim.current.buffer.mark('<'),
                              self.nvim.current.buffer.mark('>'))
        x0, x1 = min(x0, x1), max(x0, x1)
        l.debug('MARKS {}'.format((x0, x1, y0, y1)))
        # it's enough to verify that the rows are `(0, 0)` because
        # `neovim` valid row numbering starts at 1
        if y0 == y1 == 0:
            (y0, y1), (x0, x1) = r, (0, c.MAX_I)
        else:
            # for the time being deleting the marks will have to do (but only
            # in case there is an initial selection)
            self.nvim.command('delmarks <>')
        x1, y0 = x1 + 1, y0 - 1
        code = '\n'.join(line[x0:x1].strip()
                         if y1 - y0 == 1 else
                         line[x0:x1].rstrip()
                         for line in self.nvim.current.buffer[y0:y1])
        msg_id = self.kc.execute(code)
        msg = self._get_iopub_msg(msg_id)
        self._print_to_buffer(msg)

    @nv.shutdown_hook
    def shutdown(self):
        """Don't know what this hook does...
        """
        l.debug('shutdown hook')
        if self.new_kernel_started is True:
            self.kc.shutdown()

    def _set_buffer_and_window(self):
        """Create new scratch buffer in neovim for feedback from kernel

        Returns
        -------
        buffer: `neovim` buffer
            The newly created buffer object.
        window: `neovim` window
            The window associated with `buffer`.
        """
        self.nvim.command('{height}new'.format(
            height=int(self.nvim.current.window.height * 0.3))
        )
        # TODO: these will need to be changed based on the response from
        #       the kernel
        self.nvim.current.buffer.name = '[IPython]'
        self.nvim.current.buffer.options['buftype'] = 'nofile'
        self.nvim.current.buffer.options['bufhidden'] = 'hide'
        self.nvim.current.buffer.options['swapfile'] = False
        self.nvim.current.buffer.options['readonly'] = True
        self.nvim.current.buffer.options['filetype'] = 'python'
        self.nvim.current.buffer.options['syntax'] = 'python'
        self.nvim.command('syntax enable')
        buffer = self.nvim.current.buffer
        window = self.nvim.current.window
        self.nvim.command('wincmd j')
        return buffer, window

    def _connect_to_kernel(self, args):
        """Start new or connect to existing `Jupyter` kernel

        Parameters
        ----------
        args: argparse.ArgumentParser parsed arguments
            Arguments given to `JKernel` command through `neovim`.

        Returns
        -------
        kc: jupyter_client.KernelClient
            The kernel client in charge of negotiating communication between
            `neovim` and the `Jupyter` kernel.
        new_kernel_started: bool
            Flag to keep track of new / existing kernel.
        """
        l.debug('ARGS {}'.format(args))
        if args.existing is not None:
            connection_file = jc.find_connection_file(filename=args.existing)
            l.debug('CONNECT {}, {}'.format(connection_file, args.existing))
            km = jc.KernelManager(connection_file=connection_file)
            km.load_connection_file()
            new_kernel_started = False
        else:
            km = jc.KernelManager()
            km.start_kernel()
            new_kernel_started = True
        kc = km.client()
        kc.start_channels()
        return kc, new_kernel_started

    def _get_iopub_msg(self, msg_id):
        '''Get the iopub socket message after execution
        '''
        msg = {}
        while True:
            iopub_msg = self.kc.get_iopub_msg()
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
                iopub_msg['parent_header']['msg_type'] != 'kernel_info_request'
                and iopub_msg['msg_type'] == 'status'
                and iopub_msg['content']['execution_state'] == 'idle'
            ):
                break
        return msg

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

    def _echo(self, msg, prefix='', hl='NormalMsg'):
        self.nvim.command('echohl {hl} | echom "{prefix}{msg}" |'
                          ' echohl NormalMsg'
                          .format(msg=msg, prefix=prefix, hl=hl))

    def _warning(self, msg, prefix=''):
        self._echo(msg, prefix=prefix, hl='WarningMsg')

    def _error(self, msg, prefix=''):
        self._echo(msg, prefix=prefix, hl='ErrorMsg')
