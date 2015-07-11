import neovim


@neovim.plugin
class NVimJupyter:
    def __init__(self, con_nvim):
        self._con_nvim = con_nvim.with_hook(neovim.DecodeHook())

    @neovim.command('JConnect', nargs='*', sync=True)
    def jconnect_handler(self, args):
        self._con_nvim.current.line = (
            'JConnect: {}'.format(args)
        )
