文档化脚本
===================

.. currentmodule:: click

Click 让文档化你的命令行工具变得非常容易。
首先，它自动生成帮助页面给你。同时目前没有
自定义图层功能，所有的文字内容都会被改变。

帮助内容
----------

命令和可选项都接收帮助参数。在命令中使用时，
函数的文档字符串会自动用作帮助内容。

简单的示例:

.. click:函数文档字符串作为帮助内容的示例::

    @click.command()
    @click.option('--count', default=1, help='number of greetings')
    @click.argument('name')
    def hello(count, name):
        """This script prints hello NAME COUNT times."""
        for x in range(count):
            click.echo('Hello %s!' % name)

运行时的情况:

.. click:run::

    invoke(hello, args=['--help'])


.. _documenting-arguments:

文档化参数
~~~~~~~~~~~~~~~~~~~~~

在使用 :func:`click.argument` 的时候不会得到一个 ``help`` 参数。
这是遵循 Unix 工具的通用惯例，因为使用参数只是为了必不缺少的事物，
并且在命令行帮助内容里对参数文档化都是通过名字来识别，也就是顾名思义。

你可以在函数文档字符串中来描述参数的参考信息:

.. click:文档化参数在函数文档字符串中实现的示例1::

    @click.command()
    @click.argument('filename')
    def touch(filename):
        """Print FILENAME."""
        click.echo(filename)

运行时的情况:

.. click:run::

    invoke(touch, args=['--help'])

或者你可以在函数文档字符串中对参数描述的明确些:

.. click:文档化参数在函数文档字符串中实现的示例2::

    @click.command()
    @click.argument('filename')
    def touch(filename):
        """Print FILENAME.

        FILENAME is the name of the file to check.
        """
        click.echo(filename)

运行时的情况:

.. click:run::

    invoke(touch, args=['--help'])

对于更多示例，阅读 :doc:`/arguments` 文档内容来了解。


防止二次打包
---------------------

Click 二次打包文档内容的默认行为是根据终端的宽来决定。
在一些情况中，这会有一个问题。主要问题是当显示代码示例时，
使用换行符是有意义的事情。

二次打包可以被禁用在每个段落上，通过使用 ``\b`` 转义字符
加入到单独一行上来实现。那么段落与段落就不会打包在一起了，
就实现了分段落显示帮助内容了，这就是禁用二次打包的效果。

示例:

.. click:防止二次打包示例::

    @click.command()
    def cli():
        """First paragraph.

        This is a very long second paragraph and as you
        can see wrapped very early in the source text
        but will be rewrapped to the terminal width in
        the final output.

        \b
        This is
        a paragraph
        without rewrapping.

        And this is a paragraph
        that will be rewrapped again.
        """

运行时的情况:

.. click:run::

    invoke(cli, args=['--help'])

.. _doc-meta-variables:

隐藏帮助内容
---------------------

Click 从函数文档字符串中获得命令的帮助内容。
不管如何做到的，如果你已经使用文档字符串来对
函数的参数做文档化工作，那么你要不想在帮助内容
中看到 :param: 和 :return: 这些内容的话，

你可以使用 ``\f`` 转移字符，该转义字符以后的
内容都会被 Click 隐藏起来，不再显示在帮助内容中。

示例:

.. click:隐藏帮助内容示例1::

    @click.command()
    @click.pass_context
    def cli(ctx):
        """First paragraph.

        This is a very long second
        paragraph and not correctly
        wrapped but it will be rewrapped.
        \f

        :param click.core.Context ctx: Click context.
        """

运行时的情况:

.. click:run::

    invoke(cli, args=['--help'])

注意一点，在只使用 ``\f``转义字符时，可能会出现二次打包的显示混乱问题，
要解决这个问题可以通过结合 ``\b`` 转义字符来修复。

.. click:隐藏帮助内容示例2::

    @click.command()
    @click.pass_context
    def cli(ctx):
        """First paragraph.

        \b
        This is a very long second
        paragraph and not correctly
        wrapped but it will be rewrapped.
        \f

        :param click.core.Context ctx: Click context.
        """

运行时的情况:

.. click:run::

    invoke(cli, args=['--help'])

元变量
--------------

可选项和参数形式都接受一个 ``metavar`` 参数，它可以改变
帮助页面中的元变量显示效果。默认版本是参数形式名带有下划线的
全大写形式，但也可以注释成不同形式。这个特性可以在所有层面上
实现自定义:

.. click:元变量示例::

    @click.command(options_metavar='<options>')
    @click.option('--count', default=1, help='number of greetings',
                  metavar='<int>')
    @click.argument('name', metavar='<name>')
    def hello(count, name):
        """This script prints hello <name> <int> times."""
        for x in range(count):
            click.echo('Hello %s!' % name)

运行时的情况:

.. click:run::

    invoke(hello, args=['--help'])


命令的简短帮助内容
------------------

对于命令或子命令来说，生成一个简短帮助内容有时是有帮助的。
默认情况是把命令的文档字符串内容作为帮助信息的内容，
那么也可以用短帮助参数来覆写要的显示帮助内容:

.. click:命令短帮助示例::

    @click.group()
    def cli():
        """A simple command line tool."""

    @cli.command('init', short_help='init the repo')
    def init():
        """Initializes the repository."""

    @cli.command('delete', short_help='delete the repo')
    def delete():
        """Deletes the repository."""

运行时的情况:

.. click:run::

    invoke(cli, prog_name='repo.py')


自定义帮助参数形式
----------------------------

.. versionadded:: 2.0

在 Click 中实现的帮助参数是一种非常特殊的方式。
不像其它的参数形式，帮助参数形式由 Click 自动
增加给任何一个命令，并且执行自动冲突解决方案。
默认情况下，帮助参数形式叫做 ``--help`` ，但
这也是可以改变的。如果一个命令自身实现了一个同名
参数形式的话，默认的帮助参数形式会拒绝接收。
这里有一个语境设置，可以用来覆写帮助参数形式的名字，
叫做 :attr:`~Context.help_option_names` 属性。

这里的示例把默认帮助参数形式变成了 ``-h`` 和 ``--help``
 两种形式，而不再只是 ``--help`` 一种形式了:

.. click:自定义帮助参数形式示例::

    CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

    @click.command(context_settings=CONTEXT_SETTINGS)
    def cli():
        pass

运行时的情况:

.. click:run::

    invoke(cli, ['-h'])

这里要注意一点，在命令中设置这个自定义帮助参数形式时，要写在第一个参数位置上才有效。
