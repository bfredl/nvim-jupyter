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
