import errno
import inspect
import os
import sys
from contextlib import contextmanager
from itertools import repeat
from functools import update_wrapper

from .types import convert_type, IntRange, BOOL
from .utils import PacifyFlushWrapper, make_str, make_default_short_help, \
     echo, get_os_args
from .exceptions import ClickException, UsageError, BadParameter, Abort, \
     MissingParameter, Exit
from .termui import prompt, confirm, style
from .formatting import HelpFormatter, join_options
from .parser import OptionParser, split_opt
from .globals import push_context, pop_context

from ._compat import PY2, isidentifier, iteritems, string_types
from ._unicodefun import _check_for_unicode_literals, _verify_python3_env


_missing = object()


SUBCOMMAND_METAVAR = 'COMMAND [ARGS]...'
SUBCOMMANDS_METAVAR = 'COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...'

DEPRECATED_HELP_NOTICE = ' (DEPRECATED)'
DEPRECATED_INVOKE_NOTICE = 'DeprecationWarning: ' + \
                           'The command %(name)s is deprecated.'


def _maybe_show_deprecated_notice(cmd):
    if cmd.deprecated:
        echo(style(DEPRECATED_INVOKE_NOTICE % {'name': cmd.name}, fg='red'), err=True)


def fast_exit(code):
    """Exit without garbage collection, this speeds up exit by about 10ms for
    things like bash completion.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def _bashcomplete(cmd, prog_name, complete_var=None):
    """Internal handler for the bash completion support."""
    if complete_var is None:
        complete_var = '_%s_COMPLETE' % (prog_name.replace('-', '_')).upper()
    complete_instr = os.environ.get(complete_var)
    if not complete_instr:
        return

    from ._bashcomplete import bashcomplete
    if bashcomplete(cmd, prog_name, complete_var, complete_instr):
        fast_exit(1)


def _check_multicommand(base_command, cmd_name, cmd, register=False):
    if not base_command.chain or not isinstance(cmd, MultiCommand):
        return
    if register:
        hint = 'It is not possible to add multi commands as children to ' \
               'another multi command that is in chain mode'
    else:
        hint = 'Found a multi command as subcommand to a multi command ' \
               'that is in chain mode.  This is not supported'
    raise RuntimeError('%s.  Command "%s" is set to chain and "%s" was '
                       'added as subcommand but it in itself is a '
                       'multi command.  ("%s" is a %s within a chained '
                       '%s named "%s").' % (
                           hint, base_command.name, cmd_name,
                           cmd_name, cmd.__class__.__name__,
                           base_command.__class__.__name__,
                           base_command.name))


def batch(iterable, batch_size):
    return list(zip(*repeat(iter(iterable), batch_size)))


def invoke_param_callback(callback, ctx, param, value):
    code = getattr(callback, '__code__', None)
    args = getattr(code, 'co_argcount', 3)

    if args < 3:
        # This will become a warning in Click 3.0:
        from warnings import warn
        warn(Warning('Invoked legacy parameter callback "%s".  The new '
                     'signature for such callbacks starting with '
                     'click 2.0 is (ctx, param, value).'
                     % callback), stacklevel=3)
        return callback(ctx, value)
    return callback(ctx, param, value)


@contextmanager
def augment_usage_errors(ctx, param=None):
    """Context manager that attaches extra information to exceptions that
    fly.
    """
    try:
        yield
    except BadParameter as e:
        if e.ctx is None:
            e.ctx = ctx
        if param is not None and e.param is None:
            e.param = param
        raise
    except UsageError as e:
        if e.ctx is None:
            e.ctx = ctx
        raise


def iter_params_for_processing(invocation_order, declaration_order):
    """Given a sequence of parameters in the order as should be considered
    for processing and an iterable of parameters that exist, this returns
    a list in the correct order as they should be processed.
    """
    def sort_key(item):
        try:
            idx = invocation_order.index(item)
        except ValueError:
            idx = float('inf')
        return (not item.is_eager, idx)

    return sorted(declaration_order, key=sort_key)

class ParameterSource(object):
    """This is an enum that indicates the source of a command line parameter.

    The enum has one of the following values: COMMANDLINE,
    ENVIRONMENT, DEFAULT, DEFAULT_MAP.  The DEFAULT indicates that the
    default value in the decorator was used.  This class should be
    converted to an enum when Python 2 support is dropped.
    """

    COMMANDLINE = "COMMANDLINE"
    ENVIRONMENT = "ENVIRONMENT"
    DEFAULT = "DEFAULT"
    DEFAULT_MAP = "DEFAULT_MAP"
    
    VALUES = {COMMANDLINE, ENVIRONMENT, DEFAULT, DEFAULT_MAP}
    
    @classmethod
    def validate(cls, value):
        """Validate that the specified value is a valid enum.

        This method will raise a ValueError if the value is
        not a valid enum.

        :param value: the string value to verify
        """
        if value not in cls.VALUES:
            raise ValueError("Invalid ParameterSource value: '{}'. Valid "
                             "values are: {}".format(value, ",".join(cls.VALUES)))


class Context(object):
    """语境类是一个特殊的内部对象。
    它是用来保存与脚本执行有关的状态，作用在每个层次上执行的脚本。
    正常来说命令是看不到这个类的，除非命令开启了这个功能才可以访问语境对象。

    语境是有用的，因为语境可以传递内部对象，并且可以控制特殊的执行特性，
    例如从环境变量中读取数据。

    一个语境可以用作语境管理器，在语境管理器环境中会在 teardown 上调用
    :meth:`close` 方法。

    .. versionadded:: 2.0
       其中增加了 `resilient_parsing` 、 `help_option_names` 
       和 `token_normalize_func` 参数。

    .. versionadded:: 3.0
       其中增加了 `allow_extra_args` 和 `allow_interspersed_args`
       参数。

    .. versionadded:: 4.0
       其中增加了 `color` 、 `ignore_unknown_options` 和
       `max_content_width` 参数。

    :param command: 使用语境的命令类。
    :param parent: 父语境。
    :param info_name: 语境内部的信息名。通用中，描述的名字常是脚本或命令。
                      对于顶层的脚本来说，常是脚本的名字，对于脚本下面的
                      命令来说也是脚本的名字。
    :param obj: 用户数据的任意一个对象。
    :param auto_envvar_prefix: 为自动的环境变量使用的前缀。
                               如何设置成 `None` 的话，无法从环境变量中读取。
                               这不会影响手动设置环境变量，因为手动设置会一直读取。
    :param default_map: 一个含有参数默认值的字典 (类似对象) 。
    :param terminal_width: 终端的宽度。默认值继承自父语境。如果语境没定义终端宽度，
                           会自动进行检测。
    :param max_content_width: 被 Click 渲染的内容最大宽度值 (目前只作用在帮助页面上)。
                              如果不覆写这个值的话，默认是 80 个字符的宽度。
                              换句话说: 即时终端更大的话， Click 不会格式化宽度大于
                              这个值，默认情况不会大于 80 个字符宽。另外，格式化器也许
                              增加一些安全映射内容在右边。
    :param resilient_parsing: 如果开启这个旗语的话， Click 会不带互动或回调语境来执行
                              语法分析。默认值也会忽略。对于实现补全功能时是有用的。
    :param allow_extra_args: 如果设置成 `True` 的话，那么尾部的额外参数不会抛出一个例外，
                             并且会保存在语境中。默认值是继承自命令的。
    :param allow_interspersed_args: 如果设置成 `False` 的话，那么不能混用可选项和参数。
                                    默认值是继承自命令的。
    :param ignore_unknown_options: 指导 click 忽略不知道的可选项，并且把未知可选项
                                   保存下来稍后处理。
    :param help_option_names: 可以用字符串组成的一个列表，字符串都是参数形式名。
                              如何定义默认帮助参数的名字，默认值是 ``['--help']``
    :param token_normalize_func: 一个用来正常化令牌的函数 (令牌包括可选项、选项等等对象)。
                                 例如可以用来实现大小写敏感行为。
    :param color: 控制终端是否支持 ANSI 色彩机制。默认是自动检测。
                  如果 ANSI 颜色代号用在文本上就需要这个值， Click
                  默认不会输出变色文字。这个也会影响帮助页面的输出。
    :param show_default: 如果设置成 `True` 的话，对于所有可选项来说会显示默认值。
                    即使一个可选项稍后用 `show_default=False` 来建立的话，
                    这种命令层的设置会覆写可选项层的值。
    """

    def __init__(self, command, parent=None, info_name=None, obj=None,
                 auto_envvar_prefix=None, default_map=None,
                 terminal_width=None, max_content_width=None,
                 resilient_parsing=False, allow_extra_args=None,
                 allow_interspersed_args=None,
                 ignore_unknown_options=None, help_option_names=None,
                 token_normalize_func=None, color=None, show_default=None):
        #: the parent context or `None` if none exists.
        self.parent = parent
        #: the :class:`Command` for this context.
        self.command = command
        #: the descriptive information name
        self.info_name = info_name
        #: the parsed parameters except if the value is hidden in which
        #: case it's not remembered.
        self.params = {}
        #: the leftover arguments.
        self.args = []
        #: protected arguments.  These are arguments that are prepended
        #: to `args` when certain parsing scenarios are encountered but
        #: must be never propagated to another arguments.  This is used
        #: to implement nested parsing.
        self.protected_args = []
        if obj is None and parent is not None:
            obj = parent.obj
        #: the user object stored.
        self.obj = obj
        self._meta = getattr(parent, 'meta', {})

        #: A dictionary (-like object) with defaults for parameters.
        if default_map is None \
           and parent is not None \
           and parent.default_map is not None:
            default_map = parent.default_map.get(info_name)
        self.default_map = default_map

        #: This flag indicates if a subcommand is going to be executed. A
        #: group callback can use this information to figure out if it's
        #: being executed directly or because the execution flow passes
        #: onwards to a subcommand. By default it's None, but it can be
        #: the name of the subcommand to execute.
        #:
        #: If chaining is enabled this will be set to ``'*'`` in case
        #: any commands are executed.  It is however not possible to
        #: figure out which ones.  If you require this knowledge you
        #: should use a :func:`resultcallback`.
        self.invoked_subcommand = None

        if terminal_width is None and parent is not None:
            terminal_width = parent.terminal_width
        #: The width of the terminal (None is autodetection).
        self.terminal_width = terminal_width

        if max_content_width is None and parent is not None:
            max_content_width = parent.max_content_width
        #: The maximum width of formatted content (None implies a sensible
        #: default which is 80 for most things).
        self.max_content_width = max_content_width

        if allow_extra_args is None:
            allow_extra_args = command.allow_extra_args
        #: Indicates if the context allows extra args or if it should
        #: fail on parsing.
        #:
        #: .. versionadded:: 3.0
        self.allow_extra_args = allow_extra_args

        if allow_interspersed_args is None:
            allow_interspersed_args = command.allow_interspersed_args
        #: Indicates if the context allows mixing of arguments and
        #: options or not.
        #:
        #: .. versionadded:: 3.0
        self.allow_interspersed_args = allow_interspersed_args

        if ignore_unknown_options is None:
            ignore_unknown_options = command.ignore_unknown_options
        #: Instructs click to ignore options that a command does not
        #: understand and will store it on the context for later
        #: processing.  This is primarily useful for situations where you
        #: want to call into external programs.  Generally this pattern is
        #: strongly discouraged because it's not possibly to losslessly
        #: forward all arguments.
        #:
        #: .. versionadded:: 4.0
        self.ignore_unknown_options = ignore_unknown_options

        if help_option_names is None:
            if parent is not None:
                help_option_names = parent.help_option_names
            else:
                help_option_names = ['--help']

        #: The names for the help options.
        self.help_option_names = help_option_names

        if token_normalize_func is None and parent is not None:
            token_normalize_func = parent.token_normalize_func

        #: An optional normalization function for tokens.  This is
        #: options, choices, commands etc.
        self.token_normalize_func = token_normalize_func

        #: Indicates if resilient parsing is enabled.  In that case Click
        #: will do its best to not cause any failures and default values
        #: will be ignored. Useful for completion.
        self.resilient_parsing = resilient_parsing

        # If there is no envvar prefix yet, but the parent has one and
        # the command on this level has a name, we can expand the envvar
        # prefix automatically.
        if auto_envvar_prefix is None:
            if parent is not None \
               and parent.auto_envvar_prefix is not None and \
               self.info_name is not None:
                auto_envvar_prefix = '%s_%s' % (parent.auto_envvar_prefix,
                                           self.info_name.upper())
        else:
            auto_envvar_prefix = auto_envvar_prefix.upper()
        self.auto_envvar_prefix = auto_envvar_prefix

        if color is None and parent is not None:
            color = parent.color

        #: Controls if styling output is wanted or not.
        self.color = color

        self.show_default = show_default

        self._close_callbacks = []
        self._depth = 0
        self._source_by_paramname = {}
        
    def __enter__(self):
        self._depth += 1
        push_context(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._depth -= 1
        if self._depth == 0:
            self.close()
        pop_context()

    @contextmanager
    def scope(self, cleanup=True):
        """这是一个辅助方法，可以与语境对象一起使用。
        把语境对象给当前本地线程 (查看 :func:`get_current_context` 函数)。
        本函数默认行为是触发 cleanup 函数，可以通过把 `cleanup` 设置成 
        `False` 来禁用。 cleanup 函数典型来说都是用来像关闭文件处理这样的操作。

        如果想要 cleanup 效果在语境对象上自动执行，也可以直接用作一个语境管理器。

        示例用法::

            with ctx.scope():
                assert get_current_context() is ctx

        等价用法::

            with ctx:
                assert get_current_context() is ctx

        .. versionadded:: 5.0

        :param cleanup: 控制是否要运行 cleanup 函数。默认是运行这些函数。
                        在一些情况中，语境只想临时被推送，那就要禁用。
                        嵌入的推送自动推迟 cleanup 函数的执行。
        """
        if not cleanup:
            self._depth += 1
        try:
            with self as rv:
                yield rv
        finally:
            if not cleanup:
                self._depth -= 1

    @property
    def meta(self):
        """This is a dictionary which is shared with all the contexts
        that are nested.  It exists so that click utilities can store some
        state here if they need to.  It is however the responsibility of
        that code to manage this dictionary well.

        The keys are supposed to be unique dotted strings.  For instance
        module paths are a good choice for it.  What is stored in there is
        irrelevant for the operation of click.  However what is important is
        that code that places data here adheres to the general semantics of
        the system.

        Example usage::

            LANG_KEY = __name__ + '.lang'

            def set_language(value):
                ctx = get_current_context()
                ctx.meta[LANG_KEY] = value

            def get_language():
                return get_current_context().meta.get(LANG_KEY, 'en_US')

        .. versionadded:: 5.0
        """
        return self._meta

    def make_formatter(self):
        """Creates the formatter for the help and usage output."""
        return HelpFormatter(width=self.terminal_width,
                             max_width=self.max_content_width)

    def call_on_close(self, f):
        """This decorator remembers a function as callback that should be
        executed when the context tears down.  This is most useful to bind
        resource handling to the script execution.  For instance, file objects
        opened by the :class:`File` type will register their close callbacks
        here.

        :param f: the function to execute on teardown.
        """
        self._close_callbacks.append(f)
        return f

    def close(self):
        """Invokes all close callbacks."""
        for cb in self._close_callbacks:
            cb()
        self._close_callbacks = []

    @property
    def command_path(self):
        """The computed command path.  This is used for the ``usage``
        information on the help page.  It's automatically created by
        combining the info names of the chain of contexts to the root.
        """
        rv = ''
        if self.info_name is not None:
            rv = self.info_name
        if self.parent is not None:
            rv = self.parent.command_path + ' ' + rv
        return rv.lstrip()

    def find_root(self):
        """Finds the outermost context."""
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def find_object(self, object_type):
        """Finds the closest object of a given type."""
        node = self
        while node is not None:
            if isinstance(node.obj, object_type):
                return node.obj
            node = node.parent

    def ensure_object(self, object_type):
        """Like :meth:`find_object` but sets the innermost object to a
        new instance of `object_type` if it does not exist.
        """
        rv = self.find_object(object_type)
        if rv is None:
            self.obj = rv = object_type()
        return rv

    def lookup_default(self, name):
        """Looks up the default for a parameter name.  This by default
        looks into the :attr:`default_map` if available.
        """
        if self.default_map is not None:
            rv = self.default_map.get(name)
            if callable(rv):
                rv = rv()
            return rv

    def fail(self, message):
        """Aborts the execution of the program with a specific error
        message.

        :param message: the error message to fail with.
        """
        raise UsageError(message, self)

    def abort(self):
        """Aborts the script."""
        raise Abort()

    def exit(self, code=0):
        """Exits the application with a given exit code."""
        raise Exit(code)

    def get_usage(self):
        """Helper method to get formatted usage string for the current
        context and command.
        """
        return self.command.get_usage(self)

    def get_help(self):
        """Helper method to get formatted help page for the current
        context and command.
        """
        return self.command.get_help(self)

    def invoke(*args, **kwargs):
        """Invokes a command callback in exactly the way it expects.  There
        are two ways to invoke this method:

        1.  the first argument can be a callback and all other arguments and
            keyword arguments are forwarded directly to the function.
        2.  the first argument is a click command object.  In that case all
            arguments are forwarded as well but proper click parameters
            (options and click arguments) must be keyword arguments and Click
            will fill in defaults.

        Note that before Click 3.2 keyword arguments were not properly filled
        in against the intention of this code and no context was created.  For
        more information about this change and why it was done in a bugfix
        release see :ref:`upgrade-to-3.2`.
        """
        self, callback = args[:2]
        ctx = self

        # It's also possible to invoke another command which might or
        # might not have a callback.  In that case we also fill
        # in defaults and make a new context for this command.
        if isinstance(callback, Command):
            other_cmd = callback
            callback = other_cmd.callback
            ctx = Context(other_cmd, info_name=other_cmd.name, parent=self)
            if callback is None:
                raise TypeError('The given command does not have a '
                                'callback that can be invoked.')

            for param in other_cmd.params:
                if param.name not in kwargs and param.expose_value:
                    kwargs[param.name] = param.get_default(ctx)

        args = args[2:]
        with augment_usage_errors(self):
            with ctx:
                return callback(*args, **kwargs)

    def forward(*args, **kwargs):
        """Similar to :meth:`invoke` but fills in default keyword
        arguments from the current context if the other command expects
        it.  This cannot invoke callbacks directly, only other commands.
        """
        self, cmd = args[:2]

        # It's also possible to invoke another command which might or
        # might not have a callback.
        if not isinstance(cmd, Command):
            raise TypeError('Callback is not a command.')

        for param in self.params:
            if param not in kwargs:
                kwargs[param] = self.params[param]

        return self.invoke(cmd, **kwargs)

    def set_parameter_source(self, name, source):
        """Set the source of a parameter.

        This indicates the location from which the value of the
        parameter was obtained.

        :param name: the name of the command line parameter
        :param source: the source of the command line parameter, which
                       should be a valid ParameterSource value
        """
        ParameterSource.validate(source)
        self._source_by_paramname[name] = source

    def get_parameter_source(self, name):
        """Get the source of a parameter.

        This indicates the location from which the value of the
        parameter was obtained.  This can be useful for determining
        when a user specified an option on the command line that is
        the same as the default.  In that case, the source would be
        ParameterSource.COMMANDLINE, even though the value of the
        parameter was equivalent to the default.

        :param name: the name of the command line parameter
        :returns: the source
        :rtype: ParameterSource
        """
        return self._source_by_paramname[name]


class BaseCommand(object):
    """基础命令类实现了命令最小化的 API 协议。
    大部分代码永远不会使用这个类，因为没有部署大量有用的功能，
    本类只扮演了基类的角色，直接作为子类的父类来用，另外语法分析
    方法不依赖 Click 的语法分析器。

    例如，可以用本类来作为 Click 和其它系统之间的桥梁，就像
    argparse 库或 docopt 库。

    由于基类不实现大量 Click 其它部分许可使用的 API 接口，
    所以基类都不支持所有操作。例如，基类不能与装饰器一起使用，
    并且基类也没有内置回调系统。

    .. versionchanged:: 2.0
       其中增加了 `context_settings` 参数。

    :param name: 要使用的命令名，除非一个群组命令覆写它。
    :param context_settings: 一个字典数据类型值，默认都会提供给语境对象。
    """
    #: the default for the :attr:`Context.allow_extra_args` flag.
    allow_extra_args = False
    #: the default for the :attr:`Context.allow_interspersed_args` flag.
    allow_interspersed_args = True
    #: the default for the :attr:`Context.ignore_unknown_options` flag.
    ignore_unknown_options = False

    def __init__(self, name, context_settings=None):
        #: the name the command thinks it has.  Upon registering a command
        #: on a :class:`Group` the group will default the command name
        #: with this information.  You should instead use the
        #: :class:`Context`\'s :attr:`~Context.info_name` attribute.
        self.name = name
        if context_settings is None:
            context_settings = {}
        #: an optional dictionary with defaults passed to the context.
        self.context_settings = context_settings

    def get_usage(self, ctx):
        raise NotImplementedError('Base commands cannot get usage')

    def get_help(self, ctx):
        raise NotImplementedError('Base commands cannot get help')

    def make_context(self, info_name, args, parent=None, **extra):
        """This function when given an info name and arguments will kick
        off the parsing and create a new :class:`Context`.  It does not
        invoke the actual command callback though.

        :param info_name: the info name for this invokation.  Generally this
                          is the most descriptive name for the script or
                          command.  For the toplevel script it's usually
                          the name of the script, for commands below it it's
                          the name of the script.
        :param args: the arguments to parse as list of strings.
        :param parent: the parent context if available.
        :param extra: extra keyword arguments forwarded to the context
                      constructor.
        """
        for key, value in iteritems(self.context_settings):
            if key not in extra:
                extra[key] = value
        ctx = Context(self, info_name=info_name, parent=parent, **extra)
        with ctx.scope(cleanup=False):
            self.parse_args(ctx, args)
        return ctx

    def parse_args(self, ctx, args):
        """Given a context and a list of arguments this creates the parser
        and parses the arguments, then modifies the context as necessary.
        This is automatically invoked by :meth:`make_context`.
        """
        raise NotImplementedError('Base commands do not know how to parse '
                                  'arguments.')

    def invoke(self, ctx):
        """Given a context, this invokes the command.  The default
        implementation is raising a not implemented error.
        """
        raise NotImplementedError('Base commands are not invokable by default')

    def main(self, args=None, prog_name=None, complete_var=None,
             standalone_mode=True, **extra):
        """This is the way to invoke a script with all the bells and
        whistles as a command line application.  This will always terminate
        the application after a call.  If this is not wanted, ``SystemExit``
        needs to be caught.

        This method is also available by directly calling the instance of
        a :class:`Command`.

        .. versionadded:: 3.0
           Added the `standalone_mode` flag to control the standalone mode.

        :param args: the arguments that should be used for parsing.  If not
                     provided, ``sys.argv[1:]`` is used.
        :param prog_name: the program name that should be used.  By default
                          the program name is constructed by taking the file
                          name from ``sys.argv[0]``.
        :param complete_var: the environment variable that controls the
                             bash completion support.  The default is
                             ``"_<prog_name>_COMPLETE"`` with prog_name in
                             uppercase.
        :param standalone_mode: the default behavior is to invoke the script
                                in standalone mode.  Click will then
                                handle exceptions and convert them into
                                error messages and the function will never
                                return but shut down the interpreter.  If
                                this is set to `False` they will be
                                propagated to the caller and the return
                                value of this function is the return value
                                of :meth:`invoke`.
        :param extra: extra keyword arguments are forwarded to the context
                      constructor.  See :class:`Context` for more information.
        """
        # If we are in Python 3, we will verify that the environment is
        # sane at this point or reject further execution to avoid a
        # broken script.
        if not PY2:
            _verify_python3_env()
        else:
            _check_for_unicode_literals()

        if args is None:
            args = get_os_args()
        else:
            args = list(args)

        if prog_name is None:
            prog_name = make_str(os.path.basename(
                sys.argv and sys.argv[0] or __file__))

        # Hook for the Bash completion.  This only activates if the Bash
        # completion is actually enabled, otherwise this is quite a fast
        # noop.
        _bashcomplete(self, prog_name, complete_var)

        try:
            try:
                with self.make_context(prog_name, args, **extra) as ctx:
                    rv = self.invoke(ctx)
                    if not standalone_mode:
                        return rv
                    # it's not safe to `ctx.exit(rv)` here!
                    # note that `rv` may actually contain data like "1" which
                    # has obvious effects
                    # more subtle case: `rv=[None, None]` can come out of
                    # chained commands which all returned `None` -- so it's not
                    # even always obvious that `rv` indicates success/failure
                    # by its truthiness/falsiness
                    ctx.exit()
            except (EOFError, KeyboardInterrupt):
                echo(file=sys.stderr)
                raise Abort()
            except ClickException as e:
                if not standalone_mode:
                    raise
                e.show()
                sys.exit(e.exit_code)
            except IOError as e:
                if e.errno == errno.EPIPE:
                    sys.stdout = PacifyFlushWrapper(sys.stdout)
                    sys.stderr = PacifyFlushWrapper(sys.stderr)
                    sys.exit(1)
                else:
                    raise
        except Exit as e:
            if standalone_mode:
                sys.exit(e.exit_code)
            else:
                # in non-standalone mode, return the exit code
                # note that this is only reached if `self.invoke` above raises
                # an Exit explicitly -- thus bypassing the check there which
                # would return its result
                # the results of non-standalone execution may therefore be
                # somewhat ambiguous: if there are codepaths which lead to
                # `ctx.exit(1)` and to `return 1`, the caller won't be able to
                # tell the difference between the two
                return e.exit_code
        except Abort:
            if not standalone_mode:
                raise
            echo('Aborted!', file=sys.stderr)
            sys.exit(1)

    def __call__(self, *args, **kwargs):
        """Alias for :meth:`main`."""
        return self.main(*args, **kwargs)


class Command(BaseCommand):
    """本类是 Click 中命令行接口的基础建筑块。
    一个基础命令处理命令行语法分析，并且调度更多
    的语法分析作用在嵌入式命令上。

    .. versionchanged:: 2.0
       其中增加了 `context_settings` 参数。
    .. versionchanged:: 8.0
       其中增加了 repr 命令名显示形式。
    .. versionchanged:: 7.1
       其中增加了 `no_args_is_help` 参数。

    :param name: 要使用的命令名，除非一个群组命令覆写它。
    :param context_settings: 一个字典数据类型，默认提供给语境对象。
    :param callback: 要触发的回调。可选可不选。
    :param params: 注册给这个命令的参数。即可以是 :class:`Option` 
                   也可以是 :class:`Argument` 对象。
    :param help: 这个命令要使用的帮助页面字符串。
    :param epilog: 类似帮助字符串，但显示在帮助页面最后位置。
    :param short_help: 这个命令要使用的简短帮助字符串。这会显示在
                       父命令的命令清单上。
    :param add_help_option: 默认给每个命令注册一个 ``--help`` 可选项。
                            通过这个参数可以显示。
    :param no_args_is_help: 这是控制如果不提供多个参数时的情况。
                            默认会显示这个选项。如果开启这个参数
                            没有多个参数代入的话会把 ``--help``
                            增加成参数。
    :param hidden: 隐藏这个命令，不显示在帮助输出中。

    :param deprecated: 发布一条消息说明命令已经被淘汰了。
    """

    def __init__(self, name, context_settings=None, callback=None,
                 params=None, help=None, epilog=None, short_help=None,
                 options_metavar='[OPTIONS]', add_help_option=True,
                 no_args_is_help=False, hidden=False, deprecated=False):
        BaseCommand.__init__(self, name, context_settings)
        #: the callback to execute when the command fires.  This might be
        #: `None` in which case nothing happens.
        self.callback = callback
        #: the list of parameters for this command in the order they
        #: should show up in the help page and execute.  Eager parameters
        #: will automatically be handled before non eager ones.
        self.params = params or []
        # if a form feed (page break) is found in the help text, truncate help
        # text to the content preceding the first form feed
        if help and '\f' in help:
            help = help.split('\f', 1)[0]
        self.help = help
        self.epilog = epilog
        self.options_metavar = options_metavar
        self.short_help = short_help
        self.add_help_option = add_help_option
        self.no_args_is_help = no_args_is_help
        self.hidden = hidden
        self.deprecated = deprecated

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    def get_usage(self, ctx):
        """Formats the usage line into a string and returns it.

        Calls :meth:`format_usage` internally.
        """
        formatter = ctx.make_formatter()
        self.format_usage(ctx, formatter)
        return formatter.getvalue().rstrip('\n')

    def get_params(self, ctx):
        rv = self.params
        help_option = self.get_help_option(ctx)
        if help_option is not None:
            rv = rv + [help_option]
        return rv

    def format_usage(self, ctx, formatter):
        """Writes the usage line into the formatter.

        This is a low-level method called by :meth:`get_usage`.
        """
        pieces = self.collect_usage_pieces(ctx)
        formatter.write_usage(ctx.command_path, ' '.join(pieces))

    def collect_usage_pieces(self, ctx):
        """Returns all the pieces that go into the usage line and returns
        it as a list of strings.
        """
        rv = [self.options_metavar]
        for param in self.get_params(ctx):
            rv.extend(param.get_usage_pieces(ctx))
        return rv

    def get_help_option_names(self, ctx):
        """Returns the names for the help option."""
        all_names = set(ctx.help_option_names)
        for param in self.params:
            all_names.difference_update(param.opts)
            all_names.difference_update(param.secondary_opts)
        return all_names

    def get_help_option(self, ctx):
        """Returns the help option object."""
        help_options = self.get_help_option_names(ctx)
        if not help_options or not self.add_help_option:
            return

        def show_help(ctx, param, value):
            if value and not ctx.resilient_parsing:
                echo(ctx.get_help(), color=ctx.color)
                ctx.exit()
        return Option(help_options, is_flag=True,
                      is_eager=True, expose_value=False,
                      callback=show_help,
                      help='Show this message and exit.')

    def make_parser(self, ctx):
        """Creates the underlying option parser for this command."""
        parser = OptionParser(ctx)
        for param in self.get_params(ctx):
            param.add_to_parser(parser, ctx)
        return parser

    def get_help(self, ctx):
        """Formats the help into a string and returns it.

        Calls :meth:`format_help` internally.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip('\n')

    def get_short_help_str(self, limit=45):
        """Gets short help for the command or makes it by shortening the long help string."""
        return self.short_help or self.help and make_default_short_help(self.help, limit) or ''

    def format_help(self, ctx, formatter):
        """Writes the help into the formatter if it exists.

        This is a low-level method called by :meth:`get_help`.

        This calls the following methods:

        -   :meth:`format_usage`
        -   :meth:`format_help_text`
        -   :meth:`format_options`
        -   :meth:`format_epilog`
        """
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(self, ctx, formatter):
        """Writes the help text to the formatter if it exists."""
        if self.help:
            formatter.write_paragraph()
            with formatter.indentation():
                help_text = self.help
                if self.deprecated:
                    help_text += DEPRECATED_HELP_NOTICE
                formatter.write_text(help_text)
        elif self.deprecated:
            formatter.write_paragraph()
            with formatter.indentation():
                formatter.write_text(DEPRECATED_HELP_NOTICE)

    def format_options(self, ctx, formatter):
        """Writes all the options into the formatter if they exist."""
        opts = []
        for param in self.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is not None:
                opts.append(rv)

        if opts:
            with formatter.section('Options'):
                formatter.write_dl(opts)

    def format_epilog(self, ctx, formatter):
        """Writes the epilog into the formatter if it exists."""
        if self.epilog:
            formatter.write_paragraph()
            with formatter.indentation():
                formatter.write_text(self.epilog)

    def parse_args(self, ctx, args):
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            echo(ctx.get_help(), color=ctx.color)
            ctx.exit()

        parser = self.make_parser(ctx)
        opts, args, param_order = parser.parse_args(args=args)

        for param in iter_params_for_processing(
                param_order, self.get_params(ctx)):
            value, args = param.handle_parse_result(ctx, opts, args)

        if args and not ctx.allow_extra_args and not ctx.resilient_parsing:
            ctx.fail('Got unexpected extra argument%s (%s)'
                     % (len(args) != 1 and 's' or '',
                        ' '.join(map(make_str, args))))

        ctx.args = args
        return args

    def invoke(self, ctx):
        """Given a context, this invokes the attached callback (if it exists)
        in the right way.
        """
        _maybe_show_deprecated_notice(self)
        if self.callback is not None:
            return ctx.invoke(self.callback, **ctx.params)


class MultiCommand(Command):
    """多命令是一种命令的基础实现，它调度成子命令。
    最共性的版本就是用于 :class:`Group` 类。

    :param invoke_without_command: 这是控制多命令自身是如何被触发的。
                                   如果提供了一个子命令，默认被触发。
    :param no_args_is_help: 这是控制如果不提供多参数会发生什么。
                            如果 `invoke_without_command` 被禁用，
                            默认开启这个选项，反之否然。如果开启这个参数
                            如果没有多参数代入的话，会把 ``--help`` 
                            作为参数加入。
    :param subcommand_metavar: 用在文档中的字符串，说明子命令的位置。
    :param chain: 如果设置成 `True` 的话，多个子命令锁链就被开启。
                  这会限制命令的形式，命令不能有可选项参数，但允许有
                  多命令串联在一起。
    :param result_callback: 提供给这个多命令的回调结果。
    """
    allow_extra_args = True
    allow_interspersed_args = False

    def __init__(self, name=None, invoke_without_command=False,
                 no_args_is_help=None, subcommand_metavar=None,
                 chain=False, result_callback=None, **attrs):
        Command.__init__(self, name, **attrs)
        if no_args_is_help is None:
            no_args_is_help = not invoke_without_command
        self.no_args_is_help = no_args_is_help
        self.invoke_without_command = invoke_without_command
        if subcommand_metavar is None:
            if chain:
                subcommand_metavar = SUBCOMMANDS_METAVAR
            else:
                subcommand_metavar = SUBCOMMAND_METAVAR
        self.subcommand_metavar = subcommand_metavar
        self.chain = chain
        #: The result callback that is stored.  This can be set or
        #: overridden with the :func:`resultcallback` decorator.
        self.result_callback = result_callback

        if self.chain:
            for param in self.params:
                if isinstance(param, Argument) and not param.required:
                    raise RuntimeError('Multi commands in chain mode cannot '
                                       'have optional arguments.')

    def collect_usage_pieces(self, ctx):
        rv = Command.collect_usage_pieces(self, ctx)
        rv.append(self.subcommand_metavar)
        return rv

    def format_options(self, ctx, formatter):
        Command.format_options(self, ctx, formatter)
        self.format_commands(ctx, formatter)

    def resultcallback(self, replace=False):
        """Adds a result callback to the chain command.  By default if a
        result callback is already registered this will chain them but
        this can be disabled with the `replace` parameter.  The result
        callback is invoked with the return value of the subcommand
        (or the list of return values from all subcommands if chaining
        is enabled) as well as the parameters as they would be passed
        to the main callback.

        Example::

            @click.group()
            @click.option('-i', '--input', default=23)
            def cli(input):
                return 42

            @cli.resultcallback()
            def process_result(result, input):
                return result + input

        .. versionadded:: 3.0

        :param replace: if set to `True` an already existing result
                        callback will be removed.
        """
        def decorator(f):
            old_callback = self.result_callback
            if old_callback is None or replace:
                self.result_callback = f
                return f
            def function(__value, *args, **kwargs):
                return f(old_callback(__value, *args, **kwargs),
                         *args, **kwargs)
            self.result_callback = rv = update_wrapper(function, f)
            return rv
        return decorator

    def format_commands(self, ctx, formatter):
        """Extra format methods for multi methods that adds all the commands
        after the options.
        """
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            rows = []
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))

            if rows:
                with formatter.section('Commands'):
                    formatter.write_dl(rows)

    def parse_args(self, ctx, args):
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            echo(ctx.get_help(), color=ctx.color)
            ctx.exit()

        rest = Command.parse_args(self, ctx, args)
        if self.chain:
            ctx.protected_args = rest
            ctx.args = []
        elif rest:
            ctx.protected_args, ctx.args = rest[:1], rest[1:]

        return ctx.args

    def invoke(self, ctx):
        def _process_result(value):
            if self.result_callback is not None:
                value = ctx.invoke(self.result_callback, value,
                                   **ctx.params)
            return value

        if not ctx.protected_args:
            # If we are invoked without command the chain flag controls
            # how this happens.  If we are not in chain mode, the return
            # value here is the return value of the command.
            # If however we are in chain mode, the return value is the
            # return value of the result processor invoked with an empty
            # list (which means that no subcommand actually was executed).
            if self.invoke_without_command:
                if not self.chain:
                    return Command.invoke(self, ctx)
                with ctx:
                    Command.invoke(self, ctx)
                    return _process_result([])
            ctx.fail('Missing command.')

        # Fetch args back out
        args = ctx.protected_args + ctx.args
        ctx.args = []
        ctx.protected_args = []

        # If we're not in chain mode, we only allow the invocation of a
        # single command but we also inform the current context about the
        # name of the command to invoke.
        if not self.chain:
            # Make sure the context is entered so we do not clean up
            # resources until the result processor has worked.
            with ctx:
                cmd_name, cmd, args = self.resolve_command(ctx, args)
                ctx.invoked_subcommand = cmd_name
                Command.invoke(self, ctx)
                sub_ctx = cmd.make_context(cmd_name, args, parent=ctx)
                with sub_ctx:
                    return _process_result(sub_ctx.command.invoke(sub_ctx))

        # In chain mode we create the contexts step by step, but after the
        # base command has been invoked.  Because at that point we do not
        # know the subcommands yet, the invoked subcommand attribute is
        # set to ``*`` to inform the command that subcommands are executed
        # but nothing else.
        with ctx:
            ctx.invoked_subcommand = args and '*' or None
            Command.invoke(self, ctx)

            # Otherwise we make every single context and invoke them in a
            # chain.  In that case the return value to the result processor
            # is the list of all invoked subcommand's results.
            contexts = []
            while args:
                cmd_name, cmd, args = self.resolve_command(ctx, args)
                sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                                           allow_extra_args=True,
                                           allow_interspersed_args=False)
                contexts.append(sub_ctx)
                args, sub_ctx.args = sub_ctx.args, []

            rv = []
            for sub_ctx in contexts:
                with sub_ctx:
                    rv.append(sub_ctx.command.invoke(sub_ctx))
            return _process_result(rv)

    def resolve_command(self, ctx, args):
        cmd_name = make_str(args[0])
        original_cmd_name = cmd_name

        # Get the command
        cmd = self.get_command(ctx, cmd_name)

        # If we can't find the command but there is a normalization
        # function available, we try with that one.
        if cmd is None and ctx.token_normalize_func is not None:
            cmd_name = ctx.token_normalize_func(cmd_name)
            cmd = self.get_command(ctx, cmd_name)

        # If we don't find the command we want to show an error message
        # to the user that it was not provided.  However, there is
        # something else we should do: if the first argument looks like
        # an option we want to kick off parsing again for arguments to
        # resolve things like --help which now should go to the main
        # place.
        if cmd is None and not ctx.resilient_parsing:
            if split_opt(cmd_name)[0]:
                self.parse_args(ctx, ctx.args)
            ctx.fail('No such command "%s".' % original_cmd_name)

        return cmd_name, cmd, args[1:]

    def get_command(self, ctx, cmd_name):
        """Given a context and a command name, this returns a
        :class:`Command` object if it exists or returns `None`.
        """
        raise NotImplementedError()

    def list_commands(self, ctx):
        """Returns a list of subcommand names in the order they should
        appear.
        """
        return []


class Group(MultiCommand):
    """一个群组命令类，允许一个主命令有许多子命令在其后。
    最共性的方法就是在 Click 中部署嵌入式命令。

    :param commands: 许多命令组成的一个字典数据类型。
    """

    def __init__(self, name=None, commands=None, **attrs):
        MultiCommand.__init__(self, name, **attrs)
        #: the registered subcommands by their exported names.
        self.commands = commands or {}

    def add_command(self, cmd, name=None):
        """Registers another :class:`Command` with this group.  If the name
        is not provided, the name of the command is used.
        """
        name = name or cmd.name
        if name is None:
            raise TypeError('Command has no name.')
        _check_multicommand(self, name, cmd, register=True)
        self.commands[name] = cmd

    def command(self, *args, **kwargs):
        """一个用来声明一个命令和把一个命令加入群组的快捷装饰器。
        本装饰器得到的参数与 :func:`command` 函数一样，但通过
        调用 :meth:`add_command` 方法立即注册含有本类实例的
        已建立完的命令。
        """
        def decorator(f):
            cmd = command(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd
        return decorator

    def group(self, *args, **kwargs):
        """为声明和把一个群组加入到群组中的一种快捷装饰器。
        本装饰器得到的参数与 :func:`group` 函数一样，但
        通过调用 :meth:`add_command` 方法立即注册含有
        本类实例的已建立完的命令。
        """
        def decorator(f):
            cmd = group(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd
        return decorator

    def get_command(self, ctx, cmd_name):
        return self.commands.get(cmd_name)

    def list_commands(self, ctx):
        return sorted(self.commands)


class CommandCollection(MultiCommand):
    """一个命令收集类是把多个多命令合并成一个多命令的类。
    本类直接实现了接收不同多命令形成的一个列表作为源头，
    并且提供所有的命令给每个多命令。
    """

    def __init__(self, name=None, sources=None, **attrs):
        MultiCommand.__init__(self, name, **attrs)
        #: The list of registered multi commands.
        self.sources = sources or []

    def add_source(self, multi_cmd):
        """Adds a new multi command to the chain dispatcher."""
        self.sources.append(multi_cmd)

    def get_command(self, ctx, cmd_name):
        for source in self.sources:
            rv = source.get_command(ctx, cmd_name)
            if rv is not None:
                if self.chain:
                    _check_multicommand(self, cmd_name, rv)
                return rv

    def list_commands(self, ctx):
        rv = set()
        for source in self.sources:
            rv.update(source.list_commands(ctx))
        return sorted(rv)


class Parameter(object):
    r"""提供给命令的一种参数形式，有 2 个版本。
    参数形式即可以是 :class:`Option` 类，也可以是 :class:`Argument` 类。
    其它子类目前都不支持，由于设计的一些内部语法分析在内部还没有完成。

    一些配置都是通过可选项和参数来支持的。

    .. versionchanged:: 2.0
       对参数形式回调足够的变更，也可以代入到参数形式中了。
       在 Click 2.0 版本中，老旧的回调格式依然有效，但
       会抛出一个警告，可以变成更容易的代码格式。

    :param param_decls: 针对可选项或参数的参数形式声明。
                        这是一个旗语组成的列表，或参数名组成的列表。
    :param type: 你应该使用的类型。既可以是一个 :class:`ParamType`
                 也可以是一个 Python 类型。对于 Python 类型来说如果
                 支持的话，会自动转换成前者的形式。
    :param required: 控制是否是可选的。
    :param default: 如果命令行不使用参数形式的话，会使用默认值。
                    当设置默认值时，也可以是一个可调用对象。
    :param callback: 一个回调函数，参数形式匹配上以后才会执行回调函数。
                     回调函数定义成 ``fn(ctx, param, value)`` 样式，
                     并且要返回 `value` 这个参数。在 Click 2.0 以前，
                     回调函数的信号曾是 ``(ctx, value)`` 形式。
    :param nargs: 要匹配的参数数量。如果设置的不是 ``1`` 返回值是一个元组，
                  就不再是单个值的信号了。默认是 ``1`` (除了类型是一个元组
                  的话，那么这个参数值就是元组的长度)。如果 ``nargs=-1`` 
                  的话，对可选项来说会抛出类型错误。
    :param metavar: 在帮助页面中如何显示值。
    :param expose_value: 如果设置成 `True` 的话，那么值会提供给命令回调后
                         存储在语境上，否则会跳过。
    :param is_eager: 期望值都会在非期望值之前进行处理。
                     这个参数不应该设置给参数，否则会
                     把处理顺序变成逆序。
    :param envvar: 一个字符串或字符串组成的一个列表。
                   内容都是应该被检查的环境变量名。
    """
    param_type_name = 'parameter'

    def __init__(self, param_decls=None, type=None, required=False,
                 default=None, callback=None, nargs=None, metavar=None,
                 expose_value=True, is_eager=False, envvar=None,
                 autocompletion=None):
        self.name, self.opts, self.secondary_opts = \
            self._parse_decls(param_decls or (), expose_value)

        self.type = convert_type(type, default)

        # Default nargs to what the type tells us if we have that
        # information available.
        if nargs is None:
            if self.type.is_composite:
                nargs = self.type.arity
            else:
                nargs = 1

        self.required = required
        self.callback = callback
        self.nargs = nargs
        self.multiple = False
        self.expose_value = expose_value
        self.default = default
        self.is_eager = is_eager
        self.metavar = metavar
        self.envvar = envvar
        self.autocompletion = autocompletion

    @property
    def human_readable_name(self):
        """返回适合人类阅读的参数形式名字。
        与可选项名一样，但参数名会是 metavar 形式。
        """
        return self.name

    def make_metavar(self):
        if self.metavar is not None:
            return self.metavar
        metavar = self.type.get_metavar(self)
        if metavar is None:
            metavar = self.type.name.upper()
        if self.nargs != 1:
            metavar += '...'
        return metavar

    def get_default(self, ctx):
        """Given a context variable this calculates the default value."""
        # Otherwise go with the regular default.
        if callable(self.default):
            rv = self.default()
        else:
            rv = self.default
        return self.type_cast_value(ctx, rv)

    def add_to_parser(self, parser, ctx):
        pass

    def consume_value(self, ctx, opts):
        value = opts.get(self.name)
        source = ParameterSource.COMMANDLINE
        if value is None:
            value = self.value_from_envvar(ctx)
            source = ParameterSource.ENVIRONMENT
        if value is None:
            value = ctx.lookup_default(self.name)
            source = ParameterSource.DEFAULT_MAP
        if value is not None:
            ctx.set_parameter_source(self.name, source)
        return value

    def type_cast_value(self, ctx, value):
        """Given a value this runs it properly through the type system.
        This automatically handles things like `nargs` and `multiple` as
        well as composite types.
        """
        if self.type.is_composite:
            if self.nargs <= 1:
                raise TypeError('Attempted to invoke composite type '
                                'but nargs has been set to %s.  This is '
                                'not supported; nargs needs to be set to '
                                'a fixed value > 1.' % self.nargs)
            if self.multiple:
                return tuple(self.type(x or (), self, ctx) for x in value or ())
            return self.type(value or (), self, ctx)

        def _convert(value, level):
            if level == 0:
                return self.type(value, self, ctx)
            return tuple(_convert(x, level - 1) for x in value or ())
        return _convert(value, (self.nargs != 1) + bool(self.multiple))

    def process_value(self, ctx, value):
        """Given a value and context this runs the logic to convert the
        value as necessary.
        """
        # If the value we were given is None we do nothing.  This way
        # code that calls this can easily figure out if something was
        # not provided.  Otherwise it would be converted into an empty
        # tuple for multiple invocations which is inconvenient.
        if value is not None:
            return self.type_cast_value(ctx, value)

    def value_is_missing(self, value):
        if value is None:
            return True
        if (self.nargs != 1 or self.multiple) and value == ():
            return True
        return False

    def full_process_value(self, ctx, value):
        value = self.process_value(ctx, value)

        if value is None and not ctx.resilient_parsing:
            value = self.get_default(ctx)
            if value is not None:
                ctx.set_parameter_source(self.name, ParameterSource.DEFAULT)

        if self.required and self.value_is_missing(value):
            raise MissingParameter(ctx=ctx, param=self)

        return value

    def resolve_envvar_value(self, ctx):
        if self.envvar is None:
            return
        if isinstance(self.envvar, (tuple, list)):
            for envvar in self.envvar:
                rv = os.environ.get(envvar)
                if rv is not None:
                    return rv
        else:
            return os.environ.get(self.envvar)

    def value_from_envvar(self, ctx):
        rv = self.resolve_envvar_value(ctx)
        if rv is not None and self.nargs != 1:
            rv = self.type.split_envvar_value(rv)
        return rv

    def handle_parse_result(self, ctx, opts, args):
        with augment_usage_errors(ctx, param=self):
            value = self.consume_value(ctx, opts)
            try:
                value = self.full_process_value(ctx, value)
            except Exception:
                if not ctx.resilient_parsing:
                    raise
                value = None
            if self.callback is not None:
                try:
                    value = invoke_param_callback(
                        self.callback, ctx, self, value)
                except Exception:
                    if not ctx.resilient_parsing:
                        raise

        if self.expose_value:
            ctx.params[self.name] = value
        return value, args

    def get_help_record(self, ctx):
        pass

    def get_usage_pieces(self, ctx):
        return []

    def get_error_hint(self, ctx):
        """Get a stringified version of the param for use in error messages to
        indicate which param caused the error.
        """
        hint_list = self.opts or [self.human_readable_name]
        return ' / '.join('"%s"' % x for x in hint_list)


class Option(Parameter):
    """可选项类都常常是命令行中可选项的值。
    并且有些额外特性是参数类所有没有的。

    所有其它参数都代入到参数形式构造器中。

    :param show_default: 控制默认值是否要显示在帮助页面上。
                         正常情况，默认值是不限时的。如果
                         设置的值是一个字符串的话，显示的
                         是字符串而不是值了。对于动态可选项
                         来说这是特别有用。
    :param show_envvar: 控制一个环境变量是否应该显示在帮助
                        页面上。正常来说，不显示环境变量。
    :param prompt: 如果设置成 `True` 或一种非空字符串的话，
                   那么在用户输入时会提示给用户。设置成 `True` 
                   时，提示的会是首字母大写的可选项名字。
    :param confirmation_prompt: 如果设置的话，会需要对输入进行再次确认提示。
    :param hide_input: 如果设置成 `True` 在提示输入时隐藏用户的输入内容。
                       对于输入密码时是有用的。
    :param is_flag: 让可选项扮演一个旗语的角色。默认是自动检测的。
    :param flag_value: 如果开启旗语功能的话，设置旗语值。
                       如果可选项字符串中含有一个斜杠来
                       分隔两项的话，会自动设置成布尔值。
    :param multiple: 如果设置成 `True` 那么参数会被接收很多次并记录下来。
                     这类似 ``nargs`` 参数，但支持任意参数数量。
    :param count: 开启这个旗语会让一个可选项变成一个增量计数结果，用来计算使用了多少次。
    :param allow_from_autoenv: 如果开启的话，参数形式的值会从环境变量中获得，
                               这种情况下，在语境上会定义一个前缀。
    :param help: 帮助字符串。
    :param hidden: 在帮助输出中隐藏这个可选项。
    """
    param_type_name = 'option'

    def __init__(self, param_decls=None, show_default=False,
                 prompt=False, confirmation_prompt=False,
                 hide_input=False, is_flag=None, flag_value=None,
                 multiple=False, count=False, allow_from_autoenv=True,
                 type=None, help=None, hidden=False, show_choices=True,
                 show_envvar=False, **attrs):
        default_is_missing = attrs.get('default', _missing) is _missing
        Parameter.__init__(self, param_decls, type=type, **attrs)

        if prompt is True:
            prompt_text = self.name.replace('_', ' ').capitalize()
        elif prompt is False:
            prompt_text = None
        else:
            prompt_text = prompt
        self.prompt = prompt_text
        self.confirmation_prompt = confirmation_prompt
        self.hide_input = hide_input
        self.hidden = hidden

        # Flags
        if is_flag is None:
            if flag_value is not None:
                is_flag = True
            else:
                is_flag = bool(self.secondary_opts)
        if is_flag and default_is_missing:
            self.default = False
        if flag_value is None:
            flag_value = not self.default
        self.is_flag = is_flag
        self.flag_value = flag_value
        if self.is_flag and isinstance(self.flag_value, bool) \
           and type is None:
            self.type = BOOL
            self.is_bool_flag = True
        else:
            self.is_bool_flag = False

        # Counting
        self.count = count
        if count:
            if type is None:
                self.type = IntRange(min=0)
            if default_is_missing:
                self.default = 0

        self.multiple = multiple
        self.allow_from_autoenv = allow_from_autoenv
        self.help = help
        self.show_default = show_default
        self.show_choices = show_choices
        self.show_envvar = show_envvar

        # Sanity check for stuff we don't support
        if __debug__:
            if self.nargs < 0:
                raise TypeError('Options cannot have nargs < 0')
            if self.prompt and self.is_flag and not self.is_bool_flag:
                raise TypeError('Cannot prompt for flags that are not bools.')
            if not self.is_bool_flag and self.secondary_opts:
                raise TypeError('Got secondary option for non boolean flag.')
            if self.is_bool_flag and self.hide_input \
               and self.prompt is not None:
                raise TypeError('Hidden input does not work with boolean '
                                'flag prompts.')
            if self.count:
                if self.multiple:
                    raise TypeError('Options cannot be multiple and count '
                                    'at the same time.')
                elif self.is_flag:
                    raise TypeError('Options cannot be count and flags at '
                                    'the same time.')

    def _parse_decls(self, decls, expose_value):
        opts = []
        secondary_opts = []
        name = None
        possible_names = []

        for decl in decls:
            if isidentifier(decl):
                if name is not None:
                    raise TypeError('Name defined twice')
                name = decl
            else:
                split_char = decl[:1] == '/' and ';' or '/'
                if split_char in decl:
                    first, second = decl.split(split_char, 1)
                    first = first.rstrip()
                    if first:
                        possible_names.append(split_opt(first))
                        opts.append(first)
                    second = second.lstrip()
                    if second:
                        secondary_opts.append(second.lstrip())
                else:
                    possible_names.append(split_opt(decl))
                    opts.append(decl)

        if name is None and possible_names:
            possible_names.sort(key=lambda x: -len(x[0]))  # group long options first
            name = possible_names[0][1].replace('-', '_').lower()
            if not isidentifier(name):
                name = None

        if name is None:
            if not expose_value:
                return None, opts, secondary_opts
            raise TypeError('Could not determine name for option')

        if not opts and not secondary_opts:
            raise TypeError('No options defined but a name was passed (%s). '
                            'Did you mean to declare an argument instead '
                            'of an option?' % name)

        return name, opts, secondary_opts

    def add_to_parser(self, parser, ctx):
        kwargs = {
            'dest': self.name,
            'nargs': self.nargs,
            'obj': self,
        }

        if self.multiple:
            action = 'append'
        elif self.count:
            action = 'count'
        else:
            action = 'store'

        if self.is_flag:
            kwargs.pop('nargs', None)
            if self.is_bool_flag and self.secondary_opts:
                parser.add_option(self.opts, action=action + '_const',
                                  const=True, **kwargs)
                parser.add_option(self.secondary_opts, action=action +
                                  '_const', const=False, **kwargs)
            else:
                parser.add_option(self.opts, action=action + '_const',
                                  const=self.flag_value,
                                  **kwargs)
        else:
            kwargs['action'] = action
            parser.add_option(self.opts, **kwargs)

    def get_help_record(self, ctx):
        if self.hidden:
            return
        any_prefix_is_slash = []

        def _write_opts(opts):
            rv, any_slashes = join_options(opts)
            if any_slashes:
                any_prefix_is_slash[:] = [True]
            if not self.is_flag and not self.count:
                rv += ' ' + self.make_metavar()
            return rv

        rv = [_write_opts(self.opts)]
        if self.secondary_opts:
            rv.append(_write_opts(self.secondary_opts))

        help = self.help or ''
        extra = []
        if self.show_envvar:
            envvar = self.envvar
            if envvar is None:
                if self.allow_from_autoenv and \
                    ctx.auto_envvar_prefix is not None:
                    envvar = '%s_%s' % (ctx.auto_envvar_prefix, self.name.upper())
            if envvar is not None:
              extra.append('env var: %s' % (
                           ', '.join('%s' % d for d in envvar)
                           if isinstance(envvar, (list, tuple))
                           else envvar, ))
        if self.default is not None and \
            (self.show_default or ctx.show_default):
            if isinstance(self.show_default, string_types):
                default_string = '({})'.format(self.show_default)
            elif isinstance(self.default, (list, tuple)):
                default_string = ', '.join('%s' % d for d in self.default)
            elif inspect.isfunction(self.default):
                default_string = "(dynamic)"
            else:
                default_string = self.default
            extra.append('default: {}'.format(default_string))

        if self.required:
            extra.append('required')
        if extra:
            help = '%s[%s]' % (help and help + '  ' or '', '; '.join(extra))

        return ((any_prefix_is_slash and '; ' or ' / ').join(rv), help)

    def get_default(self, ctx):
        # If we're a non boolean flag out default is more complex because
        # we need to look at all flags in the same group to figure out
        # if we're the the default one in which case we return the flag
        # value as default.
        if self.is_flag and not self.is_bool_flag:
            for param in ctx.command.params:
                if param.name == self.name and param.default:
                    return param.flag_value
            return None
        return Parameter.get_default(self, ctx)

    def prompt_for_value(self, ctx):
        """This is an alternative flow that can be activated in the full
        value processing if a value does not exist.  It will prompt the
        user until a valid value exists and then returns the processed
        value as result.
        """
        # Calculate the default before prompting anything to be stable.
        default = self.get_default(ctx)

        # If this is a prompt for a flag we need to handle this
        # differently.
        if self.is_bool_flag:
            return confirm(self.prompt, default)

        return prompt(self.prompt, default=default, type=self.type,
                      hide_input=self.hide_input, show_choices=self.show_choices,
                      confirmation_prompt=self.confirmation_prompt,
                      value_proc=lambda x: self.process_value(ctx, x))

    def resolve_envvar_value(self, ctx):
        rv = Parameter.resolve_envvar_value(self, ctx)
        if rv is not None:
            return rv
        if self.allow_from_autoenv and \
           ctx.auto_envvar_prefix is not None:
            envvar = '%s_%s' % (ctx.auto_envvar_prefix, self.name.upper())
            return os.environ.get(envvar)

    def value_from_envvar(self, ctx):
        rv = self.resolve_envvar_value(ctx)
        if rv is None:
            return None
        value_depth = (self.nargs != 1) + bool(self.multiple)
        if value_depth > 0 and rv is not None:
            rv = self.type.split_envvar_value(rv)
            if self.multiple and self.nargs != 1:
                rv = batch(rv, self.nargs)
        return rv

    def full_process_value(self, ctx, value):
        if value is None and self.prompt is not None \
           and not ctx.resilient_parsing:
            return self.prompt_for_value(ctx)
        return Parameter.full_process_value(self, ctx, value)


class Argument(Parameter):
    """参数都是命令行中的位置参数形式。
    通用中，参数要比可选项提供的特性要少，但参数可以设置无限 ``nargs`` 
    不会抛出例外错误，而且默认都会使用。

    所有参数都代入到参数形式构造器中。
    """
    param_type_name = 'argument'

    def __init__(self, param_decls, required=None, **attrs):
        if required is None:
            if attrs.get('default') is not None:
                required = False
            else:
                required = attrs.get('nargs', 1) > 0
        Parameter.__init__(self, param_decls, required=required, **attrs)
        if self.default is not None and self.nargs < 0:
            raise TypeError('nargs=-1 in combination with a default value '
                            'is not supported.')

    @property
    def human_readable_name(self):
        if self.metavar is not None:
            return self.metavar
        return self.name.upper()

    def make_metavar(self):
        if self.metavar is not None:
            return self.metavar
        var = self.type.get_metavar(self)
        if not var:
            var = self.name.upper()
        if not self.required:
            var = '[%s]' % var
        if self.nargs != 1:
            var += '...'
        return var

    def _parse_decls(self, decls, expose_value):
        if not decls:
            if not expose_value:
                return None, [], []
            raise TypeError('Could not determine name for argument')
        if len(decls) == 1:
            name = arg = decls[0]
            name = name.replace('-', '_').lower()
        else:
            raise TypeError('Arguments take exactly one '
                            'parameter declaration, got %d' % len(decls))
        return name, [arg], []

    def get_usage_pieces(self, ctx):
        return [self.make_metavar()]

    def get_error_hint(self, ctx):
        return '"%s"' % self.make_metavar()

    def add_to_parser(self, parser, ctx):
        parser.add_argument(dest=self.name, nargs=self.nargs,
                            obj=self)


# Circular dependency between decorators and core
from .decorators import command, group
