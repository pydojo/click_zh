快速开始
==========

.. currentmodule:: click

直接从 PyPI 上安装::

    pip install click

强烈建议在虚拟环境中来安装，查看 :ref:`virtualenv` 参考文档。

.. _virtualenv:

virtualenv
----------

Virtualenv 是建立虚拟环境的正确选择，对于开发 Click 应用来说亦然。

虚拟环境 virtualenv 到底解决了什么问题？ 
能够让你在许多其它项目中使用 Click 系统层命令模式。
而且更多的项目都能够实现在不同的版本开发中，这就是虚拟环境能解决的。
包括不同的 Python 版本，或不同的 Python 第三方库版本。
正视虚拟环境：常常许多第三方库都会导致软件版本更新时出现断裂，
让你感到以前用没问题，现在用就有问题了，并且每一个系列应用都会有依赖库。
那么如果你的项目不止一两个的话，你就会遇到依赖冲突问题，这是一个头大的问题是吧？

让 Virtualenv 虚拟环境来减轻头痛！
虚拟环境开启了多种连续挨着的 Python 安装，
即时对于每一个项目来说会存在多个 Python 版本的兼容情况。
实际上不是分别安装不同的 Python 版本在系统上，
虚拟环境提供了一种更聪明的方法来保持不同的项目环境，
每个环境都彼此隔离。让我们看看虚拟环境是如何工作的吧。

如果你用的是 Mac OS X 或 Linux 系统的话::

    $ sudo pip install virtualenv

可以安装 virtualenv 虚拟环境库到你的系统上。
也许需要先提前安装 `pip` 包管理器。如果你使用
 Ubuntu 版本的 Linux 系统，那么尝试::

    $ sudo apt-get install python-virtualenv

如果你用的是 Windows 系统的话， (上面的方法就无效了) 
你必须先安装 ``pip`` 。关于更多这方面的信息查看 `installing pip`_.
一旦完成了安装后，在 Windows 上运行 ``pip`` 命令不需要 `sudo` 命令。

.. _installing pip: https://pip.readthedocs.io/en/latest/installing.html

当你安装完 virtualenv 虚拟环境库后，首先要在终端里建立你自己的虚拟环境。
我常常建立一个项目文件夹后，在项目目录里建立一个虚拟环境文件夹 `venv`::

    $ mkdir myproject
    $ cd myproject
    $ virtualenv venv
    New python executable in venv/bin/python
    Installing setuptools, pip............done.

现在不管什么时候你要工作在一个项目上，你只需要激活相关项目
里的虚拟环境即可。在 OS X 和 Linux 系统上，按照如下操作::

    $ . venv/bin/activate

如果在 Windows 系统上，操作如下::

    $ venv\scripts\activate

不管哪种方法，你激活成功后就说明正在使用项目的虚拟环境了
 (注意终端里的提示符会有变化)

如果你想回到系统层环境，使用如下命令::

    $ deactivate

关闭虚拟环境后，终端的提示符就是系统层环境的提示符了。

在虚拟环境中我们来执行安装 Click 命令行库::

    $ pip install Click

几秒之后你就完成了准备工作。

屏幕录制与示例
-----------------------

这里有一种屏幕录制视频，展示了如何用 Click 建立简单的应用。
介绍了 Click 的基础 API 使用，也告诉你如何建立含有子命令的命令内容。

*   `Building Command Line Applications with Click
    <https://www.youtube.com/watch?v=kNke39OZ2k0>`_

使用 Click 应用的示例可以在文档中找到，同时在 GitHub 仓库里含有相关文件:

*   ``inout``: `文件输入与输出
    <https://github.com/pallets/click/tree/master/examples/inout>`_
*   ``naval``: `移植到 docopt 库的示例
    <https://github.com/pallets/click/tree/master/examples/naval>`_
*   ``aliases``: `命令别名示例
    <https://github.com/pallets/click/tree/master/examples/aliases>`_
*   ``repo``: `Git 命令行接口和变体命令行结构
    <https://github.com/pallets/click/tree/master/examples/repo>`_
*   ``complex``: `含有插件加载的多层化示例
    <https://github.com/pallets/click/tree/master/examples/complex>`_
*   ``validation``: `自定义参数验证示例
    <https://github.com/pallets/click/tree/master/examples/validation>`_
*   ``colors``: `彩色命令显示支持
    <https://github.com/pallets/click/tree/master/examples/colors>`_
*   ``termui``: `终端 UI 函数示范
    <https://github.com/pallets/click/tree/master/examples/termui>`_
*   ``imagepipe``: `多命令链示范
    <https://github.com/pallets/click/tree/master/examples/imagepipe>`_

基础概念 - 建立一个命令
-----------------------------------

Click 是基于通过装饰器来声明命令的工作方式。
内部里，是一个非装饰器接口提供给高级用例，但
对于高级别用法来说是不鼓励这样使用的。

一个 Python 函数要想变成一个终端命令，
是通过 Click 的装饰器用法 :func:`click.command` 函数来实现的。
简单实用的技术在于直接用它来装饰一个函数即可:

.. click:示例::

    import click

    @click.command()
    def hello():
        click.echo('Hello World!')

上面的代码发生了什么？装饰器把函数变成一个
:class:`Command` 类的实例，然后用脚本习语来触发::

    if __name__ == '__main__':
        hello()

那么这看起来会是什么样子呢？:

.. click:运行命令时::

    invoke(hello, args=[], prog_name='python hello.py')

命令有帮助页面信息时会是:

.. click:运行命令时::

    invoke(hello, args=['--help'], prog_name='python hello.py')

回声
-------

为什么上面示例中会使用 :func:`echo` 函数来代替
常规的 :func:`print` 函数呢？答案就是 Click
 意图是使用相同的方法来支持 Python 2 和 Python 3 ，
并且这样会非常健壮，即使错误配置环境也能保证有效。
 Click 在基础层上至少要是函数式的，即使每件事出现
破裂也能保证功能独立性。

那么 :func:`echo` 函数意味着什么？在函数中应用了
一些错误纠正，在终端存在错误配置时用一个
 :exc:`UnicodeError` 来代替死命令情况。

增加这项支持的好处是从 Click 2.0 开始的， echo 函数也
良好地支持着 ANSI 彩色机制。它会自动地剥离 ANSI 代码内容，
如果输出流数据是一个文件的话，并且支持彩色机制的话， ANSI 颜色
也会在 Windows 系统上有效。注意在 Python 2 中，
 :func:`echo` 函数是不能对来自字节阵列的颜色代码进行语法分析的。
查看 :ref:`ansi-colors` 参考文档了解更多信息。

如果你不需要这种好处的话，你也可以使用 `print()` 函数。

嵌入命令
----------------

许多命令可以跟在 :class:`Group` 类型的其它命令后面使用。
这样就可以实现许多脚本的任何嵌入用法。这里有一个示例，为管理
数据库实现了 2 个命令嵌入式使用:

.. click:嵌入命令示例1::

    @click.group()
    def cli():
        pass

    @click.command()
    def initdb():
        click.echo('Initialized the database')

    @click.command()
    def dropdb():
        click.echo('Dropped the database')

    cli.add_command(initdb)
    cli.add_command(dropdb)

你可以明白 :func:`group` 装饰器工作起来就像 :func:`command` 装饰器一样，
但它建立了一个 :class:`Group` 类实例，所以使用 :meth:`Group.add_command`
 方法后，才能够使用多个子命令方式。

杜宇简单的脚本来说，也可以直接使用 :meth:`Group.command` 装饰器来
实现自动跟着建立一个命令行命令。那么上面的嵌入命令示例可以写成如下代码:

.. click:嵌入命令示例2::

    @click.group()
    def cli():
        pass

    @cli.command()
    def initdb():
        click.echo('Initialized the database')

    @cli.command()
    def dropdb():
        click.echo('Dropped the database')

然后你应该在 setuptools 的配置文件入口点参数中来触发 :class:`Group` 类，
或者采用脚本习语方式来触发::

    if __name__ == '__main__':
        cli()

增加命令参数
-----------------

要给一个命令增加参数，使用 :func:`option` 函数和
 :func:`argument` 装饰器:

.. click:增加命令参数示例::

    @click.command()
    @click.option('--count', default=1, help='number of greetings')
    @click.argument('name')
    def hello(count, name):
        for x in range(count):
            click.echo('Hello %s!' % name)

触发时是什么样子呢:

.. click:运行命令时::

    invoke(hello, args=['--help'], prog_name='python hello.py')

.. _switching-to-setuptools:

切换到 Setuptools 标准库
-----------------------

上面所写的那些代码中可执行区域的脚本习语用法:
 ``if __name__ == '__main__':`` 是传统的
运行独立 Python 模块的方式。在使用 Click 库时，
你可以继续这样做，但通过 setuptools 标准库是更好的方式。

这样做的主要原因有 2 个 (还有更多原因) :

第一个：是 setuptools 标准库自动生成可执行打包器给 Windows 系统，
所以你的命令行工具在 Windows 系统上也有效。

第二个：是 setuptools 标准库建立的脚本使用 virtualenv 工作在
没有激活虚拟环境的 Unix 系统上。这是非常有用的概念，因为让你把脚本
与所有需求绑定到一个虚拟环境中。

Click 更愿意与这种方式工作，并且事实上后面的文档内容都是建立在
这个假设前提之上，所以都要写一个 setuptools 标准库配置文件。

我强烈建议接下来阅读 :ref:`setuptools-integration` 参考文档，
然后再去阅读其它示例，先把本文档中的示例与 setuptools 结合起来运行成功再说。
