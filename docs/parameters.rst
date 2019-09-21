参数形式
==========

.. currentmodule:: click

对于脚本来说 Click 支持两种参数类型：可选项与参数。
通用中在命令后脚本作者们使用时也会有一些含糊，所以
本篇文档就会来一次二者之间区别的快速概览。顾名思义，
可选项就是可以用可不用，而参数作为选择时都是含有原因的，
它们二者之间区别在于它们都具备可选择时是如何被限制的。

要帮助你区分可选项和参数之间的不同，建议就是使用参数来决定
使用的子命令，或使用参数来作为输入文件名、网址这些主要值，
然后其它的值都用可选项来实现。

区别
-----------

参数可以实现较少的选择。如下这些特性是用在可选项上:

*   自动提示缺少输入内容
*   作为旗语 (布尔值或其它类似值)
*   可选项值可以从环境变量中获得，参数值不能来自环境变量。
*   可选项都要完整地文档化在帮助页面中，参数不需要。阅读
    (:ref:`this is intentional <documenting-arguments>` 参考文档
    了解太具体的参数需要自动化文档)

另一方面参数不同于可选项的是，参数可以接收任意数量的参数。
可选项要严格只接收固定数量的参数 (默认是 1 个参数)。

参数类型
---------------

参数形式可以是不同的类型。参数类型具有不同的行为，
并且有些类型支持盒外技术:

``str`` / :data:`click.STRING`:
    默认参数类型，指明使用 unicode 字符串。

``int`` / :data:`click.INT`:
    只接受整数的一种参数形式。

``float`` / :data:`click.FLOAT`:
    只接受浮点数的一种参数形式。

``bool`` / :data:`click.BOOL`:
    只接受布尔值的一种参数形式。自动用于布尔旗语。
    如果使用时含有字符串值 ``1``, ``yes``, ``y``, ``t``
    和 ``true`` 时会转换成 `True` 以及
     ``0``, ``no``, ``n``, ``f`` 和 ``false``
    转换成 `False` 结果。

:data:`click.UUID`:
    只接受 UUID 值的一种参数形式。不会自动去猜，
    而表示成 :class:`uuid.UUID` 类。

.. autoclass:: File
   :noindex:

.. autoclass:: Path
   :noindex:

.. autoclass:: Choice
   :noindex:

.. autoclass:: IntRange
   :noindex:

.. autoclass:: FloatRange
  :noindex:

.. autoclass:: DateTime
   :noindex:

自定义参数类型可以通过 :class:`click.ParamType` 的子类来实现。
对于简单情况来说，代入一个含有 `ValueError` 例外错误的 Python 
函数也可以，但不鼓励这样做。

.. _parameter_names:

参数形式的名字
---------------

参数形式 (包括可选项和参数) 接收一定数量的位置参数时，
位置参数都要代入到命令函数中作为函数参数。每个带有1个
减号的字符串是一种短参数形式；带有2个减号的是长参数形式。

如果加入了不带减号的字符串，这个字符串会变成内部参数形式的名字，
这个名字也用作变量名。

如果一个参数形式的所有名字都含有减号的话，内部名字会自动
通过获得长参数名生成，然后把所有的减号都转换成下划线。

内部名字是转换成全小写形式。

名字示例:

* 对于含有 ``('-f', '--foo-bar')`` 的一个选项，参数形式的名字就是 `foo_bar`
* 对于含有 ``('-x',)`` 的一个选项，参数形式的名字是 `x`
* 对于含有 ``('-f', '--filename', 'dest')`` 的一个选项，参数形式的名字是  `dest`
* 对于含有 ``('--CamelCaseOption',)`` 的一个选项，参数形式的名字是 `camelcaseoption`.
* 对于含有 ``(`foogle`)`` 的一个参数，参数形式的名字是 `foogle` 。要在帮助文本中
  提供一种不一样的适合人阅读的名字，阅读一下 :ref:`doc-meta-variables` 参考文档。

实现自定义类型
-------------------------

要实现一个自定义参数类型，你需要 :class:`ParamType` 类的子类。
覆写 :meth:`~ParamType.convert` 方法来把一个字符串值转换成正确的类型。

下面代码实现了一个整数类型，该整数类型接收十六进制和八进制数字
作为正常整数类型，然后转换成常规的整数值。

.. code-block:: python

    import click

    class BasedIntParamType(click.ParamType):
        name = "integer"

        def convert(self, value, param, ctx):
            try:
                if value[:2].lower() == "0x":
                    return int(value[2:], 16)
                elif value[:1] == "0":
                    return int(value, 8)
                return int(value, 10)
            except TypeError:
                self.fail(
                    "expected string for int() conversion, got "
                    f"{value!r} of type {type(value).__name__}",
                    param,
                    ctx,
                )
            except ValueError:
                self.fail(f"{value!r} is not a valid integer", param, ctx)

    BASED_INT = BasedIntParamType()

其中 :attr:`~ParamType.name` 属性是可选的，并且用来提供给文档。
如果转换失败的话，会调用 :meth:`~ParamType.fail` 方法。其中
在有的情况里 ``param`` 和 ``ctx`` 参数可能是 ``None`` 值，
例如提示环境里。
