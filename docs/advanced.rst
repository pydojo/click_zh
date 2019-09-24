高级模式
=================

.. currentmodule:: click

另外说一下共性的功能实现在 Click 库自身上的情况，
有许多无法数算的模式可以通过 Click 扩展来实现。
本篇文档有责任给一些专家们的见解，那就是我们还能做什么。

.. _aliases:

命令别名
---------------

许多工具支持命令别名 (阅读 `Command alias example
<https://github.com/pallets/click/tree/master/examples/aliases>`_)
例如，你可以配置 ``git`` 来接受 ``git ci`` 作为 ``git commit`` 的别名。
其它工具也支持自动发现那些自动短写形式的别名。

Click 不做这种盒外技术，但要自定义 :class:`Group` 类或任何其它一种
 :class:`MultiCommand` 类实例时，提供这种功能是非常容易的。

由于已经解释在 :ref:`custom-multi-commands` 参考文档中了，
一个多命令可以提供 2 个方法: :meth:`~MultiCommand.list_commands` 
方法和 :meth:`~MultiCommand.get_command` 方法。在这种特殊情况下，
你只需要稍后覆写成通用中你不想要的别名形式，并在帮助页面上可以避免困惑。

下面的例子实现了一个 :class:`Group` 类的子类，它接收了一个命令的前缀。
如果有一个命令叫 ``push`` 的话，这个子类会接受 ``pus`` 作为别名
 (那么这个别名就是不曾用过的):

.. click:命令别名示例::

    class AliasedGroup(click.Group):

        def get_command(self, ctx, cmd_name):
            rv = click.Group.get_command(self, ctx, cmd_name)
            if rv is not None:
                return rv
            matches = [x for x in self.list_commands(ctx)
                       if x.startswith(cmd_name)]
            if not matches:
                return None
            elif len(matches) == 1:
                return click.Group.get_command(self, ctx, matches[0])
            ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))

然后这个子类的用法如下:

.. click:命令别名用法示例::

    @click.command(cls=AliasedGroup)
    def cli():
        pass

    @cli.command()
    def push():
        pass

    @cli.command()
    def pop():
        pass

参数形式修改
-----------------------

参数形式 (可选项和参数) 都被直接指向命令回调，如同以前见过的一样。
一种共性方法来保护被代入给回调函数的参数形式就是一个参数形式要使用
 `expose_value` 参数，这个装饰器里的参数完全把参数形式给隐藏了。
这种方法有效是因为 :class:`Context` 类实例对象有一个
 :attr:`~Context.params` 属性，这个属性是一个所有参数形式组成的字典。
不管字典里是什么，都要被代入到回调函数中。

这可以用来组装增加的参数形式。通用中这种模式是不建议使用的，
但在有些情况里是有用的。至少要知道操作系统就是这种工作方式。

.. click:参数形式修改示例1::

    from urllib import request

    def open_url(ctx, param, value):
        if value is not None:
            ctx.params['fp'] = request.urlopen(value)
            return value

    @click.command()
    @click.option('--url', callback=open_url)
    def cli(url, fp=None):
        if fp is not None:
            click.echo('%s: %s' % (url, fp.code))

在这种情况下，回调函数返回了没有变更的 URL 但也把
第二个 ``fp`` 值代入到回调函数中了。不管如何做到的，
解决这里出现的问题时，更多的建议就是把这种信息代入到一个打包器中:

.. click:参数形式修改示例2::

    from urllib import request

    class URL(object):

        def __init__(self, url, fp):
            self.url = url
            self.fp = fp

    def open_url(ctx, param, value):
        if value is not None:
            return URL(value, request.urlopen(value))

    @click.command()
    @click.option('--url', callback=open_url)
    def cli(url):
        if url is not None:
            click.echo('%s: %s' % (url.url, url.fp.code))


令牌正常化
-------------------

.. versionadded:: 2.0

从 Click 2.0 开始，提供一个函数来对令牌进行序列化处理变得可能了。
令牌都是可选项名字、可选项的值、或命令的值。例如，这可以用来实现
大小写字母脱敏处理。

要使用这种特性，语境需要被代入一个函数，这个函数执行令牌的序列化处理。
例如，你可以有一个函数把令牌转换成全小写字母:

.. click:令牌正常化示例::

    CONTEXT_SETTINGS = dict(token_normalize_func=lambda x: x.lower())

    @click.command(context_settings=CONTEXT_SETTINGS)
    @click.option('--name', default='Pete')
    def cli(name):
        click.echo('Name: %s' % name)

运行时的情况:

.. click:run::

    invoke(cli, prog_name='cli', args=['--NAME=Pete'])

触发其它命令
-----------------------

有时候触发一个命令是通过另一个命令实现的，这可能是一件有趣的事情。
这种模式在通用中是 Click 不鼓励使用的，但仍然可能会出现。
对于这个特性，你可以使用 :func:`Context.invoke` 函数或者用
 :func:`Context.forward` 方法来实现。

它们俩个效果类似，但差异在于 :func:`Context.invoke` 函数很少
会用你提供的参数来触发另一个命令，你提供的参数扮演了一名调用者。
而 :func:`Context.forward` 方法会把当前命令的参数填入到另一个
命令中去。它们俩个都把命令作为第一参数位，其它的参数都会直接代入到
你所期望的命令中去。

示例:

.. click:触发其它命令示例::

    cli = click.Group()

    @cli.command()
    @click.option('--count', default=1)
    def test(count):
        click.echo('Count: %d' % count)

    @cli.command()
    @click.option('--count', default=2)
    @click.pass_context
    def dist(ctx, count):
        ctx.forward(test)
        ctx.invoke(test, count=42)

运行时的情况:

.. click:run::

    invoke(cli, prog_name='cli', args=['dist'])


.. _callback-evaluation-order:

回调评估顺序
-------------------------

Click 与其它一些命令行语法分析器工作起来有些不同，
因为要把参数的顺序与编程者定义参数时的顺序保持一样，
与用户定义的参数顺序也保持一样。所以触发任何一个回调
函数时参数的顺序不会变乱。

这是一项重要的概念，要理解这个概念，对于把来自 optparse 的
多层化模式，或者把其它系统的多层化模式移植到 Click 时都是重要的。
一个参数形式回调函数触发，在 optparse 里是作为语法分析步骤的一部分，
而在 Click 里一个回调函数的触发是在语法分析结束后发生。

主要的区别就是在 optparse 里，所有回调函数都要用生食值来触发，
而 Click 中的一个回调函数是在值经过完整的转换之后触发的。

通用中，触发的顺序是由用户提供给脚本的参数值顺序来驱动；
如果有一个可选项名叫 ``--foo`` 和另一个可选项名叫
 ``--bar`` 的话，如果用户调用是使用的顺序是
 ``--bar --foo`` 的话，那么回调 ``bar`` 会发生在回调 ``foo`` 之前。

对于这种规则有 3 个例外情况，是你们重点了解的:

期望参数形式:
    一个可选项可以设置成 "eager" 期望状态。所有期望的参数形式都要经过评估，
    而评估是在所有非期望参数形式评估之前完成，但这违反了用户在命令行输入的顺序。

    对于参数形式的执行和退出来说是一件重要事情，就像 ``--help``
    和 ``--version`` 它们俩。它们都是期望参数形式，但在命令行中
    不管谁先进入都会获胜并退出程序，遵循了先进先出的算法。

重复的参数形式:
    如果一个可选项或一个参数在命令行中划分到多个地方的话，
    由于出现了重复使用现象 -- 例如，
     ``--exclude foo --include baz --exclude bar`` 
     这种情况 -- 那么回调会根据第一个可选项位来启动。
    在这种情况下，回调会启动 ``exclude`` 并代入这两个相同
    的可选项值 (``foo`` 和 ``bar``)，然后回调再只启动
     ``include`` 所含的 ``baz`` 值。

    注意，如果一个参数形式不允许多版本的话， Click 依然接受
    第一参数位，但会忽略其中的每个值，只接收最后一个值。对于
    这个来说，原因是为了允许兼容终端别名默认设置。

缺少参数形式:
    如果一个参数形式没有写在命令行中的话，回调依然会启动。
    这与 optparse 中的工作原理不同，因为 optparse 规定
    为定义值是不可以启动回调的。缺少参数形式启动它们的回调
    是结束时，其中让来自一个参数形式的默认值提供给回调变成可能。

绝大多数时候你不需要担心这 3 种情况中的任何一个，
但对于一些高级环境来说，了解这是如何工作的是重要的事情。

.. _forwarding-unknown-options:

继续指向未知可选项
--------------------------

在有些环境中，为下一步手动处理接收所有未知的可选项是一件有趣的事。
 Click 可以在通用中实现这种特性，从 Click 4.0 开始，但有一些
限制，这属于问题的实质原因。要支持这种特性，需要一个语法分析器旗语，
名叫 ``ignore_unknown_options`` 来实现。这个旗语会指导语法分析器
收集所有未知可选项，然后放到剩余参数中，代替触发一个语法分析错误。

通用中，激活这种特性有 2 种不同的方法:

1.  在自定义 :class:`Command` 类的子类里，通过改变
     :attr:`~BaseCommand.ignore_unknown_options` 属性来激活。
2.  在语境类上通过改变相同名字的属性
     (:attr:`Context.ignore_unknown_options`) 来激活。
    最好是在命令上通过改变 ``context_settings`` 字典键值来激活。

对于大多数情况来说，最简单的解决方案就是第二种了。
一旦行为改变了，有些事需要获得那些剩余的未知可选项
 (在这里可以看成参数)。对于这个来说你有 2 种选择:

1.  你可以使用 :func:`pass_context` 函数来得到代入的语境。
    当然如果增加了 :attr:`~Context.ignore_unknown_options` 
    属性后你也设置了 :attr:`~Context.allow_extra_args` 
    这个属性时才有效，否则命令会带着一个错误而终止，错误会告诉你
    有剩余参数。如果使用这种解决方案的话，额外的参数会收集在 
    :attr:`Context.args` 属性里。
2.  你可以把一个 :func:`argument` 函数放在 ``nargs`` 之后设置成 `-1` ，
    这样会吃掉所有剩余的参数。在这种情况中，建议把 `type` 设置成
     :data:`UNPROCESSED` 数据类型，这样可以避免在这些参数上处理成
    任何一种字符串，否则都会自动地被处理成 unicode 字符串，这常常不是你所期望见到的。

最后我们来一个例子:

.. click:未知可选项处理示例::

    import sys
    from subprocess import call

    @click.command(context_settings=dict(
        ignore_unknown_options=True,
    ))
    @click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode')
    @click.argument('timeit_args', nargs=-1, type=click.UNPROCESSED)
    def cli(verbose, timeit_args):
        """A fake wrapper around Python's timeit."""
        cmdline = ['echo', 'python', '-mtimeit'] + list(timeit_args)
        if verbose:
            click.echo('Invoking: %s' % ' '.join(cmdline))
        call(cmdline)

运行时的情况:

.. click:run::

    invoke(cli, prog_name='cli', args=['--help'])
    println()
    invoke(cli, prog_name='cli', args=['-n', '100', 'a = 1; b = 2; a * b'])
    println()
    invoke(cli, prog_name='cli', args=['-v', 'a = 1; b = 2; a * b'])

如你所见，冗余旗语是由 Click 来处理，在命令行中输入其它任何没定义的可选项内容
都会进入 `timeit_args` 变量中，对于下一步处理来说，会允许触发一个子进程。
这个例子中有几点重要的事情要知道，那就是这种忽略未处理的旗语是如何发生的:

*   通用中，未知的长可选项都被忽略，并且根本不被处理。
    所以例如如果代入了 ``--foo=bar`` 或 ``--foo bar`` 的话，
    它们都会像示例中一样结束。注意因为语法分析器不知道一个可选项
    是否会接收一个参数，那么 ``bar`` 部分可能被处理成一个参数。
*   未知短可选项可能是部分被处理，然后如果需要的话会重新组装。
    例如上面的示例中，有一个 ``-v`` 可选项，它是开启冗余模式。
    如果 ``-va`` 命令被忽略的话，那么 ``-v`` 部分会被 Click 
    处理 (因为知道) 然后剩下部分变成 ``-a`` 会收集到剩余参数中
    提供给下一步做处理。
*   根据你所做的计划，你也许通过禁用离散参数
    (:attr:`~Context.allow_interspersed_args`) 
    获得成功，该属性会指导语法分析器不允许参数和可选项混用。
    根据你的环境，这种方法也许会提升你的效果。

通用中，尽管可选项和来自你自己的命令参数，以及来自另一个应用程序命令的参数，
这种组合处理都是不被鼓励的，如果你能避免的话，还是别给自己找麻烦吧。
更好的设计思路是，把参数形式放到一个子命令下，让子命令继续触发另一个应用程序。
这要比你自己去处理一些参数要好许多！


全局语境访问
---------------------

.. versionadded:: 5.0

从 Click 5.0 开始，在相同的线程里，在任何地方访问当前语境变的可能了。
通过使用 :func:`get_current_context` 函数来实现，它会返回当前语境。
对于访问语境绑定的对象来说是非常重要的，同样访问存储在语境对象上的一些旗语
也是同等重要，因为可以自定义运行时的行为。例如， :func:`echo` 函数就
实现了这个特性，它参考了 `color` 旗语的默认值。

示例用法::

    def get_current_command_name():
        return click.get_current_context().info_name

有责任注意到这个特性只在当前线程里有效。
如果你释放了另外一些线程，那么那些线程是没有能力指向当前语境的。
如果你想要给其它线程指向这个语境的话，你需要在线程中把语境用作
一个语境管理器才有效::

    def spawn_thread(ctx, func):
        def wrapper():
            with ctx:
                func()
        t = threading.Thread(target=wrapper)
        t.start()
        return t

此时释放线程函数可以访问语境了，就像主线程一样。
不管如何做到的，如果你使用这种特性给线程的话，
你需要非常谨慎，因为语境的大量内容都不在是线程安全模式！
你只做读取语境就好，而不要对语境对象执行任何修改操作。


侦测一个参数形式的源头
-----------------------------------

在有些环境里，理解一个可选项或一个参数形式是否是来自命令行、
环境变量、默认值、还是默认映射。这有助于弄清楚问题根源。
可以使用 :meth:`Context.get_parameter_source` 方法
来找到这个源头。

.. click:侦测参数形式值的源头示例::

    @click.command()
    @click.argument('port', nargs=1, default=8080, envvar="PORT")
    @click.pass_context
    def cli(ctx, port):
        source = ctx.get_parameter_source("port")
        click.echo("Port came from {}".format(source))

.. click:run::

    invoke(cli, prog_name='cli', args=['8080'])
    println()
    invoke(cli, prog_name='cli', args=[], env={"PORT": "8080"})
    println()
    invoke(cli, prog_name='cli', args=[])
    println()
