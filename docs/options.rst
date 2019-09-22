.. _options:

可选项
=======

.. currentmodule:: click

把可选项增加到命令中可以通过 :func:`option` 函数装饰器来实现。
由于可选项变化太多，会有成吨的参数要配置其行为。
在 Click 中的可选项与位置参数是完全不同的概念，
可以阅读一下 :ref:`positional arguments <arguments>` 参考文档。

命名你的可选项
-----------------

命名规则可以阅读 :ref:`parameter_names` 参考文档。
长话短说，你可以把带有双减号名字的一种参数形式**隐含地**
表达成一种可选项形式:

.. click:可选项示例1::

    @click.command()
    @click.option('-s', '--string-to-echo')
    def echo(string_to_echo):
        click.echo(string_to_echo)

或者把无减号的参数形式**隐含地**表达成一种可选项形式:

.. click:可选项示例2::

    @click.command()
    @click.option('-s', '--string-to-echo', 'string')
    def echo(string):
        click.echo(string)

可选项基础值
-------------------

最基本的可选项是一种值选择。这些可选项把一个值接收成一个参数。
如果不提供类型的话，默认类型就是值的类型。
如果不提供默认值的话，值类型假设成 :data:`STRING` 字符串数据类型。
除非明确地描述一个名字，参数的名字是第一个长型可选项；
否则就使用第一个短型可选项。默认情况下，可选项都是不需要的，
不管如何做到的，要把一个可选项变成必须项，
直接把 `required=True` 参数代入到装饰器中即可。

.. click:可选项默认值示例::

    @click.command()
    @click.option('--n', default=1)
    def dots(n):
        click.echo('.' * n)

.. click:必选可选项示例::

    # How to make an option required
    @click.command()
    @click.option('--n', required=True, type=int)
    def dots(n):
        click.echo('.' * n)

.. click:处理Python关键字作为可选项时的示例::

    # How to use a Python reserved word such as `from` as a parameter
    @click.command()
    @click.option('--from', '-f', 'from_')
    @click.option('--to', '-t')
    def reserved_param_name(from_, to):
        click.echo('from %s to %s' % (from_, to))

运行时的状况:

.. click:run::

   invoke(dots, args=['--n=2'])

在这种情况下，可选项是类型 :data:`INT` 数据类型，因为默认值是一个整数。

当显示命令帮助信息时要显示默认值，使用 ``show_default=True`` 参数。

.. click:帮助页面中显示默认值信息示例::

    @click.command()
    @click.option('--n', default=1, show_default=True)
    def dots(n):
        click.echo('.' * n)

.. click:run::

   invoke(dots, args=['--help'])

可选项多参数值
-------------------

有时候你有一些可选项要获得多个参数值。
对于这些可选项来说，只提供一种固定数量的参数值支持。
这是可以通过 ``nargs`` 参数来配置的。这些参数值都会存储成一个元组。

.. click:可选项多参数值示例::

    @click.command()
    @click.option('--pos', nargs=2, type=float)
    def findme(pos):
        click.echo('%s / %s' % pos)

运行时的状况:

.. click:run::

    invoke(findme, args=['--pos', '2.0', '3.0'])

.. _tuple-type:

元组用作多值可选项
-----------------------------

.. versionadded:: 4.0

如你所见，通过使用 `nargs` 来设置可选项值的数量，
其结果会是相同数据类型的元组。这也许不是你所想要的结果，
共性的做法是，针对元组中不同的索引位指定不同的数据类型。
对于这个目标，你可以直接在元组中描述数据类型即可:

.. click:元组作为多值可选项示例::

    @click.command()
    @click.option('--item', type=(str, int))
    def putitem(item):
        click.echo('name=%s id=%d' % item)

运行时的情况:

.. click:run::

    invoke(putitem, args=['--item', 'peter', '1338'])

这样使用元组时， `nargs` 参数会自动设置成元组的长度后，
 :class:`click.Tuple` 类型也会自动被使用。
上面的示例等价于下面的示例:

.. click:元组作为多值可选项的等价示例::

    @click.command()
    @click.option('--item', nargs=2, type=click.Tuple([str, int]))
    def putitem(item):
        click.echo(f'name={item[0]} id={item[-1]}')

多次使用可选项
----------------

类似 ``nargs`` 作用，但是一种想要给一个参数提供多次使用同一个可选项时的方法。
并且所有的值都会记录下来，而不是只记录最后一次的值。
例如， ``git commit -m foo -m bar`` 这样的命令会记录两行注释消息:
 ``foo`` 和 ``bar`` 。要想这样的话，可以用 ``multiple`` 旗语来实现:

示例:

.. click:多次使用可选项示例::

    @click.command()
    @click.option('--message', '-m', multiple=True)
    def commit(message):
        click.echo('\n'.join(message))

运行时的情况:

.. click:run::

    invoke(commit, args=['-m', 'foo', '-m', 'bar'])

冗余可选项
-------------

在非常少见的情况里，重复书写可选项名字的使用是一件有趣的事，
因为会按照整数来数算重复名字的次数。这可以用在冗余旗语中，例如:

.. click:冗余可选项示例::

    @click.command()
    @click.option('-v', '--verbose', count=True)
    def log(verbose):
        click.echo('Verbosity: %s' % verbose)

运行时的情况:

.. click:run::

    invoke(log, args=['-vvv'])

布尔旗语
-------------

布尔旗语都是可选项，这些可选项可以是开启或禁用功能。
通过定义两个旗语在一行用一个斜杠  (``/``) 来分隔开来实现开启或禁用可选项。
 (如果一个斜杠用在一个选项字符串中的话， Click 自动会知道
这是一种布尔旗语用法，并且会隐含地代入 ``is_flag=True`` )
 Click 一直想要你提供一种开启和禁用旗语，这样你可以稍后改变默认值。

示例:

.. click:布尔旗语示例::

    import sys

    @click.command()
    @click.option('--shout/--no-shout', default=False)
    def info(shout):
        rv = sys.platform
        if shout:
            rv = rv.upper() + '!!!!111'
        click.echo(rv)

运行时的情况:

.. click:run::

    invoke(info, args=['--shout'])
    invoke(info, args=['--no-shout'])

如果你不想要这种切换式用法，你可以只定义一个后手动告诉
 Click 这是一个旗语用法:

.. click:无切换布尔旗语示例::

    import sys

    @click.command()
    @click.option('--shout', is_flag=True)
    def info(shout):
        rv = sys.platform
        if shout:
            rv = rv.upper() + '!!!!111'
        click.echo(rv)

运行时的情况:

.. click:run::

    invoke(info, args=['--shout'])

注意如果在你的选项中已经含有一个斜杠的话 (例如，
如果你使用的是 Windows 风格的参数，其中斜杠 ``/`` 
是前缀字符的话)，你可以另外通过分号 ``;`` 来分隔参数:

.. click:Windows风格的旗语示例::

    @click.command()
    @click.option('/debug;/no-debug')
    def log(debug):
        click.echo('debug=%s' % debug)

    if __name__ == '__main__':
        log()

.. versionchanged:: 6.0

如果你想只给第二个选项定义一个别名的话，
你需要使用一个空格来消除格式化字符串时产生的歧义:

示例:

.. click:第二个选项别名示例::

    import sys

    @click.command()
    @click.option('--shout/--no-shout', ' /-S', default=False)
    def info(shout):
        rv = sys.platform
        if shout:
            rv = rv.upper() + '!!!!111'
        click.echo(rv)

.. click:run::

    invoke(info, args=['--no-shout', '-S'])

特性切换
----------------

另外对布尔旗语来说，也有特性切换功能。
通过把两个可选项设置给同一个参数名来实现，
然后给可选项定义一个旗语值。注意要给
 ``flag_value`` 参数设置一个默认值，
 Click 会隐含设置成 ``is_flag=True``

要设置这个默认值，就是使用 ``default=True`` ，
这样当布尔旗语是 True 时代表的参数值就是旗语值，
反之，就是另一个可选项的旗语代表值。

.. click:特性切换示例::

    import sys

    @click.command()
    @click.option('--upper', 'transformation', flag_value='upper',
                  default=True)
    @click.option('--lower', 'transformation', flag_value='lower')
    def info(transformation):
        click.echo(getattr(sys.platform, transformation)())

运行时的情况:

.. click:run::

    invoke(info, args=['--upper'])
    invoke(info, args=['--lower'])
    invoke(info)

.. _choice-opts:

选择可选项值
--------------

有时候你想要一个参数是一种选择值列表形式。
这种情况下你可以使用 :class:`Choice` 类，
它可以实例化一个合法值列表。

示例:

.. click:选择可选项值示例::

    @click.command()
    @click.option('--hash-type', type=click.Choice(['md5', 'sha1']))
    def digest(hash_type):
        click.echo(hash_type)

运行时的情况:

.. click:run::

    invoke(digest, args=['--hash-type=md5'])
    println()
    invoke(digest, args=['--hash-type=foo'])
    println()
    invoke(digest, args=['--help'])

.. note::

    你只可以用列表或元组作为可选项值。
    其它的可迭代对象 (例如生成器对象) 
    可能导致意外的结果产生。

.. _option-prompting:

提示
---------

在一些情况中，你想要参数可以在命令行提供一个提示输入信息，
因为如果用户没有直接在命令行中提供值的话，就能实现提示用户输入。
使用 Click 来实现就是定义一个 ``prompt`` 参数。

示例:

.. click:开启提示功能示例::

    @click.command()
    @click.option('--name', prompt=True)
    def hello(name):
        click.echo('Hello %s!' % name)

运行时的情况:

.. click:run::

    invoke(hello, args=['--name=John'])
    invoke(hello, input=['John'])

如果你不喜欢默认提示的字符串，你可以设置一个自己的提示信息:

.. click:自定义提示信息示例::

    @click.command()
    @click.option('--name', prompt='Your name please')
    def hello(name):
        click.echo('Hello %s!' % name)

运行时的情况:

.. click:run::

    invoke(hello, input=['John'])

密码提示
----------------

Click 也支持确认密码输入时的隐藏显示功能。
对密码输入时来说这是非常有用的:

.. click:密码提示隐藏示例1::

    @click.command()
    @click.option('--password', prompt=True, hide_input=True,
                  confirmation_prompt=True)
    def encrypt(password):
        click.echo('Encrypting password to %s' % password.encode('utf16'))

运行时的情况:

.. click:run::

    invoke(encrypt, input=['secret', 'secret'])

由于这种参数组合非常有共性，所以可以用
 :func:`password_option` 函数装饰器来代替:

.. click:密码提示隐藏示例2::

    @click.command()
    @click.password_option("--password")
    def encrypt(password):
        click.echo('Encrypting password to %s' % password.encode('utf32'))

针对提示的动态默认值
----------------------------

对于语境来说 ``auto_envvar_prefix`` 和 ``default_map`` 可选项
是允许程序从环境变量或一个配置文件读取可选项值的。不管如何做到的，
这种覆写提示值的机制，不会在互动时让用户得到可选项来改变可选项值。

如果你想要让用户配置默认值值的话，如果在命令行中没有描述可选项仍然作出提示，
你可以提供一个可调用对象作为默认值来实现。例如，要从环境变量中得到一个默认值:

.. click:提示动态默认值示例::

    @click.command()
    @click.option('--username', prompt=True,
                  default=lambda: os.environ.get('USER', ''))
    def hello(username):
        print("Hello,", username)

要想在帮助页面中描述默认值是什么，在 ``show_default`` 参数中设置。

.. click:example::

    @click.command()
    @click.option('--username', prompt=True,
                  default=lambda: os.environ.get('USER', ''),
                  show_default='current user')
    def hello(username):
        print("Hello,", username)

.. click:run::

   invoke(hello, args=['--help'])

回调与期望可选项
---------------------------

有时候，你想要一个参数完全改变执行流程。
例如，当你有一个输出版本信息的 ``--version``
 参数，输出完信息后退出应用程序。

注意: 实际上一个 ``--version`` 参数的部署是一种复用情况，
在 Click 中可以用 :func:`click.version_option` 函数装饰器来实现。
这里介绍的示例代码是解释如何实现这种旗语。

在这种情况中，你需要明白 2 个概念: 期望可选项和回调。
一个期望可选项是一种参数形式，该参数要在其它参数之前进行处理。
而一个回调是要在期望参数处理完后执行。期望的需要意味着前面所需
的参数不会产生一项错误消息。例如，如果 ``--version`` 不属于
期望可选项的话，而所需的参数 ``--foo`` 定义在它之前的话，
你就需要为 ``--version`` 来描述它才能生效。对于更多这方面的信息
阅读 :ref:`callback-evaluation-order` 参考文档。

一个回调就是一个函数，这个函数带着 2 个参数被触发:
当前语境参数 :class:`Context` 类和值。语境参数
提供一些有用的特性，例如退出程序和给予访问其它已经
处理完的参数。

对于一个 ``--version`` 旗语的示例如下:

.. click:回调和期望可选项示例::

    def print_version(ctx, param, value):
        if not value or ctx.resilient_parsing:
            return
        click.echo('Version 1.0')
        ctx.exit()

    @click.command()
    @click.option('--version', is_flag=True, callback=print_version,
                  expose_value=False, is_eager=True)
    def hello():
        click.echo('Hello World!')

其中 `expose_value` 参数防止没有意义的 ``version`` 参数
被带入到回调函数中。如果不描述曝光值参数的话，或者值为 True时，
都会导致把一个布尔值代入到 `hello` 脚本函数里。
如果 Click 想要对命令行进行语法分析不带任何一种破坏行为的话，
破坏行为就是一种结构表现，它会改变执行流程，那么回调函数中的
 `resilient_parsing` 旗语就被作用到语境上了。在这里的情况，
由于我们退出了程序，并没有做什么其它事情。

运行起来的情况是:

.. click:run::

    invoke(hello)
    invoke(hello, args=['--version'])

.. admonition:: 回调信号变更

    在 Click 2.0 版本中，回调信号有了变化。对于更多这方面的信息
    阅读 :ref:`upgrade-to-2.0` 参考文档。

确认参数形式
--------------

对于那些有风险的操作来说，询问一名用户来确认一下是非常有用的一件事。
这可以通过增加一个布尔 ``--yes`` 旗语来实现，并且如果用户没有提供
确认输入的话，就会让一个回调函数执行失败，从而确保避免风险操作:

.. click:确认参数形式示例1::

    def abort_if_false(ctx, param, value):
        if not value:
            ctx.abort()

    @click.command()
    @click.option('--yes', is_flag=True, callback=abort_if_false,
                  expose_value=False,
                  prompt='Are you sure you want to drop the db?')
    def dropdb():
        click.echo('Dropped all tables!')

运行时的情况:

.. click:run::

    invoke(dropdb, input=['n'])
    invoke(dropdb, args=['--yes'])

由于这种组合参数形式非常具有共性，
也可以用 :func:`confirmation_option` 函数装饰器来实现:

.. click:确认参数形式示例2::

    @click.command()
    @click.confirmation_option(prompt='Are you sure you want to drop the db?')
    def dropdb():
        click.echo('Dropped all tables!')

.. admonition:: 回调信号变更

    在 Click 2.0 版本中，回调信号有了变化。对于更多这方面的信息
    阅读 :ref:`upgrade-to-2.0` 参考文档。

来自环境变量的值
---------------------------------

在 Click 中一个非常有用的特性就是能够接受来自环境变量的参数值作为常规参数值。
这样允许许多命令行工具更容易实现自动化。例如，你也许想要用一个 ``--config`` 
 可选项来代入一个配置文件，但也能够支持为更好的开发体验支持导出一个
 ``TOOL_CONFIG=hello.cfg`` 键值对儿。

那么 Click 有 2 种方法来支持这种实现。
一个是自动化建立环境变量只为可选项来获得支持。
要开启这种特性， ``auto_envvar_prefix`` 
参数需要代入到被触发的脚本中。每个命令和参数
都是稍后加入成一种全大写用下划线分隔的变量。
如果你有一个名叫 ``foo`` 的子命令得到了一个
名叫 ``bar`` 的可选项，那么前缀就是 ``MY_TOOL`` 了，
那么变量名就是 ``MY_TOOL_FOO_BAR`` 形式。

示例用法:

.. click:环境变量值示例::

    @click.command()
    @click.option('--username')
    def greet(username):
        click.echo('Hello %s!' % username)

    if __name__ == '__main__':
        greet(auto_envvar_prefix='GREETER')

运行时的情况:

.. click:run::

    invoke(greet, env={'GREETER_USERNAME': 'john'},
           auto_envvar_prefix='GREETER')

当 ``auto_envvar_prefix`` 与群组命令一起使用的时候，
命令名需要包含在环境变量中，在前缀和参数名之间，
 *例如：* *PREFIX_COMMAND_VARIABLE*

示例:

.. click:群组命令环境变量值示例::

   @click.group()
   @click.option('--debug/--no-debug')
   def cli(debug):
       click.echo('Debug mode is %s' % ('on' if debug else 'off'))

   @cli.command()
   @click.option('--username')
   def greet(username):
       click.echo('Hello %s!' % username)

   if __name__ == '__main__':
       cli(auto_envvar_prefix='GREETER')

.. click:run::

   invoke(cli, args=['greet',],
          env={'GREETER_GREET_USERNAME': 'John', 'GREETER_DEBUG': 'false'},
          auto_envvar_prefix='GREETER')


第二个可选项是手动获得描述的环境变量值，环境变量的名字是定义在可选项上的。

示例用法:

.. click:手动描述环境变量名给可选项示例::

    @click.command()
    @click.option('--username', envvar='USERNAME')
    def greet(username):
        click.echo('Hello %s!' % username)

    if __name__ == '__main__':
        greet()

运行时的情况:

.. click:run::

    invoke(greet, env={'USERNAME': 'john'})

在这种情况下也可以用不同的环境变量列表，但第一个会被选用。

多值环境变量
---------------------------------------

由于许多可选项能接收多个值，
那么获得多值环境变量的时候 (都是字符串类型) 
需要一点多层化处理。那么 Click 解决这个问题
的方法是通过留给类型来自定义这种行为。
对于 ``multiple`` 和 ``nargs`` 参数带着的
许多值都会大于 ``1`` ，那么 Click 会触发
 :meth:`ParamType.split_envvar_value` 方法
来执行分解这些值。

默认都是用空格来分解所有类型。对于这种规则的例外情况
都是 :class:`File` 类和 :class:`Path` 类所代表
的类型，这些类型都要根据操作系统的路径分解规则来进行分解。
在 Unix 类型的系统上，像 Linux 和 OS X 系统，分解都是
使用冒号 (``:``) 的，而对于 Windows 系统则是使用分号 (``;``)

示例用法:

.. click:多值环境变量示例::

    @click.command()
    @click.option('paths', '--path', envvar='PATH', multiple=True,
                  type=click.Path())
    def perform(paths):
        for path in paths:
            click.echo(path)

    if __name__ == '__main__':
        perform()

运行时的情况:

.. click:run::

    import os
    invoke(perform, env={'PATHS': './foo/bar%s./test' % os.path.pathsep})

其它前缀字符
-----------------------

Click 能处理另外一种前缀字符，不止可选项所用的 ``-`` 前缀。
如果你想要处理斜杠 ``/`` 作为参数或类似情况这个功能就有用了。
注意在通用中是非常不鼓励这个功能，因为 Click 想要开发者们与
 POSIX 系统语义保持紧密联系。不管如何做到的，在某些情况下本
功能是有用的:

.. click:其它前缀字符示例1::

    @click.command()
    @click.option('+w/-w')
    def chmod(w):
        click.echo('writable=%s' % w)

    if __name__ == '__main__':
        chmod()

运行时的情况:

.. click:run::

    invoke(chmod, args=['+w'])
    invoke(chmod, args=['-w'])

注意，如果你正在使用斜杠 ``/`` 作为前缀字符的话，
你想要使用布尔旗语的话，你需要用分号 ``;`` 来分隔，
而不是再使用斜杠 ``/`` 了，这是为了避免歧义:

.. click:其它前缀字符示例2::

    @click.command()
    @click.option('/debug;/no-debug')
    def log(debug):
        click.echo('debug=%s' % debug)

    if __name__ == '__main__':
        log()

.. _ranges:

范围可选项
-------------

特别要提一下 :class:`IntRange` 类，它工作起来特别像
 :data:`INT` 数据类型，但限制了值在一个具体范围里
 (起始端都包含的范围) 。并且有 2 种模式都能确保不会导致范围蔓延:

-   默认模式 (非固定模式) 就是一个值超出了范围时会产生一项错误。
-   一种可选固定模式，就是一个值超出了范围会固定到所限范围里。
    意思就是例如一个范围值是 ``0-5`` 的话，那么值是 ``10`` 的时候
    会把值返回成 ``5`` ，而值是 ``-1`` 的时候返回成 ``0`` 值。

示例:

.. click:范围可选项示例::

    @click.command()
    @click.option('--count', type=click.IntRange(0, 20, clamp=True))
    @click.option('--digit', type=click.IntRange(0, 10))
    def repeat(count, digit):
        click.echo(str(digit) * count)

    if __name__ == '__main__':
        repeat()

运行时的情况:

.. click:run::

    invoke(repeat, args=['--count=1000', '--digit=5'])
    invoke(repeat, args=['--count=1000', '--digit=12'])

如果给任何一个范围边缘值代入成 ``None`` 的话，
那就意味着范围的一边被打开不再受限了。

针对验证回调
------------------------

.. versionchanged:: 2.0

如果你想要应用自定义验证逻辑的话，
你可以在参数形式的回调中实现这个目的。
这些回调函数既可以修改值，也可以在验证无效时抛出错误。

在 Click 1.0 版本中, 你只可以抛出 :exc:`UsageError` 例外，
但从 Click 2.0 开始，你也可以抛出 :exc:`BadParameter` 例外。
败坏的参数形式例外错误增加了一种优势，那就是它会自动地格式化错误消息
时也包含了参数形式的名字。

示例:

.. click:针对验证回调示例::

    def validate_rolls(ctx, param, value):
        try:
            rolls, dice = map(int, value.split('d', 2))
            if dice <= 0:
                raise AttributeError("min-sided dice is 1")
            if dice > 6:
                raise AttributeError("max-sided dice is 6")
            return (dice, rolls)
        except ValueError:
            raise click.BadParameter('rolls need to be in format NdM')
        except AttributeError:
            raise click.UsageError(f"There is no {dice}-sided on dice.")

    @click.command()
    @click.option('--rolls', callback=validate_rolls, default='1d6')
    def roll(rolls):
        click.echo('Rolling a %d-sided dice %d time(s)' % rolls)

    if __name__ == '__main__':
        roll()

运行时的情况:

.. click:run::

    invoke(roll, args=['--rolls=42'])
    println()
    invoke(roll, args=['--rolls=2d12'])
