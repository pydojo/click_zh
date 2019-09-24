API
===

.. module:: click

本篇文档列出了全部公开类与函数的完整 API 文档内容。

装饰器
----------

.. autofunction:: command

.. autofunction:: group

.. autofunction:: argument

.. autofunction:: option

.. autofunction:: password_option

.. autofunction:: confirmation_option

.. autofunction:: version_option

.. autofunction:: help_option

.. autofunction:: pass_context

.. autofunction:: pass_obj

.. autofunction:: make_pass_decorator

工具集
---------

.. autofunction:: echo

.. autofunction:: echo_via_pager

.. autofunction:: prompt

.. autofunction:: confirm

.. autofunction:: progressbar

.. autofunction:: clear

.. autofunction:: style

.. autofunction:: unstyle

.. autofunction:: secho

.. autofunction:: edit

.. autofunction:: launch

.. autofunction:: getchar

.. autofunction:: pause

.. autofunction:: get_terminal_size

.. autofunction:: get_binary_stream

.. autofunction:: get_text_stream

.. autofunction:: open_file

.. autofunction:: get_app_dir

.. autofunction:: format_filename

命令
--------

.. autoclass:: BaseCommand
   :members:

.. autoclass:: Command
   :members:

.. autoclass:: MultiCommand
   :members:

.. autoclass:: Group
   :members:

.. autoclass:: CommandCollection
   :members:

参数形式
-----------

.. autoclass:: Parameter
   :members:

.. autoclass:: Option

.. autoclass:: Argument

语境
-------

.. autoclass:: Context
   :members:

.. autofunction:: get_current_context

数据类型
---------

.. autodata:: STRING

.. autodata:: INT

.. autodata:: FLOAT

.. autodata:: BOOL

.. autodata:: UUID

.. autodata:: UNPROCESSED

.. autoclass:: File

.. autoclass:: Path

.. autoclass:: Choice

.. autoclass:: IntRange

.. autoclass:: Tuple

.. autoclass:: ParamType
   :members:

例外
----------

.. autoexception:: ClickException

.. autoexception:: Abort

.. autoexception:: UsageError

.. autoexception:: BadParameter

.. autoexception:: FileError

.. autoexception:: NoSuchOption

.. autoexception:: BadOptionUsage

.. autoexception:: BadArgumentUsage

格式化
----------

.. autoclass:: HelpFormatter
   :members:

.. autofunction:: wrap_text

语法分析
-----------

.. autoclass:: OptionParser
   :members:

测试
-------

.. currentmodule:: click.testing

.. autoclass:: CliRunner
   :members:

.. autoclass:: Result
   :members:
