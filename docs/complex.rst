.. _complex-guide:

多层化应用程序
====================

.. currentmodule:: click

Click 是设计来帮助建立多层化和简单的 CLI 工具。
不管如何做到的，自身设计的威力在于具有任意嵌入到系统中的能力。
对于这种情况来说，如果你曾用过 Django 的话，你会认识到它提供
了一个命令行工具，而且 Celery 也有命令行工具。
当使用 Celery 与 Django 结合时，它们俩的命令行工具需要互动，
而且是横跨了不同的配置情况。

在理论世界中，分别用 Click 写这 2 个命令行工具，才能解决互动问题，
因为通过把一个嵌入到另一个中就可以了。对于这种情况，网络框架也会加载
许多命令给消息列队框架。

基础概念
--------------

要理解这是如何工作的，你需要理解 2 个概念：语境和定期调用。

语境
````````

不管什么时候，一个 Click 命令被执行时，一个 :class:`Context` 类实例就会建立，
它是用来保存这种特殊回应状态的。语境可以记住分析过的参数，是哪个命令建立的，
哪些资源需要在函数结束时被释放，然后继续前行。它也可以有选择的保存一个定义完的
应用程序对象。

语境实例对象建立了一个链条列表，直到语境对象到达顶层。
每个语境是链接到一个父语境上。这样允许一个命令可以工作
在另一个命令下面，然后把自身信息存储在语境对象里，这样
就不用担心父命令的状态改变。

由于父命令数据是可用的，不管如何做到的，如果需要是可以导航到父命令。

大部分时候，你不需要查看语境对象，但当书写更加多层化的应用程序时，
手动查看很方便。接下来就需要我们理解下一个概念了。

定期调用
``````````````````

当一个 Click 命令回调被执行时，都会把非隐藏参数作为关键字参数代入其中。
尤其是缺少语境时。不管如何做到的，一个回调可选地代入语境对象中，通过
使用 :func:`pass_context` 函数来标记自己。

所以，如果你不知道是否应该接收语境的话，你如何触发一个命令回调呢？
答案就是语境自身提供了一个辅助函数 (:meth:`Context.invoke`) 
该方法可以为你来实现。它接收回调作为第一个参数后正确地触发函数。

建立一个 Git Clone
--------------------

在本示例中，我们想要建立一个命令行工具，它重新组装了一个版本控制系统。
就像 Git 一样的系统，常常提供一种一个接着一个的命令方式，一个命令
接收一些参数和配置后，再用额外的子命令来实现其它事情。在 Linux 系统
中管道技术也是如此。

根命令
````````````````

在顶层，我们需要一个群组来保存所有我们的命令。
在这种情况下，我们使用基础的 :func:`click.group` 函数，
它允许我们把它下面的其它 Click 命令注册在一起。

对于这种命令，我们也想要接收一些参数，这些参数是用来配置我们工具的状态:

.. click:父命令示例::

    import os
    import click


    class Repo(object):
        def __init__(self, home=None, debug=False):
            self.home = os.path.abspath(home or '.')
            self.debug = debug


    @click.group()
    @click.option('--repo-home', envvar='REPO_HOME', default='.repo')
    @click.option('--debug/--no-debug', default=False,
                  envvar='REPO_DEBUG')
    @click.pass_context
    def cli(ctx, repo_home, debug):
        ctx.obj = Repo(repo_home, debug)


我们来理解一下这些代码做了什么。我们建立了一个群组命令，它可以有许多子命令。
当群组命令触发时，它会建立一个 ``Repo`` 类的实例。这个实例是用来存储
我们命令行工具的状态。在这种情况下，类实例只记住了一些参数，但在这点上
类实例也可以启动加载配置文件，等等工作。

这个状态对象稍后被语境记忆成 :attr:`~Context.obj` 属性。
这是一个特殊属性，其中记住的许多命令都视为所需要代入到子命令中去。

为了这个能工作，我们需要先用 :func:`pass_context` 函数来装饰我们的函数，
否则语境对象会藏起来无法被我们找到。

第一个子命令
```````````````````````

我们先增加第一个子命令到父命令里，那就是克隆命令:

.. click:子命令示例::

    @cli.command()
    @click.argument('src')
    @click.argument('dest', required=False)
    def clone(src, dest):
        pass

我们此时有了一个 clone 命令，但我们如何访问仓库呢？
如你所想，一种方法是使用 :func:`pass_context` 函数来
做我们的回调同时获得语境代入到我们记住的仓库上。
不管如何做到的，这里的这种装饰器第二个版本调用了
 :func:`pass_obj` 函数，它只代入已保存的对象
  (在我们的例子中就是 repo):

.. click:访问仓库示例::

    @cli.command()
    @click.argument('src')
    @click.argument('dest', required=False)
    @click.pass_obj
    def clone(repo, src, dest):
        pass

插入命令
````````````````````

这里要说的与我们上面建立的特殊程序无关，但对于插入式系统来说这也是非常好的支持。
想象一下这种情况，对于我们的版本控制系统有一种超级插件，版本控制系需要大量配置后
想要把自身的配置存储成 :attr:`~Context.obj` 属性。
如果我们稍后接着用另一个命令的话，我们会得到所有插件的配置，而不是 repo 对象。

显而易见治疗这种症状的一个方法就是，在插件中把一份参考存储到 repo 对象里，
但后面的一个命令需要知道所跟着的下面这个插件。

这里有一种更好的系统，通过获得语境连接本性的优势所建立的系统。
我们知道插件语境是要连接到我们建立的 repo 语境。因此，我们
可以启动一次搜索最后一层，其中有语境存储的一个 repo 对象。

内置支持这种功能是由 :func:`make_pass_decorator` 工厂函数提供了，
它会为我们建立许多装饰器来找到那些对象 (它内部地调用
 :meth:`Context.find_object` 方法)。在我们的案例中，我们知道想要
找到最近的 ``Repo`` 类对象，所以我们要给它一个装饰器:

.. click:语境连接示例::

    pass_repo = click.make_pass_decorator(Repo)

如果我们现在使用 ``pass_repo`` 来代替 ``pass_obj`` 的话，我们会
一直获得一个 repo 而不是其它什么东西:

.. click:用语境连接访问仓库示例::

    @cli.command()
    @click.argument('src')
    @click.argument('dest', required=False)
    @pass_repo
    def clone(repo, src, dest):
        pass

确保对象建立
````````````````````````

上面的例子只在用一个外部命令建立一个 ``Repo`` 对象时有效，
并且存储到语境中。对一些更高级的用例来说，就会有问题。
 :func:`make_pass_decorator` 函数的默认行为是调用
 :meth:`Context.find_object` 方法，这个方法回去找到对象。
如果这个方法无法找到对象的话， :meth:`make_pass_decorator` 
方法会抛出一个例外错误。另外一种行为是使用
 :meth:`Context.ensure_object` 确保对象方法来找对象，
如果确保对象方法找不到对象的话，会建立一个对象并存储到最近的语境里。
这种行为也可以为 :func:`make_pass_decorator` 函数开启，通过
把 ``ensure=True`` 参数代入到函数构造器中:

.. click:确保对象方法找对象示例::

    pass_repo = click.make_pass_decorator(Repo, ensure=True)

在此时的情况中，如果找不到对象的话，最近的语境会得到一个建立的对象。
这也许会替换以前此处存在的对象。在这种情况下，命令依然是可以执行的，
即使外部命令没运行。要想让这种方法生效，对象类型需要有一个无参构造器。

如此就可以独立运行了:

.. click:example::

    @click.command()
    @pass_repo
    def cp(repo):
        click.echo(isinstance(repo, Repo))

运行时看起来像这样:

.. click:run::

    invoke(cp, [])
