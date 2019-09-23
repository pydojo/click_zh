测试 Click 应用程序
==========================

.. currentmodule:: click.testing

对于基础测试来说， Click 提供了 :mod:`click.testing` 模块，
该模块提供了测试功能，帮助你触发命令行应用程序和检查程序行为。

这些测试工具真的应该只用在测试中，因为它们会简单地改变整个解释器状态，
并且处于一种没有任何线程安全环境中！

基础测试
-------------

对于测试 Click 应用程序的基础功能是 :class:`CliRunner` 类负责，
它可以把许多命令触发成命令行脚本。其中 :meth:`CliRunner.invoke` 
方法在隔离环境中运行命令行脚本后把输出捕获成字节和二进制数据。

返回值是一个 :class:`Result` 类实例对象，它含有捕获的的输出数据、
退出代号、跟随的可选例外类型:

.. code-block:: python
   :caption: hello.py

   import click

   @click.command()
   @click.argument('name')
   def hello(name):
      click.echo('Hello %s!' % name)

.. code-block:: python
   :caption: test_hello.py

   from click.testing import CliRunner
   from hello import hello

   def test_hello_world():
     runner = CliRunner()
     result = runner.invoke(hello, ['Peter'])
     assert result.exit_code == 0
     assert result.output == 'Hello Peter!\n'

对于子命令测试来说，一个子命令名必须描述在 :meth:`CliRunner.invoke` 方法的
 `args` 参数值中:

.. code-block:: python
   :caption: sync.py

   import click

   @click.group()
   @click.option('--debug/--no-debug', default=False)
   def cli(debug):
      click.echo('Debug mode is %s' % ('on' if debug else 'off'))

   @cli.command()
   def sync():
      click.echo('Syncing')

.. code-block:: python
   :caption: test_sync.py

   from click.testing import CliRunner
   from sync import cli

   def test_sync():
     runner = CliRunner()
     result = runner.invoke(cli, ['--debug', 'sync'])
     assert result.exit_code == 0
     assert 'Debug mode is on' in result.output
     assert 'Syncing' in result.output

另外一个关键字参数代入到 ``.invoke()`` 方法中会用来建立初始化语境对象。
例如，如果你想要运行一个固定终端宽度的测试，你可以使用下面关键字参数::

    runner = CliRunner()
    result = runner.invoke(cli, ['--debug', 'sync'], terminal_width=60)

File System Isolation
---------------------

对于基础的命令行工具来说，都是要与文件系统进行操作的，
 :meth:`CliRunner.isolated_filesystem` 方法的
用处就是配置一个空文件夹后，把当前工作目录改成这个空目录:

.. code-block:: python
   :caption: cat.py

   import click

   @click.command()
   @click.argument('f', type=click.File())
   def cat(f):
      click.echo(f.read())

.. code-block:: python
   :caption: test_cat.py

   from click.testing import CliRunner
   from cat import cat

   def test_cat():
      runner = CliRunner()
      with runner.isolated_filesystem():
         with open('hello.txt', 'w') as f:
             f.write('Hello World!')

         result = runner.invoke(cat, ['hello.txt'])
         assert result.exit_code == 0
         assert result.output == 'Hello World!\n'

输入流数据
-------------

测试打包器也可以用来为输入流数据（标准输入）提供输入数据。
对于测试用户提示来说是非常有用的，例如:

.. code-block:: python
   :caption: prompt.py

   import click

   @click.command()
   @click.option('--foo', prompt=True)
   def prompt(foo):
      click.echo('foo=%s' % foo)

.. code-block:: python
   :caption: test_prompt.py

   from click.testing import CliRunner
   from prompt import prompt

   def test_prompts():
      runner = CliRunner()
      result = runner.invoke(prompt, input='wau wau\n')
      assert not result.exception
      assert result.output == 'Foo: wau wau\nfoo=wau wau\n'

注意那个提示部分都要进行模拟，这样才把输入数据写到输出流数据中。
如果隐藏了输入内容的话，那么显然就不会出现输出流数据了。
