import os
import sys
import shutil
import tempfile
import contextlib
import shlex

from ._compat import iteritems, PY2, string_types


# If someone wants to vendor click, we want to ensure the
# correct package is discovered.  Ideally we could use a
# relative import here but unfortunately Python does not
# support that.
clickpkg = sys.modules[__name__.rsplit('.', 1)[0]]


if PY2:
    from cStringIO import StringIO
else:
    import io
    from ._compat import _find_binary_reader


class EchoingStdin(object):

    def __init__(self, input, output):
        self._input = input
        self._output = output

    def __getattr__(self, x):
        return getattr(self._input, x)

    def _echo(self, rv):
        self._output.write(rv)
        return rv

    def read(self, n=-1):
        return self._echo(self._input.read(n))

    def readline(self, n=-1):
        return self._echo(self._input.readline(n))

    def readlines(self):
        return [self._echo(x) for x in self._input.readlines()]

    def __iter__(self):
        return iter(self._echo(x) for x in self._input)

    def __repr__(self):
        return repr(self._input)


def make_input_stream(input, charset):
    # Is already an input stream.
    if hasattr(input, 'read'):
        if PY2:
            return input
        rv = _find_binary_reader(input)
        if rv is not None:
            return rv
        raise TypeError('Could not find binary reader for input stream.')

    if input is None:
        input = b''
    elif not isinstance(input, bytes):
        input = input.encode(charset)
    if PY2:
        return StringIO(input)
    return io.BytesIO(input)


class Result(object):
    """保留一个触发完的命令行脚本的捕获结果。"""

    def __init__(self, runner, stdout_bytes, stderr_bytes, exit_code,
                 exception, exc_info=None):
        #: The runner that created the result
        self.runner = runner
        #: The standard output as bytes.
        self.stdout_bytes = stdout_bytes
        #: The standard error as bytes, or False(y) if not available
        self.stderr_bytes = stderr_bytes
        #: The exit code as integer.
        self.exit_code = exit_code
        #: The exception that happened if one did.
        self.exception = exception
        #: The traceback
        self.exc_info = exc_info

    @property
    def output(self):
        """作为 unicode 字符串的 (标准) 输出。"""
        return self.stdout

    @property
    def stdout(self):
        """作为 unicode 字符串的标准输出。"""
        return self.stdout_bytes.decode(self.runner.charset, 'replace') \
            .replace('\r\n', '\n')

    @property
    def stderr(self):
        """作为 unicode 字符串的标准错误。"""
        if not self.stderr_bytes:
            raise ValueError("stderr not separately captured")
        return self.stderr_bytes.decode(self.runner.charset, 'replace') \
            .replace('\r\n', '\n')


    def __repr__(self):
        return '<%s %s>' % (
            type(self).__name__,
            self.exception and repr(self.exception) or 'okay',
        )


class CliRunner(object):
    """命令行运行器提供了触发一个 Click 命令行脚本的功能。
    针对单元测试目的而进入一个隔离环境。这个只工作在单个线程系统中，
    不能有任何一个并发线程，因为会改变全局解释器的状态。

    :param charset: 为输入和输出数据提供的字符集。默认是 UTF-8 字符集，
                    并且目前不应该去改变这个字符集，因为这样才能在 Python 2
                    中能够正确地做出报告内容。
    :param env: 含有环境变量的一个字典，为了覆写用。
    :param echo_stdin: 如果设置成 `True` 的话，从标准输入读取后写到标准输出上。
                       在某些环境中为了显示示例时，这就有用了。注意常规提示会
                       自动地回应输入。
    :param mix_stderr: 如果设置成 `False` 的话，标准输出和标准错误都会被保护
                       成独立的流数据。对于 Unix 类的应用来说这是有用的，因为
                       Unix 类应用具有预先的标准输出，并且会对标准错误造成噪音，
                       因此每个数据流都要独立进行测量。
    """

    def __init__(self, charset=None, env=None, echo_stdin=False,
                 mix_stderr=True):
        if charset is None:
            charset = 'utf-8'
        self.charset = charset
        self.env = env or {}
        self.echo_stdin = echo_stdin
        self.mix_stderr = mix_stderr

    def get_default_prog_name(self, cli):
        """给出一个命令对象，本方法会返回命令的默认程序名。
        如果没有设置程序名，默认值会是命令的 `name` 属性火 ``"root"`` 
        """
        return cli.name or 'root'

    def make_env(self, overrides=None):
        """为触发一个脚本返回环境覆写值。"""
        rv = dict(self.env)
        if overrides:
            rv.update(overrides)
        return rv

    @contextlib.contextmanager
    def isolation(self, input=None, env=None, color=False):
        """一个语境管理器，为一个命令行工具的触发搭建一个隔离环境。
        本函数建立的标准输入含有给出的输入数据和来自字典覆写的环境变量
         `os.environ` 。本函数也把 Click 里的一些内部对象重新绑定
        在一起执行 mock 测试 (例如提示功能)。

        在 :meth:`invoke` 方法中本函数会自动完成。

        .. versionadded:: 4.0
           其中增加了 ``color`` 参数。

        :param input: 要放入 sys.stdin 中的输入数据流。
        :param env: 要覆写环境变量的字典。
        :param color: 其中输出内容是否应该包含颜色代号。
                      应用程序依然可以明确地覆写这个效果。
        """
        input = make_input_stream(input, self.charset)

        old_stdin = sys.stdin
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        old_forced_width = clickpkg.formatting.FORCED_WIDTH
        clickpkg.formatting.FORCED_WIDTH = 80

        env = self.make_env(env)

        if PY2:
            bytes_output = StringIO()
            if self.echo_stdin:
                input = EchoingStdin(input, bytes_output)
            sys.stdout = bytes_output
            if not self.mix_stderr:
                bytes_error = StringIO()
                sys.stderr = bytes_error
        else:
            bytes_output = io.BytesIO()
            if self.echo_stdin:
                input = EchoingStdin(input, bytes_output)
            input = io.TextIOWrapper(input, encoding=self.charset)
            sys.stdout = io.TextIOWrapper(
                bytes_output, encoding=self.charset)
            if not self.mix_stderr:
                bytes_error = io.BytesIO()
                sys.stderr = io.TextIOWrapper(
                    bytes_error, encoding=self.charset)

        if self.mix_stderr:
            sys.stderr = sys.stdout

        sys.stdin = input

        def visible_input(prompt=None):
            sys.stdout.write(prompt or '')
            val = input.readline().rstrip('\r\n')
            sys.stdout.write(val + '\n')
            sys.stdout.flush()
            return val

        def hidden_input(prompt=None):
            sys.stdout.write((prompt or '') + '\n')
            sys.stdout.flush()
            return input.readline().rstrip('\r\n')

        def _getchar(echo):
            char = sys.stdin.read(1)
            if echo:
                sys.stdout.write(char)
                sys.stdout.flush()
            return char

        default_color = color

        def should_strip_ansi(stream=None, color=None):
            if color is None:
                return not default_color
            return not color

        old_visible_prompt_func = clickpkg.termui.visible_prompt_func
        old_hidden_prompt_func = clickpkg.termui.hidden_prompt_func
        old__getchar_func = clickpkg.termui._getchar
        old_should_strip_ansi = clickpkg.utils.should_strip_ansi
        clickpkg.termui.visible_prompt_func = visible_input
        clickpkg.termui.hidden_prompt_func = hidden_input
        clickpkg.termui._getchar = _getchar
        clickpkg.utils.should_strip_ansi = should_strip_ansi

        old_env = {}
        try:
            for key, value in iteritems(env):
                old_env[key] = os.environ.get(key)
                if value is None:
                    try:
                        del os.environ[key]
                    except Exception:
                        pass
                else:
                    os.environ[key] = value
            yield (bytes_output, not self.mix_stderr and bytes_error)
        finally:
            for key, value in iteritems(old_env):
                if value is None:
                    try:
                        del os.environ[key]
                    except Exception:
                        pass
                else:
                    os.environ[key] = value
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin
            clickpkg.termui.visible_prompt_func = old_visible_prompt_func
            clickpkg.termui.hidden_prompt_func = old_hidden_prompt_func
            clickpkg.termui._getchar = old__getchar_func
            clickpkg.utils.should_strip_ansi = old_should_strip_ansi
            clickpkg.formatting.FORCED_WIDTH = old_forced_width

    def invoke(self, cli, args=None, input=None, env=None,
               catch_exceptions=True, color=False, mix_stderr=False, **extra):
        """在一个隔离环境中触发一个命令。
        参数都直接提供给命令行脚本， `extra` 多关键字参数会被代入到
        命令的 :meth:`~clickpkg.Command.main` 函数中。

        本函数返回一个 :class:`Result` 类实例对象。

        .. versionadded:: 3.0
           其中增加了 ``catch_exceptions`` 参数。

        .. versionchanged:: 3.0
           结果对象现在有了一个 `exc_info` 属性，如果可用包含追踪信息。

        .. versionadded:: 4.0
           其中增加了 ``color`` 参数。

        :param cli: 要触发的命令。
        :param args: 要触发的参数。可以作为一个可迭代对象或一个字符串。
                     当提供的是字符串，会被翻译成一种 Unix 终端命令。
                     更多细节在 :func:`shlex.split` 函数中。
        :param input: 提供给 `sys.stdin` 的输入数据。
        :param env: 覆写的环境变量。
        :param catch_exceptions: 是否要捕获除了 ``SystemExit`` 以外的任何一个其它例外。
        :param extra: 要传递给 :meth:`main` 方法的多关键字参数。
        :param color: 是否要输出内容包含颜色代号。应用程序依然可以明确覆写这个效果。
        """
        exc_info = None
        with self.isolation(input=input, env=env, color=color) as outstreams:
            exception = None
            exit_code = 0

            if isinstance(args, string_types):
                args = shlex.split(args)

            try:
                prog_name = extra.pop("prog_name")
            except KeyError:
                prog_name = self.get_default_prog_name(cli)

            try:
                cli.main(args=args or (), prog_name=prog_name, **extra)
            except SystemExit as e:
                exc_info = sys.exc_info()
                exit_code = e.code
                if exit_code is None:
                    exit_code = 0

                if exit_code != 0:
                    exception = e

                if not isinstance(exit_code, int):
                    sys.stdout.write(str(exit_code))
                    sys.stdout.write('\n')
                    exit_code = 1

            except Exception as e:
                if not catch_exceptions:
                    raise
                exception = e
                exit_code = 1
                exc_info = sys.exc_info()
            finally:
                sys.stdout.flush()
                stdout = outstreams[0].getvalue()
                stderr = outstreams[1] and outstreams[1].getvalue()

        return Result(runner=self,
                      stdout_bytes=stdout,
                      stderr_bytes=stderr,
                      exit_code=exit_code,
                      exception=exception,
                      exc_info=exc_info)

    @contextlib.contextmanager
    def isolated_filesystem(self):
        """一个语境管理器，能建立一个临时文件夹后改变当前工作目录。
        这是为了隔离的文件系统测试而使用。
        """
        cwd = os.getcwd()
        t = tempfile.mkdtemp()
        os.chdir(t)
        try:
            yield t
        finally:
            os.chdir(cwd)
            try:
                shutil.rmtree(t)
            except (OSError, IOError):
                pass
