终端补全功能
=============

.. versionadded:: 2.0

从 Click 2.0 版本开始，有了内置支持终端 Bash 环境下的补全功能。
对每一个 Click 脚本名来说都能够使用这个补全功能。
当使用这种补全功能时会有一些限制，但对大部分都是应该能够有效的。

限制
-----------

Bash 终端补全只在脚本被正确地安装后才有效，
并且不再通过写 ``python`` 命令来执行脚本。
对于如何正确安装，阅读 :ref:`setuptools-integration` 参考文档。
 Click 目前只支持 Bash 和 Zsh 终端环境的补全。

什么是补全功能？
-----------------

通用中，在 Bash 环境中的补全就是在输入子命令、选项和任何
一个选项或参数值时，使用 TAB 按键来自动填写这些内容，或
提示有哪些子命令或选项可用。
罗列出能够使用的众多子命令和选项时，至少要提供一个减号，例如::

    $ repo <TAB><TAB>
    clone    commit   copy     delete   setuser
    $ repo clone -<TAB><TAB>
    --deep     --help     --rev      --shallow  -r

另外，自定义这些建议内容可以提供给许多参数和选择，都是通过
 ``autocompletion`` 参数设置决定。
 ``autocompletion`` 应该是一个回调函数，该函数返回由
许多字符串组成的一个列表。当许多建议需要动态生成在终端补全时就显得有用了。
这个回调函数会有 3 个关键字参数需要代入:

- ``ctx`` - 当前 click 的语境。
- ``args`` - 需要代入的参数组成的一个列表。
- ``incomplete`` - 需要补全的部分单词，字符串形式。
  如果还没输出字符的话，也许是一个空字符串 ``''`` 

如下是使用一个回调函数来动态生成建议的示例:

.. click:终端命令补全示例::

    import os

    def get_env_vars(ctx, args, incomplete):
        return [k for k in os.environ.keys() if incomplete in k]

    @click.command()
    @click.argument("envvar", type=click.STRING, autocompletion=get_env_vars)
    def cmd1(envvar):
        click.echo('Environment variable: %s' % envvar)
        click.echo('Value: %s' % os.environ[envvar])


ZSH 终端补全帮助字符串
----------------------------------

ZSH 终端支持为补全显示文档字符串。
这些文档字符串来自选项和子命令的辅助参数。
对于动态地生成补全帮助字符串可以通过返回一个元组来提供，
而不是返回一个字符串了。元组的第一个元素是补全内容，
第二个元素是要现实的帮助字符串内容。

如下是使用一个回调函数来生成含有帮助字符串的动态建议示例:

.. click:补全帮助字符串示例::

    import os

    def get_colors(ctx, args, incomplete):
        colors = [('red', 'help string for the color red'),
                  ('blue', 'help string for the color blue'),
                  ('green', 'help string for the color green')]
        return [c for c in colors if incomplete in c[0]]

    @click.command()
    @click.argument("color", type=click.STRING, autocompletion=get_colors)
    def cmd1(color):
        click.echo('Chosen color is %s' % color)


激活补全功能
--------------

要激活 Bash 终端补全功能，你需要告诉 Bash 补全功能可以给你的脚本使用。
那么如何告诉 Bash 补全功能作用在你的脚本上呢？
任何一个 Click 应用程序自动地提供补全功能支持。
通用的方法是通过一个名叫 ``_<PROG_NAME>_COMPLETE`` 的魔法环境变量来生效，
其中 ``<PROG_NAME>`` 部分是你的应用程序可执行名字，且全大写形式，
脚本名字中含有减号的话，要改写成下划线。

如果你的命令行工具叫做 ``foo-bar`` 的话，那么魔法变量就要写成
 ``_FOO_BAR_COMPLETE`` 了。通过使用 ``source`` 命令来导出
这个值后，那么此时激活的脚本就可以如往常一样激活了自动补全功能。

例如，开启 Bash 补全功能给你的 ``foo-bar`` 脚本，
那么就要把如下配置内容写在你的 ``.bashrc`` 文件中::

    eval "$(_FOO_BAR_COMPLETE=source foo-bar)"

对于 zsh 终端的用户来说，
要把如下配置内容增加到你的 ``.zshrc`` 文件中::

    eval "$(_FOO_BAR_COMPLETE=source_zsh foo-bar)"

配置完后，如果是在测试时可能需要执行一次像 ``source ~/.bash_rc`` 命令后，
你的自动补全功能就开启完毕。

激活终端脚本
-----------------

上面的激活示例会在启动时一直触发你的应用程序。
如果你有许多 Click 应用程序的话，这也许会让你的终端激活时间变慢。
另外一种解决方案是，你可以转换成一个终端脚本文件，
这也是 Git 和其它系统所使用的方法。

这实现起来是容易的，对于 Bash 终端来说::

    _FOO_BAR_COMPLETE=source foo-bar > foo-bar-complete.sh

对于 zsh 终端来说:

    _FOO_BAR_COMPLETE=source_zsh foo-bar > foo-bar-complete.sh

然后你可以把这条内容写在你的 .bashrc 或 .zshrc 文件中::

    . /path/to/foo-bar-complete.sh


