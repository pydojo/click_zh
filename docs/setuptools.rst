.. _setuptools-integration:

Setuptools 标准库集成
======================

当写完命令行工具代码后，第二件事就是写 setuptools 配置模块文件，
而不再使用 Unix shebangs 技术了。

为什么要这样做？如下是这样做的原因:

1.  传统实现方式有一个问题，就是第一个模块被 Python 解释器加载时存在错误的名字。
    这也许听起来是一个小问题，但这却能给你带来足够的头疼。

    第一个模块实际上不是命令名，但解释器会把模块名重命名给 ``__main__`` 。
    在小学 Python 课程 Python 模块单元已经讲过。如果你想在其它模块导入
    这个模块中其它函数时，这样会正确地处理成模块名，那么被导入模块会触发第二次
    导入过程，并且所有代码都导入了 2 次。

2.  不是在所有的平台上都那么容易执行。在 Linux 和 OS X 系统上，你可以在模块首行
    增加 (``#!/usr/bin/env python``) shebang 技术支持。然后你的脚本支持了可
    执行工作方式 (当然还要设置可执行属性) 。不管如何做到的，但依然要使用例如
     ``./example.py`` 的方式来执行。而在 Windows 系统上就要使用 ``example.py``
     带有文件名后缀来执行 (因为要通过 Python 解释器来执行模块文件)。如果你想用
     ``example`` 命令方式执行，或在虚拟环境中执行就会遇到问题。

    事实上运行一个脚本都是与系统层有关，而且传统的实现方法并不友好，并且要激活虚拟环境
    才能正确使用 Python 解释器。

3.  如果只是一个 Python 模块文件的话，传统技巧还可以实现。
    但如果你的应用成长为大型应用的话，然后你想使用一个包来启动应用，
    那么运行时就会遇到许多问题。

介绍
------------

要把你的脚本与 setuptools 绑定在一起，你需要做的所有事情就是
为一个 Python 包的脚本写一个 ``setup.py`` 配置文件。

想象一下此时的目录结构是:

.. code-block:: text

    yourscript.py
    setup.py

其中 ``yourscript.py`` 代码内容是:

.. click:脚本示例代码::

    import click

    @click.command()
    def cli():
        """Example script."""
        click.echo('Hello World!')

其中 ``setup.py`` 代码内容是:

.. code-block:: python

    from setuptools import setup

    setup(
        name='yourscript',
        version='0.1.0',
        py_modules=['yourscript'],
        install_requires=[
            'Click',
        ],
        entry_points={
            'console_scripts': [
                'yourscript = yourscript:cli',
            ],
        },
    )

这里的奥妙在于 ``entry_points`` 入口点参数里。其中下面的
``console_scripts`` 中每一行都是识别一条终端脚本。
每行等号 (``=``) 前的部分是你写的 Python 模块名，指明生成脚本的模块，
等号后面的第二部分是导入路径后跟着一个冒号 (``:``) 再跟着 Click 命令名。

就这些！

测试一下脚本
------------------

要测试脚本，你可以建立一个新的虚拟环境后安装你的脚本:

.. code-block:: console

    $ virtualenv venv
    $ . venv/bin/activate
    $ pip install --editable .

测试时安装要用可编辑模式，之后你的命令应该可以直接使用模块名了:

.. click:run::

    invoke(cli, prog_name='yourscript')

包里的脚本
-------------------

如果你的脚本不断成长，并且你想要把脚本放到一个目录里的话，
只需要在配置模块中很少的变更即可。假设你的目录结构变成了如下情况:

.. code-block:: text

    project/
        yourpackage/
            __init__.py
            main.py
            utils.py
            scripts/
                __init__.py
                yourscript.py
        setup.py

在这种情况中，在你的 ``setup.py`` 配置文件里要用
``packages`` 配置项代替 ``py_modules`` 配置项。
然后使用 setuptools 标准库的 ``find_packages`` 函数来自动找到目录。
另外也建议使用 ``include_package_data`` 配置项。

修改后的 ``setup.py`` 配置文件代码内容是:

.. code-block:: python

    from setuptools import setup, find_packages

    setup(
        name='yourpackage',
        version='0.1.0',
        packages=find_packages(),
        include_package_data=True,
        install_requires=[
            'Click',
        ],
        entry_points={
            'console_scripts': [
                'yourscript = yourpackage.scripts.yourscript:cli',
            ],
        },
    )

另外即使项目结构是如下也依然有效:

.. code-block:: tree .

    .
    ├── yourpackage
    │   └── scripts
    │       └── yourscript.py
    └── setup.py
