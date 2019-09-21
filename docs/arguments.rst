.. _arguments:

参数
=========

.. currentmodule:: click

参数工作起来与 :ref:`options <options>` 选项参考文档中类似，
但参数都是位置参数，不是可选项。由于句法的实质，它们也仅支持
可选项特性中的部分特性。 Click 也不会为你文档话参数，
并且想要你自己去根据 :ref:`document them manually <documenting-arguments>`
 参考文档来手动书写，这是为了避免帮助页面不好看。

基础参数
---------------

最基础的选择就是直接一个字符串作为参数值。
如果不提供类型的话，会使用默认值的类型，并且
如果不提供默认参数值的话，类型会假设为 :data:`STRING` 字符串数据类型。

示例:

.. click:基础参数示例::

    @click.command()
    @click.argument('filename')
    def touch(filename):
        """Print FILENAME."""
        click.echo(filename)

运行时会是这个样子:

.. click:run::

    invoke(touch, args=['foo.txt'])

多变参数
------------------

第二个最共性的参数版本就是多变参数，就是一个具体的 (或不限制) 被接受的参数数量。
这个数量可以用 ``nargs`` 参数来控制。如果设置成 ``-1`` 的话，既不限制参数数量。

参数值稍后会带入成一个元组。注意只有一个参数可以设置成 ``nargs=-1`` 情况，
因为它会吃掉所有的参数。

示例:

.. click:多变参数示例::

    @click.command()
    @click.argument('src', nargs=-1)
    @click.argument('dst', nargs=1)
    def copy(src, dst):
        """Move file SRC to DST."""
        for fn in src:
            click.echo('move %s to folder %s' % (fn, dst))

运行时可能会是如下样子:

.. click:run::

    invoke(copy, args=['foo.txt', 'bar.txt', 'my_folder'])

注意这个示例不是你如何写这类应用程序用的代码。
因为只是为了讲解如何使用，这里的文件都定义成字符串了。
文件名不应该是字符串！文件名存储在某种操作系统上的东西，
要写对文件的操作，更好的方法是看下面的部分内容。

.. admonition:: 注意非空多变参数

   如果使用过 ``argparse`` 库的话，
   你也许无法使用 ``nargs`` 设置成 ``+`` 来指明
   至少需要一个参数。

   这种支持是通过设置 ``required=True`` 来实现。
   不管如何做到的，不再使用这种设置了，如果你可以避免
   这点的话，我们相信脚本都是有责任恩典式地降级成非空操作，
   如果一个多变参数是空的话，也没问题。原因就是许多脚本常常
   与命令行输入的通配符来触发，如果通配符是空的话，脚本不应该
   出现错误信息。

.. _file-args:

文件参数
--------------

由于所有的示例都要与文件名一起工作，那么解释如何正确处理文件就是一件有意义的事情。
命令行工具都很有趣，如果用 Unix 风格的命令行与许多文件一起工作的话，
那么要能把 ``-`` 接受成一个特殊文件，这个文件就是指向标准输入/标准输出。

Click 通过 :class:`click.File` 类来支持这种文件类型，
会智能地为你处理这些文件。也会正确地处理 Unicode 和 字节，
不管 Python 是哪个版本，所以你的脚本会非常具有移植性。

示例:

.. click:文件参数示例::

    @click.command()
    @click.argument('input', type=click.File('rb'))
    @click.argument('output', type=click.File('wb'))
    def inout(input, output):
        """Copy contents of INPUT to OUTPUT."""
        while True:
            chunk = input.read(1024)
            if not chunk:
                break
            output.write(chunk)

这个例子做了什么:

.. click:run::

    with isolated_filesystem():
        invoke(inout, args=['-', 'hello.txt'], input=['hello'],
               terminate_input=True)
        invoke(inout, args=['hello.txt', '-'])

文件路径参数
-------------------

前面的例子中，文件都是立即被打开。
但如果我们只想用一个文件名呢？幼稚的方法是使用默认字符串参数类型。
不管如何做到的，记住 Click 是基于 Unicode 的，所以字符串会一直
是一种 Unicode 值。不幸的是，文件名可以是 Unicode 也可以是字节，
这要根据你使用的是什么操作系统来决定了。因为操作系统的缘故，
字符串类型还不足以解决问题。

相反，你应该使用 :class:`Path` 类，它可以自动处理这种歧义情况。
不仅根据系统来决定返回的是字节还是 Unicode 值，还能够做一些基础
检查，例如路径是否存在。

示例:

.. click:文件路径参数::

    @click.command()
    @click.argument('filename', type=click.Path(exists=True))
    def touch(filename):
        """Print FILENAME if the file exists."""
        click.echo(click.format_filename(filename))

示例代码做了什么:

.. click:run::

    with isolated_filesystem():
        with open('hello.txt', 'w') as f:
            f.write('Hello World!\n')
        invoke(touch, args=['hello.txt'])
        println()
        invoke(touch, args=['missing.txt'])


文件安全打开
-------------------

在 :class:`FileType` 类上有一个问题需要处理，
那就是什么时候打开一个文件。默认行为是智能化。
这里的智能化是什么意思？就是会打开 标准输入/标准输出
 后立即打开文件进行读取。当一个文件无法开始时，
这样做会给用户直接反馈，但这种智能化只为第一次写
一项 IO 操作来打开文件，而 IO 操作是通过把文件
打包进一个特殊的打包器来执行。

这种行为可以通过代入 ``lazy=True`` 或 ``lazy=False`` 给
构造器来控制。如果文件采用懒蛋模式打开的话，会让第一次 IO 操作
失败，抛出一个 :exc:`FileError` 例外错误。

由于为写而打开文件典型都是立即打开一个空文件，
如果开发者要的就是这种行为，那么懒蛋模式应该被禁用。

开启懒蛋模式对避免资源处理混乱是非常有用的。如果一个文件
以懒蛋模式打开的话，会接收到一个 ``close_intelligently`` 方法，
这个方法可以帮助弄清楚是否需要关闭文件。对于参数来说这是不需要的，
但可以用 :func:`prompt` 函数来手动提醒，因为你不知道一个流数据
是否打开了，就像标准输出就是一种流数据 (都是一直提前打开) 
或者是否需要关闭一个真实的文件。

从 Click 2.0 版本开始，通过代入 ``atomic=True`` 也可以
以原子价模式打开文件。原子价模式中，所有写入都会进入相同文件夹
中的各个文件里，然后完成写操作，文件会被移到最初的位置。
如果一个常规由其它用户读取的文件被修改时，这是有用的技术。

环境变量
---------------------

像可选项一样，参数也可以从一个环境变量获得值。
与可选项不同，不管如何做到的，参数只支持明确的命名环境变量。

示例用法:

.. click:环境变量示例::

    @click.command()
    @click.argument('src', envvar='SRC', type=click.File('r'))
    def echo(src):
        """Print value of SRC environment variable."""
        click.echo(src.read())

命令行允许的情况:

.. click:run::

    with isolated_filesystem():
        with open('hello.txt', 'w') as f:
            f.write('Hello World!')
        invoke(echo, env={'SRC': 'hello.txt'})

在这种情况下，也可以是不同环境变量的一种列表形式，会选择列表中的第一项。

通用中，这个特性不建议使用，因为会导致用户不太明白。

类似选项的参数
---------------------

有时候你想要处理一些看起来像选项的参数。
对于这种情况，想象一下，你有一个文件名叫 ``-foo.txt``
 如果你把这个作为参数来代入的话， Click 会把它处理成一个选项。

要解决这种情况， Click 确实做了任何一种 POSIX 风格的命令行脚本所做的事情，
然后就可以把字符串 ``--`` 接受成选项和参数的分隔符。
在 ``--`` 符号后的所有参数都会接收成参数。

示例用法:

.. click:类似选项的参数示例::

    @click.command()
    @click.argument('files', nargs=-1, type=click.Path())
    def touch(files):
        """Print all FILES file names."""
        for filename in files:
            click.echo(filename)

运行时的样子:

.. click:run::

    invoke(touch, ['--', '-foo.txt', 'bar.txt'])

如果你不喜欢 ``--`` 描述符的话，你可以设置
 ignore_unknown_options 参数为 True 来避免检查位置选项:

.. click:忽略双减号描述符示例::

    @click.command(context_settings={"ignore_unknown_options": True})
    @click.argument('files', nargs=-1, type=click.Path())
    def touch(files):
        """Print all FILES file names."""
        for filename in files:
            click.echo(filename)

运行时会是:

.. click:run::

    invoke(touch, ['-foo.txt', 'bar.txt'])

