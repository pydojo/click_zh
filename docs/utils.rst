工具集
=========

.. currentmodule:: click

除了 Click 提供的含有参数语法分析和处理的功能外，
也提供了一堆功能插件，在些命令行工具集时是有用的。


输出到标准输出
------------------

最明显的助手就是 :func:`echo` 函数，它有许多种工作方式，
就像 Python 的 ``print`` 语句或函数一样。主要差异在于
`echo` 在 Python 2 和 3 中效果是一样的，它会智能地检测
错误配置的输出流数据，并且它永远不会失败 (在 Python 3 中
有个例外，阅读 :ref:`python3-limitations` 参考文档来了解)

示例::

    import click

    click.echo('Hello World!')

最重要的特性是它可以输出 Unicode 和二进制数据，这与 Python 3
 中的内置 ``print`` 函数不同，因为不能输出任何字节内容。
`echo` 不管如何做到的，它会默认发出一个结束位的新行字符，要想
不输出这个可以通过代入 ``nl=False`` 参数来实现::

    click.echo(b'\xe9\x81\x93', nl=False)

最后，但不止 :func:`echo` 使用了 click 的智能内部输出流数据给
标准输出和标准错误，它还支持在 Windows 终端里的 unicode 输出。
这意味着，你一直使用 `click.echo` 工具的话，你可以输出 unicode 
字符 (在默认字体上会有一些限制，可能有些字体无法显示)。这种功能是在
 Click 6.0 版本中新增的。

.. versionadded:: 6.0

Click 现在在 Windows 系统上模拟输出流数据来支持 unicode 显示在
 Windows 终端上，是通过另外的  APIs 实现的，对于更多这方面信息阅读
 :doc:`wincmd` 文档内容。

.. versionadded:: 3.0

从 Click 3.0 开始你也可以容易输出到标准错误里，通过代入
 ``err=True`` 参数来实现::

    click.echo('Hello World!', err=True)


.. _ansi-colors:

八色彩机制
-----------

.. versionadded:: 2.0

从 Click 2.0 开始， :func:`echo` 函数获得了额外的功能来处理
 ANSI 色彩机制和风格。注意在 Windows 系统上，如果安装了
 `colorama`_ 色彩机制的话，这个功能是不可用的，那么 ANSI 代号
都会智能地进行处理过再显示。注意在 Python 2 里，`echo` 函数不
对来自字节阵列的色彩代号信息进行语法分析。

主要意思就是:

-   如果流数据没有连接到一个终端的话，Click 的 :func:`echo` 函数
    会自动剥离 ANSI 色彩代号。
-   其中 :func:`echo` 函数会明显地连接到 Windows 系统上的终端，
    然后把 ANSI 色彩代号翻译成 Windows 终端 API 去调用。这就是
    说色彩在 Windows 系统上效果会一样有效，其它系统不需要这样的翻译。

注意，对于支持 `colorama` 色彩机制来说: 当 `colorama` 色彩机制
可用并且使用了这种机制时， Click 会自动检测。所以*不要调用*
 ``colorama.init()`` 第三方库！

要想安装 `colorama` 第三方库，运行如下命令::

    $ pip install colorama

对于一个字符串风格化来说， :func:`style` 函数可以使用::

    import click

    click.echo(click.style('Hello World!', fg='green'))
    click.echo(click.style('Some more text', bg='blue', fg='white'))
    click.echo(click.style('ATTENTION', blink=True, bold=True))

实际上 :func:`echo` 函数和 :func:`style` 函数的一种组合函数
可以单独使用，那就是 :func:`secho` 函数::

    click.secho('Hello World!', fg='green')
    click.secho('Some more text', bg='blue', fg='white')
    click.secho('ATTENTION', blink=True, bold=True)


.. _colorama: https://pypi.org/project/colorama/

页面支持
-------------

在某些情况下，你也许想要显示长文本内容在终端上，然后让用户来翻页。
这可以通过使用 :func:`echo_via_pager` 函数来实现，它工作起来
类似 :func:`echo` 函数，但会一直把内容写到标准输出上，如果内容
很多的话，会形成一页内容。

示例:

.. click:页面支持示例1::

    @click.command()
    def less():
        click.echo_via_pager('\n'.join('Line %d' % idx
                                       for idx in range(200)))

如果你使用了大量文字的话，尤其是有很多细节要说明的话，你可以代入一个
生成器对象 (或生成器函数) 来代替书写一个字符串:

.. click:页面支持示例2::
    def _generate_output():
        for idx in range(50000):
            yield "Line %d\n" % idx

    @click.command()
    def less():
        click.echo_via_pager(_generate_output())


清屏
---------------

.. versionadded:: 2.0

要对终端清屏，你可以使用 :func:`clear` 函数，从 Click 2.0 开始
就有这个工具了。顾名思义: 它会用一种不受操作系统限制的方式来清楚整个
屏幕显示的内容:

::

    import click
    click.clear()


从终端获得字符
--------------------------------

.. versionadded:: 2.0

正常情况下，当从终端读取输入数据时，你要从标准输入来读取。
不管如何做到的，这里是经过缓存的输入，并且不会显示除非是
标准输入。在某些情况下，你也许不想要缓存输入，而是需要逐个
字符来读取，如同我们写字一样。

对于逐字读取来说， Click 提供了 :func:`getchar` 函数
来从终端缓存里读取单个字符，然后返回成一个 Unicode 字符。

注意，这个函数会一直从终端来读取，即使标准输入被一个代替也是如此。

逐字读取示例::

    import click

    click.echo('Continue? [yn] ', nl=False)
    c = click.getchar()
    click.echo()
    if c == 'y':
        click.echo('We will go on')
    elif c == 'n':
        click.echo('Abort!')
    else:
        click.echo('Invalid input :(')

注意，这个示例读取的是生食输入数据，意味着像箭头按键会显示成系统的原生转义格式。
可以翻译成功的字符只有 ``^C`` 和 ``^D`` ，这两个组合字符分别是键盘的打断信号输入
和文件例外终止信号。实现识别这两个组合键输入是因为很容易忘记在建立脚本时无法正常
退出脚本的缘故。


等待按下键盘
---------------------

.. versionadded:: 2.0

有时候暂停是有用的，直到用户按下任意一个按键后才继续。
这在 Windows 系统上尤其有用，因为 ``cmd.exe`` 会
默认在脚本命令执行完时自动关闭窗口，相反我们一般都是
要用等待来保持窗口依然存在，由你来决定什么时候关闭窗口。

在 click 里可以用 :func:`pause` 函数来实现。这个
函数会输出一个快讯给终端 (当然可以自定义这个消息内容) 
然后等着用户按下一个按键来结束。另外如果脚本不是以
互动式运行的话，这个命令也会变成一种 NOP (无操作指导)

等待按键示例::

    import click
    click.pause()


启动编辑器
-----------------

.. versionadded:: 2.0

Click 支持通过 :func:`edit` 函数来自动启动编辑器。
对于让用户多行输入来说是非常有用的。它会自动打开用户
定义完的编辑器，或自动打开默认编辑器。如果用户没有
保存就关闭文本编辑器的话，返回值会是 `None` ，那么
要获得输入的文本内容就要先保存再退出。

启动文本编辑器示例1::

    import click

    def get_commit_message():
        MARKER = '# Everything below is ignored\n'
        message = click.edit('\n\n' + MARKER)
        if message is not None:
            return message.split(MARKER, 1)[0].rstrip('\n')

另一种情况，这个函数也可以实现用文本编辑器打开一个文件。
在这种情况下，返回值一直会是 `None`

启动文本编辑器示例2::

    import click
    click.edit(filename='/etc/passwd')


启动应用程序
----------------------

.. versionadded:: 2.0

Click 通过 :func:`launch` 函数支持启动应用程序。
这可以用来启动打开一个 URL 或打开一个文件类型的应用程序。
例如，可以用来启动网络浏览器或图片阅读器。
另外这个函数也可以启动文件管理器后自动定位到所提供的文件。

启动应用程序示例::

    click.launch("https://click.palletsprojects.com/")
    click.launch("/my/downloaded/file.txt", locate=True)


输出文件名
------------------

由于文件名也许不是 Unicode 字符，格式化时会有一点技巧。
通用中，在 Python 2 中要比 3 更容易一些，因为你可以只
用 ``print`` 语句写字节给标准输出，但在 Python 3 里
你要一直需要 Unicode 解码操作。

click 通过 :func:`format_filename` 函数可以保持这种
工作效果。它做了最多的努力把文件名转换成 Unicode 并且永
不会失败。这让在一个完全 Unicode 字符串语境中直接使用
文件名变成可能。

输出文件名示例::

    click.echo('Path: %s' % click.format_filename(b'foo.txt'))


标准流数据
----------------

对于命令行工具集来说，可靠地获得输入和输出数据流是非常重要的事情。
Python 通用中使用 ``sys.stdout`` 友好地提供了访问这些数据流，
但不幸的是，在 Python 2 和 3 之间有许多 API 上的差异，尤其是
这些数据流如何对 Unicode 和二进制数据做响应。

由于这个原因， click 提供了 :func:`get_binary_stream` 函数
和 :func:`get_text_stream` 函数，它们用不同的 Python 版本也
可以产生连续的结果，并且针对各种不同的大范围终端配置做出响应。

这 2 个函数的最终结果会一直返回一种功能性的数据流对象 (除了
在 Python 3 非常奇怪的情况里有异常，阅读
 :ref:`python3-limitations` 参考文档了解)

标准流数据示例::

    import click

    stdin_text = click.get_text_stream('stdin')
    stdout_binary = click.get_binary_stream('stdout')

.. versionadded:: 6.0

Click 目前在 Windows 系统上模拟输出流数据来支持 unicode 字符
到 Windows 终端里是通过分开来的 APIs 实现。对于更多信息阅读
 :doc:`wincmd` 文档内容。


智能文件打开
------------------------

.. versionadded:: 3.0

从 Click 3.0 开始，来自 :class:`File` 类型的文件打开逻辑
是通过 :func:`open_file` 函数来曝光的。它可以智能地打开
标准输入/标准输出，与打开任何一个其它文件都是一样的。

智能文件打开::

    import click

    stdout = click.open_file('-', 'w')
    test_file = click.open_file('test.txt', 'w')

如果标准输入或标准输出都返回完毕，返回值被打包进一个特殊文件中，
这个文件所处的语境管理器会保护文件的关闭。这让标准流数据的处理
变得透明化，并且你可以像下面一样一直使用它::

    with click.open_file(filename, 'w') as f:
        f.write('Hello World!\n')


发现应用程序文件夹
---------------------------

.. versionadded:: 2.0

最常发生的就是你想要打开一个属于你应用程序的配置文件。
不管如何做到的，不同的操作系统存储这些配置文件的位置
都不一样，因为它们的标准不一样。 Click 提供了一个
 :func:`get_app_dir` 函数，它根据操作系统返回
最适合每个用户的应用程序配置文件所在位置。

示例用法::

    import os
    import click
    import ConfigParser

    APP_NAME = 'My Application'

    def read_config():
        cfg = os.path.join(click.get_app_dir(APP_NAME), 'config.ini')
        parser = ConfigParser.RawConfigParser()
        parser.read([cfg])
        rv = {}
        for section in parser.sections():
            for key, value in parser.items(section):
                rv['%s.%s' % (section, key)] = value
        return rv


显示进度条
---------------------

.. versionadded:: 2.0

有时候你的命令行脚本需要处理大量数据，
但需要快速显示用户的某种处理过程进度，
进度条就是说明会处理多长时间的最好工具。
 Click 支持一个简单的进度条，它通过
 :func:`progressbar` 函数来翻译进度时间。

基本用法很直接: 思路就是你有一个可迭代对象时，
你可以在这个对象上做操作。可迭代对象里的每项
元素的处理都是要花费一些时间的。用法看起来像迭代::

    for user in (x for x in range(100000)):
        self_multiplied = user * user

要用一个自动更新的进度条来勾起这个过程，你所要做的
全部工作就是把上面的迭代过程变成如下代码的样子::

    import click

    with click.progressbar((x for x in range(100000))) as bar:
        for user in bar:
            self_multiplied = user * user

Click 然后会自动地输出一个进度条到终端里，并且为你计算剩余时间。
剩余时间的计算是需要可迭代对象的规模大小，也就是迭代对象的长度。
如果迭代对象没有一个长度或无法知道它的长度的话，你可以明确提供长度值::

    with click.progressbar((x for x in range(100000)),
                           length=100000) as bar:
        for user in bar:
            self_multiplied = user * user

另外一个有用的特性是给进度条增加一个相关标签信息，这会显示在进度条头部::

    with click.progressbar((x for x in range(100000)),
                           label='Modifying user accounts',
                           length=100000) as bar:
        for user in bar:
            self_multiplied = user * user

有时，一种情况是需要迭代一个外部迭代器，并且让进度条呈现不规律的状态。
要实现这个高级点的特性，你需要描述长度值 (即没有可迭代对象时的用法)
后在语境中使用更新方法返回值，而不是直接迭代外部迭代器::

    with click.progressbar(length=500000,
                           label='Unzipping archive') as bar:
        for archive in range(1, 400000):
            archive = archive / archive
            bar.update(archive)
