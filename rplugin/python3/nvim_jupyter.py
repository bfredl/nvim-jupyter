import neovim


@neovim.plugin
class NVimJupyter:
    def __init__(self, vim):
        self.vim = vim

    @neovim.command('Test', range='', nargs='*', sync=True)
    def command_handler(self, args, range):
        self.vim.current.line = (
            'Called command Test: args: {}, range: {}'
            .format(args, range)
        )
