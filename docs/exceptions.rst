例外处理
==================

.. currentmodule:: click

Click 内部使用许多例外来发送各种错误情况信号，
这些错误情况也许都是由程序用户导致的。主要情况
都可能是不正确的使用。

在什么地方进行错误处理？
-------------------------

Click 的主要错误处理是在 :meth:`BaseCommand.main` 方法中。
其中处理了所有 :exc:`ClickException` 例外类型的子类，同时也
处理标准的 :exc:`EOFError` 例外和 :exc:`KeyboardInterrupt` 例外。
这 2 个标准例外都是内部翻译成一个 :exc:`Abort` 例外。

所应用的逻辑如下:

1.  如果一个 :exc:`EOFError` 例外，或者一个 :exc:`KeyboardInterrupt` 例外发生的话，
    二次抛出成 :exc:`Abort` 例外类型。
2.  如果一个 :exc:`ClickException` 抛出来的话，会触发 
    :meth:`ClickException.show` 方法来显示，然后用 
    :attr:`ClickException.exit_code` 属性来退出程序。
3.  如果一个 :exc:`Abort` 例外抛出的话，把 ``Aborted!``
     字符串输出给标准错误，然后用退出代号 ``1`` 来退出程序。
4.  如果没有例外抛出的话，要使用退出代号 ``0`` 来退出程序。

如果我不想那样做怎么办？
--------------------------

通用中，你自己总会有选择触发 :meth:`invoke` 方法。
例如，如果你有一个 :class:`Command` 类实例的话，
你可以手动触发它::

    ctx = command.make_context('command-name', ['args', 'go', 'here'])
    with ctx:
        result = command.invoke(ctx)

在这种情况中，例外都不会被处理，并且出现的情况如你所愿。

从 Click 3.0 版本开始，你也可以使用 :meth:`Command.main` 方法，
但禁用单独模式会发生两件事: 禁用例外处理和
在结尾处隐含禁用 :meth:`sys.exit` 方法。

所以你可以这样做::

    command.main(['command-name', 'args', 'go', 'here'],
                 standalone_mode=False)

哪个例外存在着？
-----------------------

Click 有 2 个例外基础: :exc:`ClickException` 例外是为了
 Click 要发送给用户信号的所有例外而被抛出的，另一个 :exc:`Abort`
 例外是用来指导 Click 终止执行的例外类型。

一个 :exc:`ClickException` 例外有一个 :meth:`~ClickException.show` 方法，
该方法可以把一个错误消息翻译给标准错误，或者翻译给给出的一个文件对象。
如果你想要使用自己的例外来做一些事情，查看 API 文档中关于这方面的内容。

存在着下面这些子类例外:

*   :exc:`UsageError` 例外类型是告诉用户出现某种错误。
*   :exc:`BadParameter` 例外类型是告诉用户一个具体的参数形式出错了。
    这个常常在 Click 内部进行处理，并且参数中尽可能包含额外信息。例如，
    如果这种例外从一个回调跑出来的话， Click 会尽可能用参数形式名来作为
    其中的参数。
*   :exc:`FileError` 例外是通过 :exc:`FileType` 抛出来的一个错误，
    当然是在 Click 打开文件操作中遇到问题时产生的。
