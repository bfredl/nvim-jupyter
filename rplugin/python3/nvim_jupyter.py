import neovim


@neovim.plugin
class NVimJupyter:
    def __init__(self, vim):
        self.vim = vim

    @neovim.command('JConnect', nargs='*', sync=True)
    @neovim.encoding
    def jconnect_handler(self, args):
        self.vim.current.line = (
            'JConnect: {}'.format(args)
        )
