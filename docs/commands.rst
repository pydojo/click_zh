多命令与群组命令
===================

.. currentmodule:: click

Click 的最重要特性就是任意嵌入式单行命令工具概念。
这是通过 :class:`Command` 类和 :class:`Group` 
类实现的 (实际上是 :class:`MultiCommand` 类)。

回调回应
-------------------

*对于一个常规命令来说，回调就是不管什么时候运行命令，回调都会执行。*
如果脚本只有一个命令的话，脚本会一直工作 (除非用一个参数回调来阻止
脚本运行。就像某个人代入 ``--help`` 参数给脚本时的样子)。

对于群组和多命令来说，情形就不一样了。在这种情况下，
不管什么时候一个子命令触发时回调才工作 (直到这种行为改变)。
实际中有什么意义？那就是当一个内部命令运行时会运行一个外部命令:

.. click:多命令回调示例::

    @click.group()
    @click.option('--debug/--no-debug', default=False)
    def cli(debug):
        click.echo('Debug mode is %s' % ('on' if debug else 'off'))

    @cli.command()  # @cli, not @click!
    def sync():
        click.echo('Syncing')

运行时看起来会像这样:

.. click:run::

    invoke(cli, prog_name='tool.py')
    println()
    invoke(cli, prog_name='tool.py', args=['--debug', 'sync'])

代入参数
------------------

Click 严谨地把多命令和多个子命令之间的多参数进行分解。
这是什么意思呢？就是一个具体命令的许多选项和参数都要描述
在命令名 *身后* ，而不能写在任何其它命令名 *之前* 。

这种行为已经明显地用在了预定义完的 ``--help`` 选项身上。
假设我们有一个程序名叫 ``tool.py`` ，其中含有一个子命令 ``sub``:

- ``tool.py --help`` 会返回帮助页面 (列出所有的子命令)。

- ``tool.py sub --help`` 会返回 ``sub`` 子命令的帮助页面。

- 但 ``tool.py --help sub`` 会把 ``--help`` 处理成一个主程序
  的一个参数。 Click 接着为 ``--help`` 触发回调，那么输出帮助信息后
  会在 Click 处理子命令之前终止程序。

嵌入后的处理与语境
----------------------------

从前面的例子你可以明白，基础的群组命令接收了一个 debug 参数，
该参数作为自身的回调，但参数不会给 sync 命令。因为 sync 
只接收自己所拥有的参数。

这种处理允许许多工具彼此是完全独立的，但一个命令如何对一个嵌入式命令说话呢？
答案就是 :class:`Context` 语境类来实现。

每次触发一个命令时，一个新的语境就会建立完毕，然后与父语境相连。
正常来说，你看不到这些语境，但这些语境都是存在的，就像风一样。
语境都是一起与值自动传递给参数回调的。许多命令也可以请求其语境，
通过使用 :func:`pass_context` 装饰器来装饰自己后实现。
在这种情况下，语境是作为第一个参数代入其中。

语境也能把一个具体的对象带给一个程序，这个具体的对象就是为程序而使用的。
这是什么意思呢？就是你可以建立一个像下面一样的脚本:

.. click:语境把对象给程序示例::

    @click.group()
    @click.option('--debug/--no-debug', default=False)
    @click.pass_context
    def cli(ctx, debug):
        # ensure that ctx.obj exists and is a dict (in case `cli()` is called
        # by means other than the `if` block below
        ctx.ensure_object(dict)

        ctx.obj['DEBUG'] = debug

    @cli.command()
    @click.pass_context
    def sync(ctx):
        click.echo('Debug is %s' % (ctx.obj['DEBUG'] and 'on' or 'off'))

    if __name__ == '__main__':
        cli(obj={})

如果提供了对象的话，每个语境会把对象直接传给其子语境，
但在任何一层上，一个语境的对象都是可以被覆写的。
要得到一个父语境，要使用 ``context.parent`` 来实现。

另外在这种情况里，不要把一个对象向下传递，
修改全局状态来终止应用程序。例如，你只要
抛出一个全局 ``DEBUG`` 变量后就可以实现。

对命令进行装饰
-------------------

前面的例子中你也看到了，一个装饰器可以改变一个命令是如何触发的。
那么实际上内幕是什么呢？就是许多回调一直通过
 :meth:`Context.invoke` 方法来触发，这个
方法会自动地正确触发一个命令 (不管有没有语境）。

这是非常有用的，因为当你想要自己写一些装饰器时，
例如把一种共性模式配置给一个对象来表示状态后，
把对象存储在语境中，接着使用一个自定义装饰器
来找到最近出现的此类对象，然后把对象作为第一个参数代入其中。

例如， :func:`pass_obj` 装饰器函数可以实现成如下样子:

.. click:自定义装饰器示例::

    from functools import update_wrapper

    def pass_obj(f):
        @click.pass_context
        def new_func(ctx, *args, **kwargs):
            return ctx.invoke(f, ctx.obj, *args, **kwargs)
        return update_wrapper(new_func, f)

其中使用了 :meth:`Context.invoke` 方法的命令会自动用正确的方法来触发函数，
所以函数会既可以用 ``f(ctx, obj)`` 来调用，也可以用 ``f(obj)`` 来调用，
依据就是函数自身是否被 :func:`pass_context` 函数装饰了。

这是一种非常给力的概念，这个概念可以用来建立非常多层化的嵌入式应用程序，
阅读 :ref:`complex-guide` 参考文档了解更多信息。


无命令的群组回应
--------------------------------

默认情况下，一个群组或多命令是不会被触发的，除非代入了一个子命令。
事实上，不会默认提供自动代入 ``--help`` 给一个命令。
这种行为可以通过把 ``invoke_without_command=True`` 代入给一个群组后来改变。
在默认帮助情况下，回调是一直被触发，但不会显示帮助页面信息。
语境对象也包括了一个信息，就是是否会把回应给一个子命令。

示例:

.. click:一直触发回调群组命令::

    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        if ctx.invoked_subcommand is None:
            click.echo('I was invoked without subcommand')
        else:
            click.echo('I am about to invoke %s' % ctx.invoked_subcommand)

    @cli.command()
    def sync():
        click.echo('The subcommand')

实际中这个示例是如何运行的:

.. click:run::

    invoke(cli, prog_name='tool', args=[])
    invoke(cli, prog_name='tool', args=['sync'])

.. _custom-multi-commands:

自定义多命令
---------------------

另外一种 :func:`click.group` 函数的用法是，你也可以建立你自己的多命令。
这也是有用的，当你想要从插件中按需加载多命令时，就可以获得这种技术支持。

一个自定义多命令只需要实现一个列表和加载方法即可:

.. click:自定义多命令示例::

    import click
    import os

    plugin_folder = os.path.join(os.path.dirname(__file__), 'commands')

    class MyCLI(click.MultiCommand):

        def list_commands(self, ctx):
            rv = []
            for filename in os.listdir(plugin_folder):
                if filename.endswith('.py'):
                    rv.append(filename[:-3])
            rv.sort()
            return rv

        def get_command(self, ctx, name):
            ns = {}
            fn = os.path.join(plugin_folder, name + '.py')
            with open(fn) as f:
                code = compile(f.read(), fn, 'exec')
                eval(code, ns, ns)
            return ns['cli']

    cli = MyCLI(help='This tool\'s subcommands are loaded from a '
                'plugin folder dynamically.')

    if __name__ == '__main__':
        cli()

这种自定义类也可以与装饰器一起使用:

.. click:自定义类与装饰器组合用法示例::

    @click.command(cls=MyCLI, help="本命令工具的子命令都来自于插件文件夹中的 Click 程序")
    def cli():
        pass

合并多命令
----------------------

另一种实现自定义多命令的方式是，把多命令合并成一个脚本，这也很有趣。
同时这种方法通用中不是推荐使用的，因为要把一个嵌入到另一个的下面，
对某些更棒的终端体验来说，有些情况下合并过程实现的方法是有用的。

对于这种合并系统来说，默认是通过 :class:`CommandCollection` 类实现的。
它接受一个其它多命令列表后，让这些命令在相同的层次上变得可用。

示例用法:

.. click:合并多命令示例::

    import click

    @click.group()
    def cli1():
        pass

    @cli1.command()
    def cmd1():
        """Command on cli1"""

    @click.group()
    def cli2():
        pass

    @cli2.command()
    def cmd2():
        """Command on cli2"""

    cli = click.CommandCollection(sources=[cli1, cli2])

    if __name__ == '__main__':
        cli()

运行时看起来如下:

.. click:run::

    invoke(cli, prog_name='cli', args=['--help'])

在这种情况里一个主命令有许多来源，第一个来源会起主导作用。


.. _multi-command-chaining:

多命令链条
----------------------

.. versionadded:: 3.0

有时在一个命令上使用多个命令是有用的。
如果你安装了 setuptools 库的话，在熟悉
 ``setup.py sdist bdist_wheel upload``
 这样的命令链条用法，需要在 ``upload`` 之前
触发 ``bdist_wheel`` 命令，在 ``bdist_wheel`` 之前
先触发 ``sdist`` 命令。自从 Click 3.0 版本开始，
这样的实现变得非常简单了。你所要做的就是把 ``chain=True``
 参数代入到你的群组命令装饰器的构造器中:

.. click:命令链条示例::

    @click.group(chain=True)
    def cli():
        pass


    @cli.command('sdist')
    def sdist():
        click.echo('sdist called')


    @cli.command('bdist_wheel')
    def bdist_wheel():
        click.echo('bdist_wheel called')

运行起来会是如下样式:

.. click:run::

    invoke(cli, prog_name='setup.py', args=['sdist', 'bdist_wheel'])

当使用多命令链条方式时，你只有一个命令 (最后一个命令) 
在一个参数上使用 ``nargs=-1`` 参数。在链条命令下面不能
嵌入多个命令。除了这点外没有其它限制，它们依然可以正常接收
许多选项和参数。

注意另一点：语境 :attr:`Context.invoked_subcommand` 属性
对于多子命令来说是没什么用的，因为如果触发多个命令的话，它会给出
一个 ``'*'`` 作为值。这样做是需要的，因为多个子命令出现时的处理
是一个接着一个来处理的，所以真正要处理的这些子命令在回调时都是不可用的。

.. note::

    目前不支持链条命令的嵌入处理。也许在以后的 Click 版本中增加此项。


多命令管道技术
-----------------------

.. versionadded:: 3.0

多命令链条的一种非常共性的用例就是有一个命令来处理前面命令的结果。
有许多方法实现，最明显的方法就是把一个值存储在语境对象上，之后
一个函数接着一个函数来处理这个语境对象。这是通过用 :func:`pass_context`
 函数来装饰一个函数生效的，其中提供的语境对象作为一个子命令用来存储自身数据用。

另一种方法是组建许多条管道，通过返回处理中的许多函数来实现。
把这个想成：当触发一个子命令时，它处理所有自身参数，然后建立
一个如何做处理的计划。在这点上子命令稍后返回一个处理函数和其结果。

返回的函数要去哪里呢？
锁链多命令可以使用 :meth:`MultiCommand.resultcallback` 方法
来注册一个回调，该方法走遍这些函数后触发它们。见一个函数触发一个。

要实现这种管道技术要多考虑一些事情，看下面示例:

.. click:多命令管道技术示例::

    @click.group(chain=True, invoke_without_command=True)
    @click.option('-i', '--input', type=click.File('r'))
    def cli(input):
        pass

    @cli.resultcallback()
    def process_pipeline(processors, input):
        iterator = (x.rstrip('\r\n') for x in input)
        for processor in processors:
            iterator = processor(iterator)
        for item in iterator:
            click.echo(item)

    @cli.command('uppercase')
    def make_uppercase():
        def processor(iterator):
            for line in iterator:
                yield line.upper()
        return processor

    @cli.command('lowercase')
    def make_lowercase():
        def processor(iterator):
            for line in iterator:
                yield line.lower()
        return processor

    @cli.command('strip')
    def make_strip():
        def processor(iterator):
            for line in iterator:
                yield line.strip()
        return processor

这个例子有点内容，所以我们来逐步看一下。

1.  第一件事要建立一个支持锁链用法的 :func:`group` 群组命令。
    另外我们也要指导 Click 去触发即使没有定义子命令也可以执行。
    如果不这样做的话，后面触发一个空管道就会产生帮助页面，而不是
    运行回调结果了。
2.  第二件事是把一个回调结果注册在我们的群组命令上。
    这个回调会用一个参数来触发，就是所有子命令返回值
    形成的一个列表，之后与群组命令自身的关键字参数是一样的。
    这就意味着，我们可以在那里容易访问到输入文件，
    却不使用语境对象了。
3.  在这种回调结果中，我们建立一个输入文件中所有行的迭代器，
    然后把这个迭代器传递给所有返回的回调，这些回调都是来自
    所有子命令，最后我们把所有行输出到标准输出接口上。

这点之后，我们想注册多少个子命令都可以，并且每个子命令返回一个处理器函数
来修改这些行的流数据。

注意一点重要的事情，那就是 Click 会在每个运行完的回调之后来关闭语境。
这就意味着实际中的文件类型不能在 `processor` 函数中访问，因为这些
文件已经被关闭了。这种限制不会取消，因为会让资源处理变复杂。
所以建议不要使用文件类型和通过 :func:`open_file` 函数手动打开文件。

对于多命令管道技术更多层化的示例，可以查看经过改善的图片处理示例，
位置在 Click 仓库中的 `imagepipe multi command chaining demo
<https://github.com/pallets/click/tree/master/examples/imagepipe>`__ 
图片管道示例实现了基于图片编辑工具的一条管道技术，
这个图片编辑工具含有良好的内部结构支持多管道技术。


覆写参数默认值
-------------------

默认情况下，一个参数的默认值是从 ``default`` 旗语获得的，
当然是要定义了这个旗语，但这不是唯一可以加载参数值的地方。
另一个位置是语境上的 :attr:`Context.default_map` 属性 (一个字典) 。
该语境属性允许许多默认值从一个配置文件里加载，实现覆写常规的默认值。

如果你采用插件命令模式开发的话，这是有用的技术。
因为许多命令来自另一个包，但对其默认设置的值并不满意。

这个默认映射属性能够任意地嵌入给每个子命令，
然后当触发脚本时提供其中的参数值。
另一种方法是也可以在任何点上通过命令来覆写。
例如，在一个命令的顶层（执行区域）可以从一个配置文件来加载默认值。

示例用法:

.. click:覆写参数默认值示例::

    import click

    @click.group()
    def cli():
        pass

    @cli.command()
    @click.option('--port', default=8000)
    def runserver(port):
        click.echo('Serving on http://127.0.0.1:%d/' % port)

    if __name__ == '__main__':
        cli(default_map={
            'runserver': {
                'port': 5000
            }
        })

表现是:

.. click:run::

    invoke(cli, prog_name='cli', args=['runserver'], default_map={
        'runserver': {
            'port': 5000
        }
    })

语境默认值
----------------

.. versionadded:: 2.0

从 Click 2.0 版本开始，你就可以覆写语境的默认值，
而不是只在调用脚本时覆写，还可以在装饰器里声明一个命令。
例如，根据给出的前面示例，其中定义了一个自定义
 ``default_map`` 属性，目前这也可以在装饰器中实现了。

与前面示例效果一样的示例:

.. click:语境默认值示例::

    import click

    CONTEXT_SETTINGS = dict(
        default_map={'runserver': {'port': 5000}}
    )

    @click.group(context_settings=CONTEXT_SETTINGS)
    def cli():
        pass

    @cli.command()
    @click.option('--port', default=8000)
    def runserver(port):
        click.echo('Serving on http://127.0.0.1:%d/' % port)

    if __name__ == '__main__':
        cli()

表现是:

.. click:run::

    invoke(cli, prog_name='cli', args=['runserver'])


命令返回值
---------------------

.. versionadded:: 3.0

在 Click 3.0 版本中新特性之一是全面支持来自命令回调的返回值。
这个特性开启前面难于实现的整个特性范围。

实质上，任何一个命令的回调现在可以返回一个值。这个返回值吹给某些接收器。
对于这种特性的一种用例已经展示在 :ref:`multi-command-chaining` 示例中，
其中已做过的示范就是锁链多命令可以有回调来处理所有返回值。

在 Click 中与命令返回值一起工作的时候，你需要知道:

-   一个命令回调的返回值通用中是来自 :meth:`BaseCommand.invoke` 方法。
    这条规则的例外就是要与 :class:`Group` 类一起使用:

    *   在一个群组命令里，返回值通用中是触发的子命令返回值。
        对这条规则唯一例外就是，如果无参数触发和开启了
        `invoke_without_command` 参数的话，
        返回值会是群组命令回调的返回值。
    *   如果一个群组命令设置成链条的话，那么返回值是所有子命令
        结果形成的一个列表。
    *   群组命令的返回值可以通过 :attr:`MultiCommand.result_callback` 
        属性来处理。这要在链条模式中与所有返回值形成的列表一起被触发，
        或者在非链条命令中的单个返回值。

-   返回值是通过 :meth:`Context.invoke` 方法和
    :meth:`Context.forward` 方法产生的。在一些
    环境中是有用的，那就是你想要内部调用给另一个命令。

-   Click 对于返回值没有任何硬性需求，并且自身也不会使用这些返回值。
    这就可以允许返回值被自定义装饰器来使用，或者被工作流来使用
     (就像在多命令链条示例中一样)。

-   当一个 Click 脚本被触发成命令行应用程序时 (即通过
    :meth:`BaseCommand.main` 方法实现的) ，返回值时被忽略的，
    除非在产生返回值情况里禁用 `standalone_mode` 。
