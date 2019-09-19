.. rst-class:: hide-header

欢迎来到 Click 库
================

.. image:: _static/click-logo.png
    :align: center
    :scale: 50%
    :target: https://palletsprojects.com/p/click/

Click 是一个用来建立漂亮的命令行接口 Python 第三方库，
使用所需很少的代码就可以实现系统层简单实用的命令行工具。
能够建立一套 “命令行接口创建工具集”，
具有高度可配置性能，但默认采用明智的盒外技术。

目的是制作系统层命令行工具，快捷并愉悦地使用，
让实现一种 CLI API 变的畅通无阻。

Click 三点论:

-   多命令嵌入式
-   自动生成帮助页面信息
-   支持运行时按需加载子命令

那么 Click 看起来会是什么样子呢？下面就是一个简单的 Click 程序::

.. click:example::

    import click

    @click.command()
    @click.option('--count', default=1, help='Number of greetings.')
    @click.option('--name', prompt='Your name',
                  help='The person to greet.')
    def hello(count, name):
        """Simple program that greets NAME for a total of COUNT times."""
        for x in range(count):
            click.echo('Hello %s!' % name)

    if __name__ == '__main__':
        hello()

当运行时看起来可能会是如下样子:

.. click:run::

    invoke(hello, ['--count=3'], prog_name='python hello.py', input='John\n')

也会自动生成良好格式的帮助页面:

.. click:run::

    invoke(hello, ['--help'], prog_name='python hello.py')

你可以直接从 PyPI 获得本库::

    pip install click

文档
-------------

如下是文档部分的指导清单，贯穿了所有本库的用法模式。

.. toctree::
   :maxdepth: 2

   why
   quickstart
   setuptools
   parameters
   options
   arguments
   commands
   prompts
   documentation
   complex
   advanced
   testing
   utils
   bashcomplete
   exceptions
   python3
   wincmd

API 参考文档
-------------

如果你正在寻找一个具体函数、类、或方法的信息，
那么请看如下文档。

.. toctree::
   :maxdepth: 2

   api

杂项内容
-------------------

.. toctree::
   :maxdepth: 2

   contrib
   changelog
   upgrading
   license
