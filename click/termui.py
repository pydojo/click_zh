import os
import sys
import struct
import inspect
import itertools

from ._compat import raw_input, text_type, string_types, \
     isatty, strip_ansi, get_winterm_size, DEFAULT_COLUMNS, WIN
from .utils import echo
from .exceptions import Abort, UsageError
from .types import convert_type, Choice, Path
from .globals import resolve_color_default


# The prompt functions to use.  The doc tools currently override these
# functions to customize how they work.
visible_prompt_func = raw_input

_ansi_colors = {
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'white': 37,
    'reset': 39,
    'bright_black': 90,
    'bright_red': 91,
    'bright_green': 92,
    'bright_yellow': 93,
    'bright_blue': 94,
    'bright_magenta': 95,
    'bright_cyan': 96,
    'bright_white': 97,
}
_ansi_reset_all = '\033[0m'


def hidden_prompt_func(prompt):
    import getpass
    return getpass.getpass(prompt)


def _build_prompt(text, suffix, show_default=False, default=None, show_choices=True, type=None):
    prompt = text
    if type is not None and show_choices and isinstance(type, Choice):
        prompt += ' (' + ", ".join(map(str, type.choices)) + ')'
    if default is not None and show_default:
        prompt = '%s [%s]' % (prompt, default)
    return prompt + suffix


def prompt(text, default=None, hide_input=False, confirmation_prompt=False,
           type=None, value_proc=None, prompt_suffix=': ', show_default=True,
           err=False, show_choices=True):
    """提示一名用户输入。
    这是一种便利函数，它可以用来给一名用户提供输入提示功能。

    如果用户用一个打断信号终止输入提示的话，本函数会捕获打断信号后
    抛出一个 :exc:`Abort` 例外错误。

    .. versionadded:: 7.0
       其中增加了 show_choices 参数形式。

    .. versionadded:: 6.0
       为 Windows 系统上的 cmd.exe 增加了 unicode 数据支持。

    .. versionadded:: 4.0
       其中增加了 `err` 参数形式。

    :param text: 为提示而显示的文字内容。
    :param default: 如果没有输出发生时所使用的默认值。
                    如果不提供这个参数值的话，会一直
                    出现提示，直到终止提示。
    :param hide_input: 如果设置成 `True` 的话，输入的值会被隐藏显示。
    :param confirmation_prompt: 确认再输入一次提示值。
    :param type: 检查提示值的数据类型。
    :param value_proc: 如果提供这个参数的话，参数值是一个函数名，会用来
                       代替类型转换函数对提示值进行类型转换。
    :param prompt_suffix: 提示内容的最后一个符号。
    :param show_default: 在提示文字中是否显示默认值。
    :param err: 如果设置成 `True` 文件默认是 ``stderr`` 标准错误，
                而不再是 ``stdout`` 了，与 echo 效果一样。
    :param show_choices: 如果 type 参数值是 Choice 类的话，是否显示候选清单。
                         例如如果 type 参数值是一个 Choice 类的 day 或 week
                         选择的话，show_choices 参数设置成 `True` 后提示文字
                         中的 "Group by" 会变成 "Group by (day, week): "
    """
    result = None

    def prompt_func(text):
        f = hide_input and hidden_prompt_func or visible_prompt_func
        try:
            # Write the prompt separately so that we get nice
            # coloring through colorama on Windows
            echo(text, nl=False, err=err)
            return f('')
        except (KeyboardInterrupt, EOFError):
            # getpass doesn't print a newline if the user aborts input with ^C.
            # Allegedly this behavior is inherited from getpass(3).
            # A doc bug has been filed at https://bugs.python.org/issue24711
            if hide_input:
                echo(None, err=err)
            raise Abort()

    if value_proc is None:
        value_proc = convert_type(type, default)

    prompt = _build_prompt(text, prompt_suffix, show_default, default, show_choices, type)

    while 1:
        while 1:
            value = prompt_func(prompt)
            if value:
                break
            elif default is not None:
                if isinstance(value_proc, Path):
                    # validate Path default value(exists, dir_okay etc.)
                    value = default
                    break
                return default
        try:
            result = value_proc(value)
        except UsageError as e:
            echo('Error: %s' % e.message, err=err)
            continue
        if not confirmation_prompt:
            return result
        while 1:
            value2 = prompt_func('Repeat for confirmation: ')
            if value2:
                break
        if value == value2:
            return result
        echo('Error: the two entered values do not match', err=err)


def confirm(text, default=False, abort=False, prompt_suffix=': ',
            show_default=True, err=False):
    """为确认提供提示输入 (属于 yes/no 问题类型)。

    如果用户通过打断信号终止输入，
    本函数会捕获打断信号后抛出一个 :exc:`Abort` 例外错误。

    .. versionadded:: 4.0
       其中增加了 `err` 参数形式。

    :param text: 提示文字。
    :param default: 提示的默认值。
    :param abort: 如果设置成 `True` 一个否定结果会终止提示，
                  是通过抛出 :exc:`Abort` 例外错误实现的。
    :param prompt_suffix: 提示文字的后缀内容。
    :param show_default: 是否在提示中显示默认值。
    :param err: 如果设置成 `True` 文件默认为 ``stderr`` 
                而不再是 ``stdout`` 了，与 echo 效果一样。
    """
    prompt = _build_prompt(text, prompt_suffix, show_default,
                           default and 'Y/n' or 'y/N')
    while 1:
        try:
            # Write the prompt separately so that we get nice
            # coloring through colorama on Windows
            echo(prompt, nl=False, err=err)
            value = visible_prompt_func('').lower().strip()
        except (KeyboardInterrupt, EOFError):
            raise Abort()
        if value in ('y', 'yes'):
            rv = True
        elif value in ('n', 'no'):
            rv = False
        elif value == '':
            rv = default
        else:
            echo('Error: invalid input', err=err)
            continue
        break
    if abort and not rv:
        raise Abort()
    return rv


def get_terminal_size():
    """返回当前终端的尺寸。
    返回值是元组形式 ``(width, height)`` 对应着列数与行数。
    """
    # If shutil has get_terminal_size() (Python 3.3 and later) use that
    if sys.version_info >= (3, 3):
        import shutil
        shutil_get_terminal_size = getattr(shutil, 'get_terminal_size', None)
        if shutil_get_terminal_size:
            sz = shutil_get_terminal_size()
            return sz.columns, sz.lines

    # We provide a sensible default for get_winterm_size() when being invoked
    # inside a subprocess. Without this, it would not provide a useful input.
    if get_winterm_size is not None:
        size = get_winterm_size()
        if size == (0, 0):
            return (79, 24)
        else:
            return size

    def ioctl_gwinsz(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack(
                'hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except Exception:
            return
        return cr

    cr = ioctl_gwinsz(0) or ioctl_gwinsz(1) or ioctl_gwinsz(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            try:
                cr = ioctl_gwinsz(fd)
            finally:
                os.close(fd)
        except Exception:
            pass
    if not cr or not cr[0] or not cr[1]:
        cr = (os.environ.get('LINES', 25),
              os.environ.get('COLUMNS', DEFAULT_COLUMNS))
    return int(cr[1]), int(cr[0])


def echo_via_pager(text_or_generator, color=None):
    """本函数得到一个文本内容后显示成一页一页的形式在标准输出上。

    .. versionchanged:: 3.0
       其中增加了 `color` 旗语。

    :param text_or_generator: 显示到单页上的文字，或用一个
                              生成器对象来产生单页所需的文字。
    :param color: 控制页面是否支持 ANSI 色彩机制。默认是自动检测。
    """
    color = resolve_color_default(color)

    if inspect.isgeneratorfunction(text_or_generator):
        i = text_or_generator()
    elif isinstance(text_or_generator, string_types):
        i = [text_or_generator]
    else:
        i = iter(text_or_generator)

    # convert every element of i to a text type if necessary
    text_generator = (el if isinstance(el, string_types) else text_type(el)
                      for el in i)

    from ._termui_impl import pager
    return pager(itertools.chain(text_generator, "\n"), color)


def progressbar(iterable=None, length=None, label=None, show_eta=True,
                show_percent=None, show_pos=False,
                item_show_func=None, fill_char='#', empty_char='-',
                bar_template='%(label)s  [%(bar)s]  %(info)s',
                info_sep='  ', width=36, file=None, color=None):
    """本函数建立了一个可迭代对象语境管理器。
    语境管理器可以用来迭代某些对象的同时显示一个进度条。
    本函数即可以迭代 `iterable` 参数值，也可以迭代 `length` 参数值
     (都是可以进行数算的对象)。当迭代发生时，本函数会输出一个渲染过的
    进度条到给出的 `file` 文件上(默认是标准输出) ，并且会去计算剩余
    时间等事情。默认情况下，如果文件不是一个终端的话，这个进度条不会被渲染。

    语境管理器建立了进度条。当进入语境管理器时，进度条就建立完成了。进度条
    上的每次迭代，让可迭代对象优先进入进度条并更新进度条。当退出语境管理器
    的时候，会输出一个新行字符，并且进度条也会在屏幕上结束进度。

    注意: 进度条目前所设计的使用情景是，总体进度至少要在许多秒以上。
    由于这个设计， ProgressBar 类对象不会显示执行太快的进度，并且
    不会显示步骤之间所耗时间小于 1 秒的进度。

    没有进度条输出一定会发生，或者进度条会无意中被销毁。

    示例用法::

        with progressbar(items) as bar:
            for item in bar:
                do_something_with(item)

    另一种没有可迭代对象的用法，一种可以手动更新进度条的方法，通过
     `update()` 方法实现，而不是直接在进度条上进行迭代。这个更新
    方法接收步骤数来增加进度条进展::

        with progressbar(length=chunks.total_bytes) as bar:
            for chunk in chunks:
                process_chunk(chunk)
                bar.update(chunks.bytes)

    其中 ``update()`` 方法也有一个可选参数值，描述在 ``current_item`` 
    新位置上。当与 ``item_show_func`` 一起使用时是有用的，因为要自定义
    每个手动步骤的输出::

        with click.progressbar(
            length=total_size,
            label='Unzipping archive',
            item_show_func=lambda a: a.filename
        ) as bar:
            for archive in zip_file:
                archive.extract()
                bar.update(archive.size, archive)

    .. versionadded:: 2.0

    .. versionadded:: 4.0
       其中增加了 `color` 参数形式。把一个 `update` 方法增加给了进度条对象。

    :param iterable: 一个可迭代对象。如果不提供这个参数值，就要用长度参数。
    :param length: 迭代对象中每项元素的数量。默认情况进度条会得到迭代器对象
                   的长度值，也许会失效。如果提供这个参数值的话，会用来覆写
                   长度值。如果没有提供的话，进度条会对可迭代对象的长度进行
                   迭代。
    :param label: 显示进度条的标签信息。
    :param show_eta: 开启和禁用显示估算时间。如果长度值无法确定会自动禁用。
    :param show_percent: 开启或禁用显示百分比信息。如果迭代对象长度值大于0
                         的话，默认值是 `True` ，否则是 `False` 
    :param show_pos: 开启或禁用绝对位置显示。默认值是 `False`
    :param item_show_func: 一个使用当前迭代项的函数，可以返回成一个字符串显示
                           在终端里，最后显示进度条。注意当前项可以是 `None`
    :param fill_char: 显示在进度条里的字符。
    :param empty_char: 进度条中物填充部分的字符。
    :param bar_template: 进度条使用的格式化字符串模版。模版中的参数有：
                         ``label`` 进度条标签，``bar`` 进度条样式，
                         ``info`` 进度条信息部分。
    :param info_sep: 多个信息项之间的分隔字符
                     (例如剩余时间、百分比、绝对位置之间的间隔符号)
    :param width: 进度条信息部分的宽度，单位是字符，值为 0 意思是终端的宽度。
    :param file: 要写入的文件。如果不是一个终端的话，只会输出标签。
    :param color: 如果终端支持 ANSI 色彩就可控，否则不行。
                  默认是自动检测的。如果 ANSI 色彩代号包含在进度条输出中，
                  就需要这个参数值，默认不提供这个环境。
    """
    from ._termui_impl import ProgressBar
    color = resolve_color_default(color)
    return ProgressBar(iterable=iterable, length=length, show_eta=show_eta,
                       show_percent=show_percent, show_pos=show_pos,
                       item_show_func=item_show_func, fill_char=fill_char,
                       empty_char=empty_char, bar_template=bar_template,
                       info_sep=info_sep, file=file, label=label,
                       width=width, color=color)


def clear():
    """对终端执行清屏效果。
    本函数会清楚终端的整个可视区域，然后把光标移动到左上角。
    如果没有连接一个终端的话，本函数不做任何事情。

    .. versionadded:: 2.0
    """
    if not isatty(sys.stdout):
        return
    # If we're on Windows and we don't have colorama available, then we
    # clear the screen by shelling out.  Otherwise we can use an escape
    # sequence.
    if WIN:
        os.system('cls')
    else:
        sys.stdout.write('\033[2J\033[1;1H')


def style(text, fg=None, bg=None, bold=None, dim=None, underline=None,
          blink=None, reverse=None, reset=True):
    """用 ANSI 色彩来给文本着色后返回新颜色的字符串。
    默认是终端自身所含的颜色风格，在字符串最后会有一个重置代码。
    这样可以防止代入 ``reset=False`` 这个参数值。

    示例::

        click.echo(click.style('Hello World!', fg='green'))
        click.echo(click.style('ATTENTION!', blink=True))
        click.echo(click.style('Some things', reverse=True, fg='cyan'))

    所支持的颜色名字:

    * ``black`` (might be a gray)
    * ``red``
    * ``green``
    * ``yellow`` (might be an orange)
    * ``blue``
    * ``magenta``
    * ``cyan``
    * ``white`` (might be light gray)
    * ``bright_black``
    * ``bright_red``
    * ``bright_green``
    * ``bright_yellow``
    * ``bright_blue``
    * ``bright_magenta``
    * ``bright_cyan``
    * ``bright_white``
    * ``reset`` (reset the color code only)

    .. versionadded:: 2.0

    .. versionadded:: 7.0
       其中增加了亮色系列。

    :param text: 用 ansi 代号来着色的文字。
    :param fg: 如果提供改变文字的颜色，即前景色。
    :param bg: 如果提供改变终端底色，即背景色。
    :param bold: 是否开启粗体模式。
    :param dim: 是否开启深浅模式。这个效果并不好。
    :param underline: 是否开启下划线。
    :param blink: 是否开启闪烁效果。
    :param reverse: 是否开启反转渲染。
                    (前景色与背景色互换)
    :param reset: 默认重置所有风格效果，这样不会破坏终端设置。
                  这也可以被禁用来改变终端风格。
    """
    bits = []
    if fg:
        try:
            bits.append('\033[%dm' % (_ansi_colors[fg]))
        except KeyError:
            raise TypeError('Unknown color %r' % fg)
    if bg:
        try:
            bits.append('\033[%dm' % (_ansi_colors[bg] + 10))
        except KeyError:
            raise TypeError('Unknown color %r' % bg)
    if bold is not None:
        bits.append('\033[%dm' % (1 if bold else 22))
    if dim is not None:
        bits.append('\033[%dm' % (2 if dim else 22))
    if underline is not None:
        bits.append('\033[%dm' % (4 if underline else 24))
    if blink is not None:
        bits.append('\033[%dm' % (5 if blink else 25))
    if reverse is not None:
        bits.append('\033[%dm' % (7 if reverse else 27))
    bits.append(text)
    if reset:
        bits.append(_ansi_reset_all)
    return ''.join(bits)


def unstyle(text):
    """移除文字上的 ANSI 风格信息。
    通常不需要使用这个函数，因为 Click 的 echo 函数会自动
    根据需要移除颜色风格。

    .. versionadded:: 2.0

    :param text: 移除颜色风格的文字。
    """
    return strip_ansi(text)


def secho(message=None, file=None, nl=True, err=False, color=None, **styles):
    """本函数组合了 :func:`echo` 函数和 :func:`style` 函数调用。
    所以等价于如下两次调用效果::

        click.secho('Hello World!', fg='green')
        click.echo(click.style('Hello World!', fg='green'))

    所有关键字参数都是来自被组合的两个函数。

    .. versionadded:: 2.0
    """
    if message is not None:
        message = style(message, **styles)
    return echo(message, file=file, nl=nl, err=err, color=color)


def edit(text=None, editor=None, env=None, require_save=True,
         extension='.txt', filename=None):
    r"""在定义完的文本编辑器中来输入文字。
    如果给出一个文本编辑器的话，
    (应该使用完整路径指向可执行文本编辑器程序，
    但常规操作系统会搜索默认使用的文本编辑器) 
    会覆写自动检测到的文本编辑器。另外，有些
    环境变量是可以使用的。如果编辑器没有执行
    保存操作就关闭的话，返回的内容是 `None` 
    值。在这种情况下，一定要执行保存操作，并且
    会忽略 `require_save` 和 `extension` 
    参数的设置。

    如果文本编辑器不能打开，会抛出一个 :exc:`UsageError` 例外错误。

    注意 Windows 系统: 为了简化跨平台使用，新行字符都自动地从  POSIX 
    系统转换成 Windows 系统用的字符，并且反之亦然。因此这里依然会有
     ``\n`` 作为新行字符作标记用。

    :param text: 提前写入文本编辑器中的文字。
    :param editor: 选择文本编辑器程序。默认自动检测可用的默认文本编辑器。
    :param env: 直接提供给文本编辑器的环境变量。
    :param require_save: 如果设置成 `True` 的话，在文本编辑器中不执行
                         保存操作也会返回 `None` 值。
    :param extension: 告诉文本编辑器文件的扩展名是什么。
                      默认值是 `.txt` ，但改变这个可以改变句法高亮的效果。
    :param filename: 如果提供文件名的话，编辑器打开这个文件。
                     编辑器不再使用临时文件作为间接存储目标了。
    """
    from ._termui_impl import Editor
    editor = Editor(editor=editor, env=env, require_save=require_save,
                    extension=extension)
    if filename is None:
        return editor.edit(text)
    editor.edit_file(filename)


def launch(url, wait=False, locate=False):
    """本函数启动给出的 URL (或文件名) 默认应用程序。
    如果这是一个可执行程序的话，可能在新会话中打开程序。
    返回值是启动的应用程序的退出代号。常常指 ``0`` 说的。

    示例::

        click.launch('https://click.palletsprojects.com/')
        click.launch('/my/downloaded/file', locate=True)

    .. versionadded:: 2.0

    :param url: 要加载的一个 URL 或文件名。
    :param wait: 等待程序结束。
    :param locate: 如果设置成 `True` 的话，打开的不是与 URL 相关的应用程序，
                   而是打开一个文件管理器指向文件所在位置。如果 URL 没有指向
                   文件系统的话，也许会有奇怪的效果。
    """
    from ._termui_impl import open_url
    return open_url(url, wait=wait, locate=locate)


# If this is provided, getchar() calls into this instead.  This is used
# for unittesting purposes.
_getchar = None


def getchar(echo=False):
    """获得从终端输入的单个字符后返回该字符。
    本函数一直会返回一个 unicode 字符，并且
    在某些语言环境下返回的是多个字符。中文里的
    一个字就是一种多字符组成形式。对于多字符
    组成字会结束在终端缓存中，而标准输入实际上
    不是一个终端。

    注意本函数会一直从终端读取，即使使用管道技术
    连接到标准输入也是如此读取方式。

    注意 Windows 系统: 在很少的情况下，当输入非ASCII 字符时，
    本函数会等待下一个字符的输入，然后一次性返回输入结果。
    这是因为某些 Unicode 字符看起来像特殊的键盘输入方法。

    .. versionadded:: 2.0

    :param echo: 如果设置成 `True` 的话，字符读取后也会显示在终端里。
                 默认是不做这种输出到终端的设置。
    """
    f = _getchar
    if f is None:
        from ._termui_impl import getchar as f
    return f(echo)


def raw_terminal():
    from ._termui_impl import raw_terminal as f
    return f()


def pause(info='Press any key to continue ...', err=False):
    """本函数会暂停执行，并等待用户按下一个按键。
    这类似 Windows 系统的批处理 "pause" 命令。
    如果程序没有通过一个终端来运行的话，本函数什么也不会做。

    .. versionadded:: 2.0

    .. versionadded:: 4.0
       其中增加了 `err` 参数。

    :param info: 显示暂停的提示消息。
    :param err: 如果设置消息到 ``stderr`` 的话，
                即没输出到 ``stdout`` ，那么与 echo 效果一样。
    """
    if not isatty(sys.stdin) or not isatty(sys.stdout):
        return
    try:
        if info:
            echo(info, nl=False, err=err)
        try:
            getchar()
        except (KeyboardInterrupt, EOFError):
            pass
    finally:
        if info:
            echo(err=err)
