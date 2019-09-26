import os
import stat
from datetime import datetime

from ._compat import open_stream, text_type, filename_to_ui, \
    get_filesystem_encoding, get_streerror, _get_argv_encoding, PY2
from .exceptions import BadParameter
from .utils import safecall, LazyFile


class ParamType(object):
    """帮助通过类型来转换值。如下是合法类型:

    *   需要一个名字
    *   需要通过 None 来传递未变更
    *   需要从一个字符串来进行转换
    *   需要通过未变更来转换自身结果类型
        (例如: 需要被注释)
    *   需要能够处理 param 和语境为 `None` 情况。
        这可以是当对象与提示输入一起使用的情况。
    """
    is_composite = False

    #: the descriptive name of this type
    name = None

    #: if a list of this type is expected and the value is pulled from a
    #: string environment variable, this is what splits it up.  `None`
    #: means any whitespace.  For all parameters the general rule is that
    #: whitespace splits them up.  The exception are paths and files which
    #: are split by ``os.path.pathsep`` by default (":" on Unix and ";" on
    #: Windows).
    envvar_list_splitter = None

    def __call__(self, value, param=None, ctx=None):
        if value is not None:
            return self.convert(value, param, ctx)

    def get_metavar(self, param):
        """Returns the metavar default for this param if it provides one."""

    def get_missing_message(self, param):
        """Optionally might return extra information about a missing
        parameter.

        .. versionadded:: 2.0
        """

    def convert(self, value, param, ctx):
        """Converts the value.  This is not invoked for values that are
        `None` (the missing value).
        """
        return value

    def split_envvar_value(self, rv):
        """Given a value from an environment variable this splits it up
        into small chunks depending on the defined envvar list splitter.

        If the splitter is set to `None`, which means that whitespace splits,
        then leading and trailing whitespace is ignored.  Otherwise, leading
        and trailing splitters usually lead to empty items being included.
        """
        return (rv or '').split(self.envvar_list_splitter)

    def fail(self, message, param=None, ctx=None):
        """Helper method to fail with an invalid value message."""
        raise BadParameter(message, ctx=ctx, param=param)


class CompositeParamType(ParamType):
    is_composite = True

    @property
    def arity(self):
        raise NotImplementedError()


class FuncParamType(ParamType):

    def __init__(self, func):
        self.name = func.__name__
        self.func = func

    def convert(self, value, param, ctx):
        try:
            return self.func(value)
        except ValueError:
            try:
                value = text_type(value)
            except UnicodeError:
                value = str(value).decode('utf-8', 'replace')
            self.fail(value, param, ctx)


class UnprocessedParamType(ParamType):
    name = 'text'

    def convert(self, value, param, ctx):
        return value

    def __repr__(self):
        return 'UNPROCESSED'


class StringParamType(ParamType):
    name = 'text'

    def convert(self, value, param, ctx):
        if isinstance(value, bytes):
            enc = _get_argv_encoding()
            try:
                value = value.decode(enc)
            except UnicodeError:
                fs_enc = get_filesystem_encoding()
                if fs_enc != enc:
                    try:
                        value = value.decode(fs_enc)
                    except UnicodeError:
                        value = value.decode('utf-8', 'replace')
            return value
        return value

    def __repr__(self):
        return 'STRING'


class Choice(ParamType):
    """选择类型允许一个值经过所支持的固定值集合做检查。
    所有哪些能用的值都要用字符串。

    你应该只采用列表或元组来作为代入的候选清单。
    其它可迭代对象 (例如生成器对象) 会导致意外结果。

    查看 :ref:`choice-opts` 选择可选值文档中的示例。

    :param case_sensitive: 设置成 `False` 会开启大小写敏感功能。
        默认值是 `True` 效果是脱敏。
    """

    name = 'choice'

    def __init__(self, choices, case_sensitive=True):
        self.choices = choices
        self.case_sensitive = case_sensitive

    def get_metavar(self, param):
        return '[%s]' % '|'.join(self.choices)

    def get_missing_message(self, param):
        return 'Choose from:\n\t%s.' % ',\n\t'.join(self.choices)

    def convert(self, value, param, ctx):
        # Exact match
        if value in self.choices:
            return value

        # Match through normalization and case sensitivity
        # first do token_normalize_func, then lowercase
        # preserve original `value` to produce an accurate message in
        # `self.fail`
        normed_value = value
        normed_choices = self.choices

        if ctx is not None and \
           ctx.token_normalize_func is not None:
            normed_value = ctx.token_normalize_func(value)
            normed_choices = [ctx.token_normalize_func(choice) for choice in
                              self.choices]

        if not self.case_sensitive:
            normed_value = normed_value.lower()
            normed_choices = [choice.lower() for choice in normed_choices]

        if normed_value in normed_choices:
            return normed_value

        self.fail('invalid choice: %s. (choose from %s)' %
                  (value, ', '.join(self.choices)), param, ctx)

    def __repr__(self):
        return 'Choice(%r)' % list(self.choices)


class DateTime(ParamType):
    """The DateTime type converts date strings into `datetime` objects.

    The format strings which are checked are configurable, but default to some
    common (non-timezone aware) ISO 8601 formats.

    When specifying *DateTime* formats, you should only pass a list or a tuple.
    Other iterables, like generators, may lead to surprising results.

    The format strings are processed using ``datetime.strptime``, and this
    consequently defines the format strings which are allowed.

    Parsing is tried using each format, in order, and the first format which
    parses successfully is used.

    :param formats: A list or tuple of date format strings, in the order in
                    which they should be tried. Defaults to
                    ``'%Y-%m-%d'``, ``'%Y-%m-%dT%H:%M:%S'``,
                    ``'%Y-%m-%d %H:%M:%S'``.
    """
    name = 'datetime'

    def __init__(self, formats=None):
        self.formats = formats or [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S'
        ]

    def get_metavar(self, param):
        return '[{}]'.format('|'.join(self.formats))

    def _try_to_convert_date(self, value, format):
        try:
            return datetime.strptime(value, format)
        except ValueError:
            return None

    def convert(self, value, param, ctx):
        # Exact match
        for format in self.formats:
            dtime = self._try_to_convert_date(value, format)
            if dtime:
                return dtime

        self.fail(
            'invalid datetime format: {}. (choose from {})'.format(
                value, ', '.join(self.formats)))

    def __repr__(self):
        return 'DateTime'


class IntParamType(ParamType):
    name = 'integer'

    def convert(self, value, param, ctx):
        try:
            return int(value)
        except (ValueError, UnicodeError):
            self.fail('%s is not a valid integer' % value, param, ctx)

    def __repr__(self):
        return 'INT'


class IntRange(IntParamType):
    """一种类似 :data:`click.INT` 的数据类型，但把值限制在一个范围里。
    如果值超出范围的话，默认行为会失败，但也可以把超出范围但值固定成边缘值。

    阅读 :ref:`ranges` 参考文档了解一个示例。
    """
    name = 'integer range'

    def __init__(self, min=None, max=None, clamp=False):
        self.min = min
        self.max = max
        self.clamp = clamp

    def convert(self, value, param, ctx):
        rv = IntParamType.convert(self, value, param, ctx)
        if self.clamp:
            if self.min is not None and rv < self.min:
                return self.min
            if self.max is not None and rv > self.max:
                return self.max
        if self.min is not None and rv < self.min or \
           self.max is not None and rv > self.max:
            if self.min is None:
                self.fail('%s is bigger than the maximum valid value '
                          '%s.' % (rv, self.max), param, ctx)
            elif self.max is None:
                self.fail('%s is smaller than the minimum valid value '
                          '%s.' % (rv, self.min), param, ctx)
            else:
                self.fail('%s is not in the valid range of %s to %s.'
                          % (rv, self.min, self.max), param, ctx)
        return rv

    def __repr__(self):
        return 'IntRange(%r, %r)' % (self.min, self.max)


class FloatParamType(ParamType):
    name = 'float'

    def convert(self, value, param, ctx):
        try:
            return float(value)
        except (UnicodeError, ValueError):
            self.fail('%s is not a valid floating point value' %
                      value, param, ctx)

    def __repr__(self):
        return 'FLOAT'


class FloatRange(FloatParamType):
    """一种参数形式，工作起来类似 :data:`click.FLOAT` 但把值限制在一个范围里。
    如果值超出了范围的话，默认行为会失败，但也可以默默地把超出范围的值设定成边缘值。

    阅读 :ref:`ranges` 了解示例。
    """
    name = 'float range'

    def __init__(self, min=None, max=None, clamp=False):
        self.min = min
        self.max = max
        self.clamp = clamp

    def convert(self, value, param, ctx):
        rv = FloatParamType.convert(self, value, param, ctx)
        if self.clamp:
            if self.min is not None and rv < self.min:
                return self.min
            if self.max is not None and rv > self.max:
                return self.max
        if self.min is not None and rv < self.min or \
           self.max is not None and rv > self.max:
            if self.min is None:
                self.fail('%s is bigger than the maximum valid value '
                          '%s.' % (rv, self.max), param, ctx)
            elif self.max is None:
                self.fail('%s is smaller than the minimum valid value '
                          '%s.' % (rv, self.min), param, ctx)
            else:
                self.fail('%s is not in the valid range of %s to %s.'
                          % (rv, self.min, self.max), param, ctx)
        return rv

    def __repr__(self):
        return 'FloatRange(%r, %r)' % (self.min, self.max)


class BoolParamType(ParamType):
    name = 'boolean'

    def convert(self, value, param, ctx):
        if isinstance(value, bool):
            return bool(value)
        value = value.lower()
        if value in ('true', 't', '1', 'yes', 'y'):
            return True
        elif value in ('false', 'f', '0', 'no', 'n'):
            return False
        self.fail('%s is not a valid boolean' % value, param, ctx)

    def __repr__(self):
        return 'BOOL'


class UUIDParameterType(ParamType):
    name = 'uuid'

    def convert(self, value, param, ctx):
        import uuid
        try:
            if PY2 and isinstance(value, text_type):
                value = value.encode('ascii')
            return uuid.UUID(value)
        except (UnicodeError, ValueError):
            self.fail('%s is not a valid UUID value' % value, param, ctx)

    def __repr__(self):
        return 'UUID'


class File(ParamType):
    """把一个参数形式声明成一个文件进行读取或写入。
    文件是自动通过语境关闭的 (命令执行完成后)。

    文件都可以为读取或写入而打开。特殊值 ``-`` 根据开启的模式变成了标准输入或标准输出文件。

    默认情况下，文件是为读取文本数据而打开，但也可以打开二进制模式的读写。可以具体描述编码参数。

    其中 `lazy` 旗语控制文件是否立即打开，或先打开 IO 接口。这就是懒蛋模式！
    对于标准输入和标准输出流数据来说，默认是非懒蛋模式，文件为读取打开时也是一样，反之就是懒蛋模式。
    当用懒蛋模式打开一个文件读取时，依然是临时打开进行验证，但不会保持打开状态，除非先打开 IO 接口。
    懒蛋模式主要用处是，当为写入打开时，可以避免建立文件，除非需要才会建立文件。

    从 Click 2.0 开始，文件也可以自动地打开，这种情况下所有写入都会进入相同文件夹里的单个文件，
    并且直到完成文件会被移动到原始位置。如果一个文件常规地由其它用户修改的话，这是有用的。

    阅读 :ref:`file-args` 参考文档了解更多信息。
    """
    name = 'filename'
    envvar_list_splitter = os.path.pathsep

    def __init__(self, mode='r', encoding=None, errors='strict', lazy=None,
                 atomic=False):
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.lazy = lazy
        self.atomic = atomic

    def resolve_lazy_flag(self, value):
        if self.lazy is not None:
            return self.lazy
        if value == '-':
            return False
        elif 'w' in self.mode:
            return True
        return False

    def convert(self, value, param, ctx):
        try:
            if hasattr(value, 'read') or hasattr(value, 'write'):
                return value

            lazy = self.resolve_lazy_flag(value)

            if lazy:
                f = LazyFile(value, self.mode, self.encoding, self.errors,
                             atomic=self.atomic)
                if ctx is not None:
                    ctx.call_on_close(f.close_intelligently)
                return f

            f, should_close = open_stream(value, self.mode,
                                          self.encoding, self.errors,
                                          atomic=self.atomic)
            # If a context is provided, we automatically close the file
            # at the end of the context execution (or flush out).  If a
            # context does not exist, it's the caller's responsibility to
            # properly close the file.  This for instance happens when the
            # type is used with prompts.
            if ctx is not None:
                if should_close:
                    ctx.call_on_close(safecall(f.close))
                else:
                    ctx.call_on_close(safecall(f.flush))
            return f
        except (IOError, OSError) as e:
            self.fail('Could not open file: %s: %s' % (
                filename_to_ui(value),
                get_streerror(e),
            ), param, ctx)


class Path(ParamType):
    """路径类型类似 :class:`File` 文件类型，但执行了不同的检查。
    首先，代替返回一个打开的文件处理，而只是返回文件名。
    第二，可以执行各种基础检查，是文件还是目录。

    .. versionchanged:: 6.0
       其中增加了 `allow_dash` 参数。

    :param exists: 如果设置成 `True` 的话，文件或目录需要存在才是合法情况。
                   如果不需要存在检查并且确实没有一个文件的话，那么所有后面
                   的检查都默默地跳过。
    :param file_okay: 控制是否可能是一个文件。
    :param dir_okay: 控制是否可能是一个目录。
    :param writable: 如果设置成 `True` 的话，执行可写检查。
    :param readable: 如果设置成 `True` 的话，执行可读检查。
    :param resolve_path: 如何设置成 `True` 的话，在值传递下去之前变成完整路径。
                         意思就是绝对路径和软连接都要得到解决。本功能不会展开
                         带 `~` 的路径前缀，因为翻译这个路径写法只由终端来支持。
    :param allow_dash: 如果设置成 `True` 的话，允许一个减号指明标准流数据。
    :param path_type: 应该用来表示路径的一种字符串类型。默认值是 `None` 意思是
                      返回值即可以是字节，也可以是 unicode 。对于 unicode 来说
                      要根据提供的输入数据最有意义的内容由 Click 来处理。
    """
    envvar_list_splitter = os.path.pathsep

    def __init__(self, exists=False, file_okay=True, dir_okay=True,
                 writable=False, readable=True, resolve_path=False,
                 allow_dash=False, path_type=None):
        self.exists = exists
        self.file_okay = file_okay
        self.dir_okay = dir_okay
        self.writable = writable
        self.readable = readable
        self.resolve_path = resolve_path
        self.allow_dash = allow_dash
        self.type = path_type

        if self.file_okay and not self.dir_okay:
            self.name = 'file'
            self.path_type = 'File'
        elif self.dir_okay and not self.file_okay:
            self.name = 'directory'
            self.path_type = 'Directory'
        else:
            self.name = 'path'
            self.path_type = 'Path'

    def coerce_path_result(self, rv):
        if self.type is not None and not isinstance(rv, self.type):
            if self.type is text_type:
                rv = rv.decode(get_filesystem_encoding())
            else:
                rv = rv.encode(get_filesystem_encoding())
        return rv

    def convert(self, value, param, ctx):
        rv = value

        is_dash = self.file_okay and self.allow_dash and rv in (b'-', '-')

        if not is_dash:
            if self.resolve_path:
                rv = os.path.realpath(rv)

            try:
                st = os.stat(rv)
            except OSError:
                if not self.exists:
                    return self.coerce_path_result(rv)
                self.fail('%s "%s" does not exist.' % (
                    self.path_type,
                    filename_to_ui(value)
                ), param, ctx)

            if not self.file_okay and stat.S_ISREG(st.st_mode):
                self.fail('%s "%s" is a file.' % (
                    self.path_type,
                    filename_to_ui(value)
                ), param, ctx)
            if not self.dir_okay and stat.S_ISDIR(st.st_mode):
                self.fail('%s "%s" is a directory.' % (
                    self.path_type,
                    filename_to_ui(value)
                ), param, ctx)
            if self.writable and not os.access(value, os.W_OK):
                self.fail('%s "%s" is not writable.' % (
                    self.path_type,
                    filename_to_ui(value)
                ), param, ctx)
            if self.readable and not os.access(value, os.R_OK):
                self.fail('%s "%s" is not readable.' % (
                    self.path_type,
                    filename_to_ui(value)
                ), param, ctx)

        return self.coerce_path_result(rv)


class Tuple(CompositeParamType):
    """Click 的默认行为是直接把一个类型作用在一个值上。
    在大多数情况中都工作良好，除了当 `nargs` 设置成一个固定数量时，
    元组中的元素使用了不同的类型。在这种情况下，就要使用 :class:`Tuple` 类了。
    这个类型只可以与 `nargs` 参数值是一个固定数字时使用。

    对于更多信息阅读 :ref:`tuple-type` 参考文档。

    这可以使用一个 Python 元组来选择成一个类型。

    :param types: 类型组成的一个列表，其中类型应该用作元组中的元素。
    """

    def __init__(self, types):
        self.types = [convert_type(ty) for ty in types]

    @property
    def name(self):
        return "<" + " ".join(ty.name for ty in self.types) + ">"

    @property
    def arity(self):
        return len(self.types)

    def convert(self, value, param, ctx):
        if len(value) != len(self.types):
            raise TypeError('It would appear that nargs is set to conflict '
                            'with the composite type arity.')
        return tuple(ty(x, param, ctx) for ty, x in zip(self.types, value))


def convert_type(ty, default=None):
    """Converts a callable or python ty into the most appropriate param
    ty.
    """
    guessed_type = False
    if ty is None and default is not None:
        if isinstance(default, tuple):
            ty = tuple(map(type, default))
        else:
            ty = type(default)
        guessed_type = True

    if isinstance(ty, tuple):
        return Tuple(ty)
    if isinstance(ty, ParamType):
        return ty
    if ty is text_type or ty is str or ty is None:
        return STRING
    if ty is int:
        return INT
    # Booleans are only okay if not guessed.  This is done because for
    # flags the default value is actually a bit of a lie in that it
    # indicates which of the flags is the one we want.  See get_default()
    # for more information.
    if ty is bool and not guessed_type:
        return BOOL
    if ty is float:
        return FLOAT
    if guessed_type:
        return STRING

    # Catch a common mistake
    if __debug__:
        try:
            if issubclass(ty, ParamType):
                raise AssertionError('Attempted to use an uninstantiated '
                                     'parameter type (%s).' % ty)
        except TypeError:
            pass
    return FuncParamType(ty)


#: A dummy parameter type that just does nothing.  From a user's
#: perspective this appears to just be the same as `STRING` but internally
#: no string conversion takes place.  This is necessary to achieve the
#: same bytes/unicode behavior on Python 2/3 in situations where you want
#: to not convert argument types.  This is usually useful when working
#: with file paths as they can appear in bytes and unicode.
#:
#: For path related uses the :class:`Path` type is a better choice but
#: there are situations where an unprocessed type is useful which is why
#: it is is provided.
#:
#: .. versionadded:: 4.0
UNPROCESSED = UnprocessedParamType()

#: A unicode string parameter type which is the implicit default.  This
#: can also be selected by using ``str`` as type.
STRING = StringParamType()

#: An integer parameter.  This can also be selected by using ``int`` as
#: type.
INT = IntParamType()

#: A floating point value parameter.  This can also be selected by using
#: ``float`` as type.
FLOAT = FloatParamType()

#: A boolean parameter.  This is the default for boolean flags.  This can
#: also be selected by using ``bool`` as a type.
BOOL = BoolParamType()

#: A UUID parameter.
UUID = UUIDParameterType()
