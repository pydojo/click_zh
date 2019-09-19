\$ click\_
==========

Click 是一个 Python 第三方库，为建立美好的命令行接口而开发的简单实用工具。
用少量所需代码组合方式，建立了一套 “命令行接口创建工具集”。
具有高度可配置性能，但默认采用明智的盒外技术。

目标是制作系统层命令行工具，快捷并愉悦地使用，让实现一种 CLI API 变的畅通无阻。

Click 三点论:

-   多命令嵌入式
-   自动生成帮助页面信息
-   支持运行时按需加载子命令


安装
----------

安装与更新都使用 `pip`_:

.. code-block:: text

    $ pip install click

Click 支持大于 Python 3.4 版本和 Python 2.7 以及 PyPy

.. _pip: https://pip.pypa.io/en/stable/quickstart/


来一个直接示例
----------------

那么 Click 看起来会是什么样子呢？下面就是一个简单的 Click 程序:

.. code-block:: python

    import click

    @click.command()
    @click.option("--count", default=1, help="Number of greetings.")
    @click.option("--name", prompt="Your name",
                  help="The person to greet.")
    def hello(count, name):
        """Simple program that greets NAME for a total of COUNT times."""
        for _ in range(count):
            click.echo("Hello, %s!" % name)

与 ``setuptools`` 标准库结合安装后运行这个命令时会是什么效果呢:

.. code-block:: text

    $ hello --count 3
    Your name: Click
    Hello, Click!
    Hello, Click!
    Hello, Click!


捐助
------

调色板组织开发并支持着 Click 和其它受欢迎的众多包。
为贡献者和用户社区增长服务着，并且允许维护者们奉献
更多时间到多项目上， `please donate today`_.

.. _please donate today: https://palletsprojects.com/donate


链接
-----

*   官网: https://palletsprojects.com/p/click/
*   文档: https://click.palletsprojects.com/
*   协议: `BSD <https://github.com/pallets/click/blob/master/LICENSE.rst>`_
*   发布: https://pypi.org/project/click/
*   代码: https://github.com/pallets/click
*   问题追踪: https://github.com/pallets/click/issues
*   测试状态: https://dev.azure.com/pallets/click/_build
*   官方沟通频道: https://discord.gg/t6rrQZH
