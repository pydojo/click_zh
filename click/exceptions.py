from ._compat import PY2, filename_to_ui, get_text_stderr
from .utils import echo


def _join_param_hints(param_hint):
    if isinstance(param_hint, (tuple, list)):
        return ' / '.join('"%s"' % x for x in param_hint)
    return param_hint


class ClickException(Exception):
    """Click 可以处理的一个列外，并且显示给用户。"""

    #: The exit code for this exception
    exit_code = 1

    def __init__(self, message):
        ctor_msg = message
        if PY2:
            if ctor_msg is not None:
                ctor_msg = ctor_msg.encode('utf-8')
        Exception.__init__(self, ctor_msg)
        self.message = message

    def format_message(self):
        return self.message

    def __str__(self):
        return self.message

    if PY2:
        __unicode__ = __str__

        def __str__(self):
            return self.message.encode('utf-8')

    def show(self, file=None):
        if file is None:
            file = get_text_stderr()
        echo('Error: %s' % self.format_message(), file=file)


class UsageError(ClickException):
    """一个内部例外，发送一个用法错误信号。
    典型来说，终止任何下一步处理。

    :param message: 要显示的错误消息。
    :param ctx: 导致这个错误的语境。 Click 会在某些环境中自动填入语境。
    """
    exit_code = 2

    def __init__(self, message, ctx=None):
        ClickException.__init__(self, message)
        self.ctx = ctx
        self.cmd = self.ctx and self.ctx.command or None

    def show(self, file=None):
        if file is None:
            file = get_text_stderr()
        color = None
        hint = ''
        if (self.cmd is not None and
                self.cmd.get_help_option(self.ctx) is not None):
            hint = ('Try "%s %s" for help.\n'
                    % (self.ctx.command_path, self.ctx.help_option_names[0]))
        if self.ctx is not None:
            color = self.ctx.color
            echo(self.ctx.get_usage() + '\n%s' % hint, file=file, color=color)
        echo('Error: %s' % self.format_message(), file=file, color=color)


class BadParameter(UsageError):
    """一个例外，能够为败坏的参数形式格式化成一种标准化过的错误消息。
    当从一个回调函数或类型抛出来的时候是有用的，因为 Click 会把语境的
    信息附在其后 (例如，是哪个败坏的参数形式)。

    .. versionadded:: 2.0

    :param param: 会导致这个错误的参数形式对象。这个可以不填写，
                  并且可能的话 Click 会把这个信息追加到自身上。
    :param param_hint: 作为参数形式名显示的一个字符串。
                       在自定义验证应该发生的环境中，
                       这个可以用作另一种形式给 `param` 。
                       如果是一个字符串的话，就会用这个字符串，
                       如果是一个列表的话，每项元素会被引用后分离开来。
    """

    def __init__(self, message, ctx=None, param=None,
                 param_hint=None):
        UsageError.__init__(self, message, ctx)
        self.param = param
        self.param_hint = param_hint

    def format_message(self):
        if self.param_hint is not None:
            param_hint = self.param_hint
        elif self.param is not None:
            param_hint = self.param.get_error_hint(self.ctx)
        else:
            return 'Invalid value: %s' % self.message
        param_hint = _join_param_hints(param_hint)

        return 'Invalid value for %s: %s' % (param_hint, self.message)


class MissingParameter(BadParameter):
    """Raised if click required an option or argument but it was not
    provided when invoking the script.

    .. versionadded:: 4.0

    :param param_type: a string that indicates the type of the parameter.
                       The default is to inherit the parameter type from
                       the given `param`.  Valid values are ``'parameter'``,
                       ``'option'`` or ``'argument'``.
    """

    def __init__(self, message=None, ctx=None, param=None,
                 param_hint=None, param_type=None):
        BadParameter.__init__(self, message, ctx, param, param_hint)
        self.param_type = param_type

    def format_message(self):
        if self.param_hint is not None:
            param_hint = self.param_hint
        elif self.param is not None:
            param_hint = self.param.get_error_hint(self.ctx)
        else:
            param_hint = None
        param_hint = _join_param_hints(param_hint)

        param_type = self.param_type
        if param_type is None and self.param is not None:
            param_type = self.param.param_type_name

        msg = self.message
        if self.param is not None:
            msg_extra = self.param.type.get_missing_message(self.param)
            if msg_extra:
                if msg:
                    msg += '.  ' + msg_extra
                else:
                    msg = msg_extra

        return 'Missing %s%s%s%s' % (
            param_type,
            param_hint and ' %s' % param_hint or '',
            msg and '.  ' or '.',
            msg or '',
        )


class NoSuchOption(UsageError):
    """如果 click 要处理一个可选项的话，可选项不存在就会抛出这个例外。

    .. versionadded:: 4.0
    """

    def __init__(self, option_name, message=None, possibilities=None,
                 ctx=None):
        if message is None:
            message = 'no such option: %s' % option_name
        UsageError.__init__(self, message, ctx)
        self.option_name = option_name
        self.possibilities = possibilities

    def format_message(self):
        bits = [self.message]
        if self.possibilities:
            if len(self.possibilities) == 1:
                bits.append('Did you mean %s?' % self.possibilities[0])
            else:
                possibilities = sorted(self.possibilities)
                bits.append('(Possible options: %s)' % ', '.join(possibilities))
        return '  '.join(bits)


class BadOptionUsage(UsageError):
    """如果通用中提供了一个可选项，却使用错误的话，会抛出这个例外。
    例如，如果对一个可选项的参数数量用错了，就会抛出这个例外。

    .. versionadded:: 4.0

    :param option_name: 不正确使用的可选项名字。
    """

    def __init__(self, option_name, message, ctx=None):
        UsageError.__init__(self, message, ctx)
        self.option_name = option_name


class BadArgumentUsage(UsageError):
    """如果通用中提供了一个参数，却使用错误，就会抛出这个例外。
    例如，对一个参数的值数量用错了，就会抛出这个例外。

    .. versionadded:: 6.0
    """

    def __init__(self, message, ctx=None):
        UsageError.__init__(self, message, ctx)


class FileError(ClickException):
    """如果无法打开一个文件的话，会抛出这个例外。"""

    def __init__(self, filename, hint=None):
        ui_filename = filename_to_ui(filename)
        if hint is None:
            hint = 'unknown error'
        ClickException.__init__(self, hint)
        self.ui_filename = ui_filename
        self.filename = filename

    def format_message(self):
        return 'Could not open file %s: %s' % (self.ui_filename, self.message)


class Abort(RuntimeError):
    """一个内部发送例外信号的例外，告诉 Click 终止运行。"""


class Exit(RuntimeError):
    """An exception that indicates that the application should exit with some
    status code.

    :param code: the status code to exit with.
    """
    def __init__(self, code=0):
        self.exit_code = code
