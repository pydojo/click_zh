import sys
import inspect

from functools import update_wrapper

from ._compat import iteritems
from ._unicodefun import _check_for_unicode_literals
from .utils import echo
from .globals import get_current_context


def pass_context(f):
    """把一个回调函数标记成想要接收当前语境对象作为第一参数。
    """
    def new_func(*args, **kwargs):
        return f(get_current_context(), *args, **kwargs)
    return update_wrapper(new_func, f)


def pass_obj(f):
    """类似 :func:`pass_context` 函数，
    但只在语境上继续传递对象 (:attr:`Context.obj`) 属性。
    如果对象呈现一个嵌入式系统的状态的话，这个函数就有用了。
    """
    def new_func(*args, **kwargs):
        return f(get_current_context().obj, *args, **kwargs)
    return update_wrapper(new_func, f)


def make_pass_decorator(object_type, ensure=False):
    """根据一个对象类型建立一个装饰器，
    装饰器工作类似 :func:`pass_obj` 函数，
    但不传递当前语境对象，它会找到 :func:`object_type` 函数
    类型的最内部的语境。

    本函数生成的一个装饰器工作起来像下面一样::

        from functools import update_wrapper

        def decorator(f):
            @pass_context
            def new_func(ctx, *args, **kwargs):
                obj = ctx.find_object(object_type)
                return ctx.invoke(f, obj, *args, **kwargs)
            return update_wrapper(new_func, f)
        return decorator

    :param object_type: 要传递的对象类型。
    :param ensure: 如果设置成 `True` 的话，一个新对象会被建立，
                   并且在语境中会被记住，反之否然。
    """
    def decorator(f):
        def new_func(*args, **kwargs):
            ctx = get_current_context()
            if ensure:
                obj = ctx.ensure_object(object_type)
            else:
                obj = ctx.find_object(object_type)
            if obj is None:
                raise RuntimeError('Managed to invoke callback without a '
                                   'context object of type %r existing'
                                   % object_type.__name__)
            return ctx.invoke(f, obj, *args, **kwargs)
        return update_wrapper(new_func, f)
    return decorator


def _make_command(f, name, attrs, cls):
    if isinstance(f, Command):
        raise TypeError('Attempted to convert a callback into a '
                        'command twice.')
    try:
        params = f.__click_params__
        params.reverse()
        del f.__click_params__
    except AttributeError:
        params = []
    help = attrs.get('help')
    if help is None:
        help = inspect.getdoc(f)
        if isinstance(help, bytes):
            help = help.decode('utf-8')
    else:
        help = inspect.cleandoc(help)
    attrs['help'] = help
    _check_for_unicode_literals()
    return cls(name=name or f.__name__.lower().replace('_', '-'),
               callback=f, params=params, **attrs)


def command(name=None, cls=None, **attrs):
    r"""建立一个新的 :class:`Command` 类并且把装饰的函数作为回调函数使用。
    本装饰器函数也会自动地把所有装饰的 :func:`option` 和 :func:`argument`
    附着成参数形式给命令。

    命令名默认为函数名。如果你要改变名字，你可以把名字作为第一参数值。

    所有关键字参数都是指命令类中的参数。

    一旦装饰的函数变成一个 :class:`Command` 类的实例，
    就可以被触发成一个命令行工具，或者成为一个命令群组
     :class:`Group` 类中的一个子命令。

    :param name: 命令的名字。默认是把函数名中的下划线换成减号。
    :param cls: 要实例化的命令类。默认值是 :class:`Command` 类。
    """
    if cls is None:
        cls = Command
    def decorator(f):
        cmd = _make_command(f, name, attrs, cls)
        cmd.__doc__ = f.__doc__
        return cmd
    return decorator


def group(name=None, **attrs):
    """建立一个新的 :class:`Group` 类所含的一个函数作为回调函数。
    本函数工作起来与 :func:`command` 类似，就是把 `cls` 参数形式
    设置成 :class:`Group` 类了。
    """
    attrs.setdefault('cls', Group)
    return command(name, **attrs)


def _param_memo(f, param):
    if isinstance(f, Command):
        f.params.append(param)
    else:
        if not hasattr(f, '__click_params__'):
            f.__click_params__ = []
        f.__click_params__.append(param)


def argument(*param_decls, **attrs):
    """把一个参数提供给命令。
    所有位置参数都代入成参数声明形式，提供给 :class:`Argument` 类；
    所有关键字参数都直接不变 (除了 ``cls``) 。
    本函数等价于手动建立了一个 :class:`Argument` 类的实例，
    并且把实例提供给 :attr:`Command.params` 属性列表。

    :param cls: 要实例化的参数类。默认值是 :class:`Argument` 类。
    """
    def decorator(f):
        ArgumentClass = attrs.pop('cls', Argument)
        _param_memo(f, ArgumentClass(param_decls, **attrs))
        return f
    return decorator


def option(*param_decls, **attrs):
    """把一个可选项提供给命令。
    所有位置参数都代入成参数声明形式，提供给 :class:`Option` 类；
    所有关键字参数都直接不变 (除了 ``cls``) 。
    本函数等价于手动建立了一个 :class:`Option` 类的实例，
    并且把实例提供给 :attr:`Command.params` 属性列表。

    :param cls: 要实例化的选项类。默认值是 :class:`Option` 类。
    """
    def decorator(f):
        # Issue 926, copy attrs, so pre-defined options can re-use the same cls=
        option_attrs = attrs.copy()

        if 'help' in option_attrs:
            option_attrs['help'] = inspect.cleandoc(option_attrs['help'])
        OptionClass = option_attrs.pop('cls', Option)
        _param_memo(f, OptionClass(param_decls, **option_attrs))
        return f
    return decorator


def confirmation_option(*param_decls, **attrs):
    """确认提示的快捷功能。
    确认提示可以通过使用 ``--yes`` 作为参数形式被忽略掉。

    等价于使用 :func:`option` 函数装饰一个函数，
    使用如下参数形式::

        def callback(ctx, param, value):
            if not value:
                ctx.abort()

        @click.command()
        @click.option('--yes', is_flag=True, callback=callback,
                      expose_value=False, prompt='Do you want to continue?')
        def dropdb():
            pass
    """
    def decorator(f):
        def callback(ctx, param, value):
            if not value:
                ctx.abort()
        attrs.setdefault('is_flag', True)
        attrs.setdefault('callback', callback)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('prompt', 'Do you want to continue?')
        attrs.setdefault('help', 'Confirm the action without prompting.')
        return option(*(param_decls or ('--yes',)), **attrs)(f)
    return decorator


def password_option(*param_decls, **attrs):
    """密码提示的快捷功能。

    等价于用 :func:`option` 函数装饰了一个函数，
    使用如下参数形式::

        @click.command()
        @click.option('--password', prompt=True, confirmation_prompt=True,
                      hide_input=True)
        def changeadmin(password):
            pass
    """
    def decorator(f):
        attrs.setdefault('prompt', True)
        attrs.setdefault('confirmation_prompt', True)
        attrs.setdefault('hide_input', True)
        return option(*(param_decls or ('--password',)), **attrs)(f)
    return decorator


def version_option(version=None, *param_decls, **attrs):
    """增加一项 ``--version`` 选项。
    该选项立即结束于程序输出版本号。本函数实现成一种期望可选项，
    期望可选项输出版本信息后在回调中退出程序。

    :param version: 要显示的版本号。如果没有提供，Click 会通过
                    setuptools 库来自动发现一个。
    :param prog_name: 程序的名字 (默认是自动检测)
    :param message: 显示自定义消息，反而不显示默认的
                    (``'%(prog)s, version %(version)s'``)
    :param others: 其它的直接提供给 :func:`option` 函数。
    """
    if version is None:
        if hasattr(sys, '_getframe'):
            module = sys._getframe(1).f_globals.get('__name__')
        else:
            module = ''

    def decorator(f):
        prog_name = attrs.pop('prog_name', None)
        message = attrs.pop('message', '%(prog)s, version %(version)s')

        def callback(ctx, param, value):
            if not value or ctx.resilient_parsing:
                return
            prog = prog_name
            if prog is None:
                prog = ctx.find_root().info_name
            ver = version
            if ver is None:
                try:
                    import pkg_resources
                except ImportError:
                    pass
                else:
                    for dist in pkg_resources.working_set:
                        scripts = dist.get_entry_map().get('console_scripts') or {}
                        for script_name, entry_point in iteritems(scripts):
                            if entry_point.module_name == module:
                                ver = dist.version
                                break
                if ver is None:
                    raise RuntimeError('Could not determine version')
            echo(message % {
                'prog': prog,
                'version': ver,
            }, color=ctx.color)
            ctx.exit()

        attrs.setdefault('is_flag', True)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('is_eager', True)
        attrs.setdefault('help', 'Show the version and exit.')
        attrs['callback'] = callback
        return option(*(param_decls or ('--version',)), **attrs)(f)
    return decorator


def help_option(*param_decls, **attrs):
    """增加一个 ``--help`` 选项。
    该选项立即结束于程序输出帮助页面内容。
    常常不需要增加，因为默认会增加给所有的命令，
    除非你要实现压制作用。

    像 :func:`version_option` 函数一样，
    本函数实现成一个期望可选项，在回调中输出后退出程序。

    所有参数都直接提供给 :func:`option` 函数。
    """
    def decorator(f):
        def callback(ctx, param, value):
            if value and not ctx.resilient_parsing:
                echo(ctx.get_help(), color=ctx.color)
                ctx.exit()
        attrs.setdefault('is_flag', True)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('help', 'Show this message and exit.')
        attrs.setdefault('is_eager', True)
        attrs['callback'] = callback
        return option(*(param_decls or ('--help',)), **attrs)(f)
    return decorator


# Circular dependencies between core and decorators
from .core import Command, Group, Argument, Option
