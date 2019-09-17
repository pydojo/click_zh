支持 Python 3
================

.. currentmodule:: click

Click 已经支持 Python 3 了，但可能会支持其它更多的命令行工具库，
因为我们要学会承受 Python 3 中的 Unicode 文本情况。
文档中的所有写完的示例既可以运行在 Python 2.x 和 Python 3.4 更高的版本上。

.. _python3-limitations:

Python 3 的约束
--------------------

此时， Click 承受着较少的 Python 3 中的一点儿问题：

*   在 Unix 系统中命令行传统方式采用了字节数据类型，还没有更新为 Unicode 数据类型。
    同时在这点上都要注意编码的问题，通用中有一些情况会出现断裂现象。
    绝大多数共性问题是一种 SSH 连接到不同位置的计算机环境。

    配置错误的操作系统环境在 Python 3 中会导致大范围 Unicode 问题，
    因为缺少替换转义字符的环绕处理支持。这不是 Click 自身能够解决的，
    是各种操作系统的字节编码都没有采用 Unicode 所导致的！

    更多这方面的信息查看 :ref:`python3-surrogates` 参考文档。

*   在 Python 3 中的标准输入和输出都是以 Unicode 模式作为默认设置。
    Click 已经会在某些环境中以二进制模式重新打开数据流。
    因为目前没有实现全球 Unicode 标准化，所以这可能不会一直有效。
    因为 Unicode 没有实现全球标准化，所以当测试命令行程序时这可能是一个主要问题。

    所以如下代码是不支持的::

        sys.stdin = io.StringIO('Input here')
        sys.stdout = io.StringIO()

    反而你要实现如下代码才有效::

        input = 'Input here'
        in_stream = io.BytesIO(input.encode('utf-8'))
        sys.stdin = io.TextIOWrapper(in_stream, encoding='utf-8')
        out_stream = io.BytesIO()
        sys.stdout = io.TextIOWrapper(out_stream, encoding='utf-8')

    记住这种情况，你需要使用 ``out_stream.getvalue()`` 方法，
    而不要用 ``sys.stdout.getvalue()`` 方法。因为如果你要访问
    缓存内容作为打包器的话，就不能直接起作用。

Python 2 和 3 的区别
--------------------------

Click 库的意图是要最小化二者之间的区别，这样对于 2 和 3 来说都要
遵循如下最实际的做法。

在 Python 2 中，如下是成立的:

*   ``sys.stdin``, ``sys.stdout``, 和 ``sys.stderr`` 都是以二进制模式打开的，
    但在某些情形下也会支持 Unicode 输出。 Click 是不会破坏这种情况，反而提供了强制
    数据流作为 Unicode 数据类型的支持。
*   ``sys.argv`` 一直是基于字节类型的。 Click 会把字节传入所有输入类型中，然后
    根据需要来进行转换。那么 :class:`STRING` 类型会自动地正确解码输入的值成一种
    字符串，通过最合适的编码来进行尝试转换。
*   当处理文件时， Click 永远不会通过 Unicode APIs 并且会使用操作系统的字节 APIs
    来打开文件。

在 Python 3 中，如下是成立的:

*   ``sys.stdin``, ``sys.stdout`` 和 ``sys.stderr`` 都是默认基于文本的。
    当 Click 需要一种二进制数据流时，会去根据二进制数据流来探索。目前这是如何
    工作的？需要查看 :ref:`python3-limitations` 参考文档。
*   ``sys.argv`` 一直是基于 Unicode 编码。这也就意味着输入的值原生类型在
    Click 中是 Unicode 类型，而不是字节类型了。

    如果终端采用的字符集设置不正确的话，这会导致一些问题，而且 Python 也不会知道
    系统终端的编码采用了什么字符集。在这种情形中， Unicode 字符串会含有错误的字节，
    因为字节编码成替换形式的转义字符。
*   当处理文件时， Click 一直会使用 Unicode 文件系统的 API 调用，这是通过使用了
    操作系统告之的或猜测出文件系统采用的编码字符集。替代形式都支持许多文件名，
    所以通过 :class:`File` 类型可以打开许多文件，即使系统环境配置错误也有可能没问题。

.. _python3-surrogates:

Python 3 替代形式处理
---------------------------

在 Python 3 中 Click 实现了全部 Unicode 处理，采用的是标准库和对象的主观表现。
在 Python 2 中， Click 是自身完成所有 Unicode 处理的，那么在错误行为上会有差异。

绝大多数让人愤怒的差异都是发生在 Python 2 中， Unicode 会刚好能工作，
而在 Python 3 里需要额外注意。对于在 Python 3 中额外注意的原因是，
编码检测是用解释器来实现的，并且在 Linux 系统上以及其它某些操作系统上，
操作系统的编码处理是因为没有全部采用 Unicode 编码造成的。所以下个时代的
操作系统发展趋势是全部采用 Unicode 来进行编码。

目前来说最大的失望就是 Click 脚本通过系统初始化进程来触发
 (sysvinit, upstart, systemd, etc.)，部署工具 (salt,
puppet)，或 cron 工作列队 (cron) 会罢工，除非导出成一种
本地 Unicode 环境变量。

如果 Click 遇到这种环境的话， Click 会组织下一步执行让你
去设置好一个本地环境变量。这种实现方法是因为 Click 无法知道
操作系统的状态，一旦 Click 引入到系统级别后存储这些环境变量值
是在 Python 的 Unicode 处理介入之前发生。

如果你在 Python 3 中看到如下错误的话::

    Traceback (most recent call last):
      ...
    RuntimeError: Click will abort further execution because Python 3 was
      configured to use ASCII as encoding for the environment. Either switch
      to Python 2 or consult the Python 3 section of the docs for
      mitigation steps.

说明你所处的环境是 Python 3 认为你被限制使用 ASCII 数据类型。
解决方案的不同是依据你的电脑运行在什么本地变量环境里。

例如，如果你使用了德语的 Linux 操作系统的话，你可以通过把系统的
本地环境变量导出成 ``de_DE.utf-8`` 来解决问题::

    export LC_ALL=de_DE.utf-8
    export LANG=de_DE.utf-8

如果你使用的是英语操作系统的话， ``en_US.utf-8`` 是该选择的编码。
在一些较新的 Linux 系统上，你也可以尝试把 ``C.UTF-8`` 作为本地环境变量值::

    export LC_ALL=C.UTF-8
    export LANG=C.UTF-8

在一些操作系统上所报告的 `UTF-8` 已经写成 `UTF8` 形式，并且反之亦然。
要想查看本地环境变量值都能使用哪些的话，你可以使用 ``locale -a`` 命令::

    locale -a

在你引入到你的 Python 脚本之前需要做好本地环境变量值的设置。
如果你好奇这个问题，你可以参与 Python 3 bug 追踪器的讨论:

*   `ASCII is a bad filesystem default encoding
    <http://bugs.python.org/issue13643#msg149941>`_
*   `Use surrogateescape as default error handler
    <http://bugs.python.org/issue19977>`_
*   `Python 3 raises Unicode errors in the C locale
    <http://bugs.python.org/issue19846>`_
*   `LC_CTYPE=C:  pydoc leaves terminal in an unusable state
    <http://bugs.python.org/issue21398>`_ (this is relevant to Click
    because the pager support is provided by the stdlib pydoc module)

注意 (Python 3.7 以后): 即时你的本地环境变量没有正确地配置，
 Python 3.7 版本的 Click 不会抛出以上的例外类型，因为
 Python 3.7 所写的程序在选择默认本地环境变量上会有更好的效果。
但这不会改变由于错误配置本地环境变量所导致的通用问题。

Unicode 字面意思
----------------

从 Click 5.0 开始，在 Python 2 中导入使用 ``unicode_literals`` 会做出警告。
这么做是因为这种导入会产生消极结果，这种导入产生的 bugs 是由于把 Unicode 数据
介绍给 APIs 所致，而这些 APIs 都不具备处理 Unicode 数据的能力。
这种问题的一些例子可以查看在 github 上的讨论: `python-future#22
<https://github.com/PythonCharmers/python-future/issues/22>`_.

如果你在任何一个文件中使用 ``unicode_literals`` 的话，
文件中定义的一个 Click 命令或引入的一个命令都会给出这种警告。
强烈建议你不要使用 ``unicode_literals`` 了，反而要在 Python 2 中
明确使用 ``u`` 前缀来写 Unicode 字符串。

如果你想要忽略这个警告的话，并继续使用 ``unicode_literals`` 的话，
风险自担，你可以禁用警告，方法如下::

    import click
    click.disable_unicode_literals_warning = True
