import neovim


@neovim.plugin
class NVimJupyter:
    def __init__(self, vim):
        self.vim = vim

    @neovim.command('Test', range='', nargs='*', sync=True)
    def command_handler(self, args, range):
        self.vim.current.line = (
            'Command: Called {} times, args: {}, range: {}'
            .format(self.calls, args, range)
        )
