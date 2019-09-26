from threading import local


_local = local()


def get_current_context(silent=False):
    """返回当前 click 语境。
    它可以用来访问任何地方的当前语境对象。这是函数要比
    用 :func:`pass_context` 函数装饰器更隐含。本函数
    主要对助手函数有用，例如 :func:`echo` 函数可以改变
    自身行为，这样在当前语境中的一些变化就变得有趣了。

    要推送当前语境，使用 :meth:`Context.scope` 方法。

    .. versionadded:: 5.0

    :param silent: 如果设置成 `True` 的话，如果没有语境可用返回 `None` 值。
                   默认行为是要抛出一个 :exc:`RuntimeError` 例外错误。
    """
    try:
        return getattr(_local, 'stack')[-1]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError('There is no active click context.')


def push_context(ctx):
    """Pushes a new context to the current stack."""
    _local.__dict__.setdefault('stack', []).append(ctx)


def pop_context():
    """Removes the top level from the stack."""
    _local.stack.pop()


def resolve_color_default(color=None):
    """"Internal helper to get the default value of the color flag.  If a
    value is passed it's returned unchanged, otherwise it's looked up from
    the current context.
    """
    if color is not None:
        return color
    ctx = get_current_context(silent=True)
    if ctx is not None:
        return ctx.color
