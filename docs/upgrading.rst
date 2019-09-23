升级更新的发布版本
===========================

Click 想向后兼容达到最高级，但有时候这种想法是没有完全的可能性。
在这种情况中，我们需要分解一下向后兼容文档内容，这样给你一些关于
如何升级或处理向后兼容的正确做法。

.. _upgrade-to-3.2:

升级到 3.2 版本
----------------

Click 3.2 版本已经执行了 2次变更，达到多命令都能被触发，
一次是变更到 2 版本，另一次是变更到 3 版本。并且结果超出预料。

语境触发
```````````````

Click 3.2 版本包含了一次修复 :meth:`Context.invoke` 方法，
当与其它命令一起工作时曾有 bug 出现。这个函数最初当想法是用来
触发其它命令，如果命令来自命令行的话，能代入到语境对象中，而不是
代入到函数里去。这种用法以前只文档化在一个地方，并且没有正确地解释
在 API 文档中。

关键问题是在 3.2 以前到版本中这种调用会出现意外行为::

    ctx.invoke(other_command, 'arg1', 'arg2')

这种现象永远不该出现，因为它不让 Click 操作在参数形式上。
根据这个原因，此模式永远不在进行文档化，并且这种病态想法
在正式发布前已经在 bug 修复中改变了，这样不会因为意外蔓延后
导致开发者们利用这种 bug 现象。

正确地触发上面命令会变成::

    ctx.invoke(other_command, name_of_arg1='arg1', name_of_arg2='arg2')

这就让我们修复默认情况下无法由此函数正确处理的问题。

多命令链条 API
`````````````````````````

Click 3 介绍了多命令链条特性。这需要做一次变更，那就是 Click 如何内部调度的问题。
不幸的是这次变更没有正确地实现，并且它出现了可能提供一种把会被触发的子命令信息告诉
给上级命令的 API 现象。

这种假设，不管如何，无法与过去提供的 API 保证一起工作。由于这种功能在 3.2 版本中
已经被移除了，所以会出现断裂情况。相反， :attr:`Context.invoked_subcommand`
 属性的意外断裂功能被恢复了。

如果你需要知道到底哪些命令会被触发，有许多不同的方法能够用这个来进行复制。
第一解决方案就是让子命令全部返回函数，然后在 :meth:`Context.resultcallback`
 方法里触发返回的函数。


.. _upgrade-to-2.0:

升级到 2.0 版本
----------------

Click 2.0 版本有一个断裂变更，就是参数形式回调信号。
在 2.0 以前的版本，回调是用 ``(ctx, value)`` 来触发的，
而此时由 ``(ctx, param, value)`` 来触发了。这种变更
是需要的，否则让复用回调变得太复杂了。

要容易过渡 Click 会依然接受老旧的回调。从 Click 3.0 开始，
它会启动一个警告给标准错误，从而鼓励你去升级版本来修复问题。

你想要同时支持 Click 1.0 和 Click 2.0 版本的话，你可以
写一个简单的装饰器调整这个信号::

    import click
    from functools import update_wrapper

    def compatcallback(f):
        # Click 1.0 does not have a version string stored, so we need to
        # use getattr here to be safe.
        if getattr(click, '__version__', '0.0') >= '2.0':
            return f
        return update_wrapper(lambda ctx, value: f(ctx, None, value), f)

使用这个助手后你就可以这样写了代码了::

    @compatcallback
    def callback(ctx, param, value):
        return value.upper()

注意，由于 Click 1.0 版本不会代入一个参数形式，那么此处的 `param` 参数
会是 `None` 值，所以一个兼容的回调是不能使用这个参数的。
