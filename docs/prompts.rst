用户输入提示
==================

.. currentmodule:: click

Click 支持两种位置上的提示。第一种是自动提示在参数形式处理发生的地方，
第二种就是稍后单独做出提示的地方。

这可以用 :func:`prompt` 函数来实现，它会验证输入的类型，
或根据 :func:`confirm` 函数来验证输入，确认函数是以 (yes/no) 做验证。

可选项提示
--------------

可选项使用提示都是集成在可选项接口里的。阅读
 :ref:`option-prompting` 参考文档了解更多信息。内部来说，它会自动
根据需要调用 :func:`prompt` 提示函数，或 :func:`confirm` 确认函数。

输入提示
-------------

要手动提供用户输入提示，可以使用 :func:`prompt` 提示函数。
默认情况下，它接收任何一个 Unicode 字符串，但你可以要求其它数据类型。
例如，你可以要求输入是一个合法整数::

    value = click.prompt('Please enter a valid integer', type=int)

另外，如果提供一个默认值的话，数据类型的确定是自动检测的。
例如，只接受浮点数::

    value = click.prompt('Please enter a number', default=42.0)

确认提示
--------------------

要询问用户是否想要继续一项动作的话， :func:`confirm` 确认函数少不了。
默认情况下，它把提示的结果返回成一个布尔值::

    if click.confirm('Do you want to continue?'):
        click.echo('Well done!')

也有让确认函数自动终止程序的执行选择，那就是确认函数不返回 ``True`` 值::

    click.confirm('Do you want to continue?', abort=True)
