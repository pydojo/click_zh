import os
import sys

from .globals import resolve_color_default

from ._compat import text_type, open_stream, get_filesystem_encoding, \
    get_streerror, string_types, PY2, binary_streams, text_streams, \
    filename_to_ui, auto_wrap_for_ansi, strip_ansi, should_strip_ansi, \
    _default_text_stdout, _default_text_stderr, is_bytes, WIN

if not PY2:
    from ._compat import _find_binary_writer
elif WIN:
    from ._winconsole import _get_windows_argv, \
         _hash_py_argv, _initial_argv_hash


echo_native_types = string_types + (bytes, bytearray)


def _posixify(name):
    return '-'.join(name.split()).lower()


def safecall(func):
    """Wraps a function so that it swallows exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            pass
    return wrapper


def make_str(value):
    """Converts a value into a valid string."""
    if isinstance(value, bytes):
        try:
            return value.decode(get_filesystem_encoding())
        except UnicodeError:
            return value.decode('utf-8', 'replace')
    return text_type(value)


def make_default_short_help(help, max_length=45):
    """Return a condensed version of help string."""
    words = help.split()
    total_length = 0
    result = []
    done = False

    for word in words:
        if word[-1:] == '.':
            done = True
        new_length = result and 1 + len(word) or len(word)
        if total_length + new_length > max_length:
            result.append('...')
            done = True
        else:
            if result:
                result.append(' ')
            result.append(word)
        if done:
            break
        total_length += new_length

    return ''.join(result)


class LazyFile(object):
    """A lazy file works like a regular file but it does not fully open
    the file but it does perform some basic checks early to see if the
    filename parameter does make sense.  This is useful for safely opening
    files for writing.
    """

    def __init__(self, filename, mode='r', encoding=None, errors='strict',
                 atomic=False):
        self.name = filename
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.atomic = atomic

        if filename == '-':
            self._f, self.should_close = open_stream(filename, mode,
                                                     encoding, errors)
        else:
            if 'r' in mode:
                # Open and close the file in case we're opening it for
                # reading so that we can catch at least some errors in
                # some cases early.
                open(filename, mode).close()
            self._f = None
            self.should_close = True

    def __getattr__(self, name):
        return getattr(self.open(), name)

    def __repr__(self):
        if self._f is not None:
            return repr(self._f)
        return '<unopened file %r %s>' % (self.name, self.mode)

    def open(self):
        """Opens the file if it's not yet open.  This call might fail with
        a :exc:`FileError`.  Not handling this error will produce an error
        that Click shows.
        """
        if self._f is not None:
            return self._f
        try:
            rv, self.should_close = open_stream(self.name, self.mode,
                                                self.encoding,
                                                self.errors,
                                                atomic=self.atomic)
        except (IOError, OSError) as e:
            from .exceptions import FileError
            raise FileError(self.name, hint=get_streerror(e))
        self._f = rv
        return rv

    def close(self):
        """Closes the underlying file, no matter what."""
        if self._f is not None:
            self._f.close()

    def close_intelligently(self):
        """This function only closes the file if it was opened by the lazy
        file wrapper.  For instance this will never close stdin.
        """
        if self.should_close:
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close_intelligently()

    def __iter__(self):
        self.open()
        return iter(self._f)


class KeepOpenFile(object):

    def __init__(self, file):
        self._file = file

    def __getattr__(self, name):
        return getattr(self._file, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        pass

    def __repr__(self):
        return repr(self._file)

    def __iter__(self):
        return iter(self._file)


def echo(message=None, file=None, nl=True, err=False, color=None):
    """把一个消息带着一个新行字符输出到文件或标准输出上。
    第一眼看起来像是一个输出函数，但 `echo` 已经提升为支持
    处理 Unicode 和二进制数据，不管你的系统配置有多糟糕本
    函数都不会失败。

    本函数的主要意义在于你可以在 Python 2 和 3 系版本上
    即可以输出二进制数据，也可以输出 Unicode 数据到文件，
    并以最合适的方法来实现。本函数是一个非常无忧函数，因为
    会尽最大努力不让失败发生。作为 Click 6.0 版本已经包括
    了 Unicode 输出在 Windows 系统终端上的支持。

    另外，如果 `colorama`_ 色彩机制已经安装的话， `echo` 
    函数也会支持对 ANSI 色彩代号的明智处理。如下是不可少的:

    -   在 Windows 系统上增加 ANSI 色彩代号的透明度处理。
    -   如果目标文件不是一个终端的话，自动隐藏 ANSI 色彩代号。

    .. _colorama: https://pypi.org/project/colorama/

    .. versionchanged:: 6.0
       作为 Click 6.0 版本中的 echo 函数会正确地支持 unicode 输出
       到 Windows 系统终端上。注意 click 不会用任何一种方法
       修改解释器，这意味着 `sys.stdout` 或 print 语句或函数
       依然不会提供 unicode 数据支持。

    .. versionchanged:: 2.0
       从 Click 2.0 版本开始， echo 函数会与 colorama 一起工作。

    .. versionadded:: 3.0
       其中增加了 `err` 参数形式。

    .. versionchanged:: 4.0
       其中增加了 `color` 旗语。

    :param message: 要输出的消息
    :param file: 要写入的文件 (默认值是 ``stdout``)
    :param err: 如果设置成 `True` 的话， file 默认值是 ``stderr`` 
                不再是 ``stdout`` 了。这要比你自己调用 
                :func:`get_text_stderr` 函数性能更快，
                用起来更容易。
    :param nl: 如果设置成 `True` (即默认值) 在消息最后会有一个新行字符。
    :param color: 控制终端是否支持 ANSI 色彩机制。默认是自动检测。
    """
    if file is None:
        if err:
            file = _default_text_stderr()
        else:
            file = _default_text_stdout()

    # Convert non bytes/text into the native string type.
    if message is not None and not isinstance(message, echo_native_types):
        message = text_type(message)

    if nl:
        message = message or u''
        if isinstance(message, text_type):
            message += u'\n'
        else:
            message += b'\n'

    # If there is a message, and we're in Python 3, and the value looks
    # like bytes, we manually need to find the binary stream and write the
    # message in there.  This is done separately so that most stream
    # types will work as you would expect.  Eg: you can write to StringIO
    # for other cases.
    if message and not PY2 and is_bytes(message):
        binary_file = _find_binary_writer(file)
        if binary_file is not None:
            file.flush()
            binary_file.write(message)
            binary_file.flush()
            return

    # ANSI-style support.  If there is no message or we are dealing with
    # bytes nothing is happening.  If we are connected to a file we want
    # to strip colors.  If we are on windows we either wrap the stream
    # to strip the color or we use the colorama support to translate the
    # ansi codes to API calls.
    if message and not is_bytes(message):
        color = resolve_color_default(color)
        if should_strip_ansi(file, color):
            message = strip_ansi(message)
        elif WIN:
            if auto_wrap_for_ansi is not None:
                file = auto_wrap_for_ansi(file)
            elif not color:
                message = strip_ansi(message)

    if message:
        file.write(message)
    file.flush()


def get_binary_stream(name):
    """针对字节处理返回一种系统流数据。
    这是不可缺少的，返回的流数据来自 sys 模块，使用给出的名字值，
    但本函数解决了不同 Python 版本之间的一些兼容问题。本函数的
    主要作用是在 Python 3 上获得二进制数据流。

    :param name: 要打开的流数据名字。合法的名字有 3 个:
                 ``'stdin'`` 、 ``'stdout'`` 和 ``'stderr'``
    """
    opener = binary_streams.get(name)
    if opener is None:
        raise TypeError('Unknown standard stream %r' % name)
    return opener()


def get_text_stream(name, encoding=None, errors='strict'):
    """针对文本处理返回一种系统流数据。
    本函数常返回一个打包过的流数据，即把由 :func:`get_binary_stream`
    函数返回的一种二进制流数据打包，但在 Python 3 上对于已经正确地配置
    了流数据来说也是一种快捷函数。

    :param name: 要打开的流数据名字。合法的名字有 3 个：
                 ``'stdin'`` 、 ``'stdout'`` 和 ``'stderr'``
    :param encoding: 覆写检测到的默认编码。
    :param errors: 覆写默认的错误模式。
    """
    opener = text_streams.get(name)
    if opener is None:
        raise TypeError('Unknown standard stream %r' % name)
    return opener(encoding, errors)


def open_file(filename, mode='r', encoding=None, errors='strict',
              lazy=False, atomic=False):
    """本函数类似 :class:`File` 类的工作，但手动来使用。
    默认文件都是非懒蛋模式打开的。本函数可以把常规文件打开成
    标准输入/标准输出，当然是以 ``'-'`` 作为文件名的时候。

    如果 stdin/stdout 被返回的话，流数据会被打包，
    所以语境管理器不会让关闭流数据的意外发生。所以
    本函数是确保标准流数据不会被意外关闭的保障。::

        with open_file(filename) as f:
            ...

    .. versionadded:: 3.0

    :param filename: 要打开的文件名 (或者用 ``'-'`` 来实现标准输入/标准输出)
    :param mode: 打开文件时采用的模式。
    :param encoding: 要使用的编码。
    :param errors: 针对文件的错误处理模式。
    :param lazy: 是否采用懒蛋模式打开文件。
    :param atomic: 以原子价模式写文件会进入一个临时文件，
                   并且直到文件关闭。
    """
    if lazy:
        return LazyFile(filename, mode, encoding, errors, atomic=atomic)
    f, should_close = open_stream(filename, mode, encoding, errors,
                                  atomic=atomic)
    if not should_close:
        f = KeepOpenFile(f)
    return f


def get_os_args():
    """This returns the argument part of sys.argv in the most appropriate
    form for processing.  What this means is that this return value is in
    a format that works for Click to process but does not necessarily
    correspond well to what's actually standard for the interpreter.

    On most environments the return value is ``sys.argv[:1]`` unchanged.
    However if you are on Windows and running Python 2 the return value
    will actually be a list of unicode strings instead because the
    default behavior on that platform otherwise will not be able to
    carry all possible values that sys.argv can have.

    .. versionadded:: 6.0
    """
    # We can only extract the unicode argv if sys.argv has not been
    # changed since the startup of the application.
    if PY2 and WIN and _initial_argv_hash == _hash_py_argv():
        return _get_windows_argv()
    return sys.argv[1:]


def format_filename(filename, shorten=False):
    """为用户显示格式化一个文件名。
    本函数的主要目的是确保文件名可以全部显示出来。
    这会把文件名解码成 unicode 格式，否则会出现乱码。
    另外可以显示文件名的短写形式，不包括完整路径部分。

    :param filename: 为用户显示的格式化一个文件名。也会把文件名转换成
                     unicode 编码，不会失败。
    :param shorten: 设置成 `True` 后会只提取文件名短写形式，
                    完整路径部分会被剥离。
    """
    if shorten:
        filename = os.path.basename(filename)
    return filename_to_ui(filename)


def get_app_dir(app_name, roaming=True, force_posix=False):
    r"""返回应用程序的配置目录。
    默认行为是针对操作系统返回最合适的应用程序所在文件夹。

    给你一个思路，对于一个名叫 ``"Foo Bar"`` 应用程序来说，
    针对不同操作系统可能会返回如下所在目录:

    Mac OS X:
      ``~/Library/Application Support/Foo Bar``
    Mac OS X (POSIX):
      ``~/.foo-bar``
    Unix:
      ``~/.config/foo-bar``
    Unix (POSIX):
      ``~/.foo-bar``
    Win XP (roaming):
      ``C:\Documents and Settings\<user>\Local Settings\Application Data\Foo Bar``
    Win XP (not roaming):
      ``C:\Documents and Settings\<user>\Application Data\Foo Bar``
    Win 7 (roaming):
      ``C:\Users\<user>\AppData\Roaming\Foo Bar``
    Win 7 (not roaming):
      ``C:\Users\<user>\AppData\Local\Foo Bar``

    .. versionadded:: 2.0

    :param app_name: 应用程序的名字。这应该是合适的含有大写字母的名字，
                     并且能包含空格字符。
    :param roaming: 在 Windows 系统上控制文件夹是否被移动。
                    其它操作系统上是无效的。
    :param force_posix: 如果设置成 `True` 的话，在任何一款 POSIX 系统上，
                        文件夹会存储在 home 目录下，并且目录名带着一个句号，
                        相反 XDG 配置 home 或者 darwin 的应用程序所支持的目录。
    """
    if WIN:
        key = roaming and 'APPDATA' or 'LOCALAPPDATA'
        folder = os.environ.get(key)
        if folder is None:
            folder = os.path.expanduser('~')
        return os.path.join(folder, app_name)
    if force_posix:
        return os.path.join(os.path.expanduser('~/.' + _posixify(app_name)))
    if sys.platform == 'darwin':
        return os.path.join(os.path.expanduser(
            '~/Library/Application Support'), app_name)
    return os.path.join(
        os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
        _posixify(app_name))


class PacifyFlushWrapper(object):
    """This wrapper is used to catch and suppress BrokenPipeErrors resulting
    from ``.flush()`` being called on broken pipe during the shutdown/final-GC
    of the Python interpreter. Notably ``.flush()`` is always called on
    ``sys.stdout`` and ``sys.stderr``. So as to have minimal impact on any
    other cleanup code, and the case where the underlying file is not a broken
    pipe, all calls and attributes are proxied.
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def flush(self):
        try:
            self.wrapped.flush()
        except IOError as e:
            import errno
            if e.errno != errno.EPIPE:
                raise

    def __getattr__(self, attr):
        return getattr(self.wrapped, attr)
