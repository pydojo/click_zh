from contextlib import contextmanager
from .termui import get_terminal_size
from .parser import split_opt
from ._compat import term_len


# Can force a width.  This is used by the test system
FORCED_WIDTH = None


def measure_table(rows):
    widths = {}
    for row in rows:
        for idx, col in enumerate(row):
            widths[idx] = max(widths.get(idx, 0), term_len(col))
    return tuple(y for x, y in sorted(widths.items()))


def iter_rows(rows, col_count):
    for row in rows:
        row = tuple(row)
        yield row + ('',) * (col_count - len(row))


def wrap_text(text, width=78, initial_indent='', subsequent_indent='',
              preserve_paragraphs=False):
    """一个助手函数，智能地打包文字。
    默认情况，它假设了操作在文本的一个段落上，
    但如果提供了 `preserve_paragraphs` 参数的话，
    它会智能地处理多个段落 (分段用 2 个空行)。

    如果要处理许多段落的话，一个段落可以用一个含有 ``\\b`` 字符 (``\\x08``) 的空行
    来说明重新打包不应该发生在这块儿。

    :param text: 应该重新打包的文本。
    :param width: 文本的最大宽度。
    :param initial_indent: 最初的缩紧，应该放在第一行作为一个字符串。
    :param subsequent_indent: 缩紧字符串，应该放在每个连续行上。
    :param preserve_paragraphs: 如果设置了这个旗语，那么打包会智能地处理许多段落。
    """
    from ._textwrap import TextWrapper
    text = text.expandtabs()
    wrapper = TextWrapper(width, initial_indent=initial_indent,
                          subsequent_indent=subsequent_indent,
                          replace_whitespace=False)
    if not preserve_paragraphs:
        return wrapper.fill(text)

    p = []
    buf = []
    indent = None

    def _flush_par():
        if not buf:
            return
        if buf[0].strip() == '\b':
            p.append((indent or 0, True, '\n'.join(buf[1:])))
        else:
            p.append((indent or 0, False, ' '.join(buf)))
        del buf[:]

    for line in text.splitlines():
        if not line:
            _flush_par()
            indent = None
        else:
            if indent is None:
                orig_len = term_len(line)
                line = line.lstrip()
                indent = orig_len - term_len(line)
            buf.append(line)
    _flush_par()

    rv = []
    for indent, raw, text in p:
        with wrapper.extra_indent(' ' * indent):
            if raw:
                rv.append(wrapper.indent_only(text))
            else:
                rv.append(wrapper.fill(text))

    return '\n\n'.join(rv)


class HelpFormatter(object):
    """这个类帮助格式化帮助页面的文本内容。
    对于特殊的内部情况常常需要用到，但也可以被曝光，
    因为开发者们可以书写他们自己的输出风格。

    目前，这个类会一直写到内存中。

    :param indent_increment: 对每个层次来说都会额外增量计算。
    :param width: 文本的宽度。默认值是终端的宽度，限制在最大宽度为 78
    """

    def __init__(self, indent_increment=2, width=None, max_width=None):
        self.indent_increment = indent_increment
        if max_width is None:
            max_width = 80
        if width is None:
            width = FORCED_WIDTH
            if width is None:
                width = max(min(get_terminal_size()[0], max_width) - 2, 50)
        self.width = width
        self.current_indent = 0
        self.buffer = []

    def write(self, string):
        """Writes a unicode string into the internal buffer."""
        self.buffer.append(string)

    def indent(self):
        """Increases the indentation."""
        self.current_indent += self.indent_increment

    def dedent(self):
        """Decreases the indentation."""
        self.current_indent -= self.indent_increment

    def write_usage(self, prog, args='', prefix='Usage: '):
        """Writes a usage line into the buffer.

        :param prog: the program name.
        :param args: whitespace separated list of arguments.
        :param prefix: the prefix for the first line.
        """
        usage_prefix = '%*s%s ' % (self.current_indent, prefix, prog)
        text_width = self.width - self.current_indent

        if text_width >= (term_len(usage_prefix) + 20):
            # The arguments will fit to the right of the prefix.
            indent = ' ' * term_len(usage_prefix)
            self.write(wrap_text(args, text_width,
                                 initial_indent=usage_prefix,
                                 subsequent_indent=indent))
        else:
            # The prefix is too long, put the arguments on the next line.
            self.write(usage_prefix)
            self.write('\n')
            indent = ' ' * (max(self.current_indent, term_len(prefix)) + 4)
            self.write(wrap_text(args, text_width,
                                 initial_indent=indent,
                                 subsequent_indent=indent))

        self.write('\n')

    def write_heading(self, heading):
        """Writes a heading into the buffer."""
        self.write('%*s%s:\n' % (self.current_indent, '', heading))

    def write_paragraph(self):
        """Writes a paragraph into the buffer."""
        if self.buffer:
            self.write('\n')

    def write_text(self, text):
        """Writes re-indented text into the buffer.  This rewraps and
        preserves paragraphs.
        """
        text_width = max(self.width - self.current_indent, 11)
        indent = ' ' * self.current_indent
        self.write(wrap_text(text, text_width,
                             initial_indent=indent,
                             subsequent_indent=indent,
                             preserve_paragraphs=True))
        self.write('\n')

    def write_dl(self, rows, col_max=30, col_spacing=2):
        """Writes a definition list into the buffer.  This is how options
        and commands are usually formatted.

        :param rows: a list of two item tuples for the terms and values.
        :param col_max: the maximum width of the first column.
        :param col_spacing: the number of spaces between the first and
                            second column.
        """
        rows = list(rows)
        widths = measure_table(rows)
        if len(widths) != 2:
            raise TypeError('Expected two columns for definition list')

        first_col = min(widths[0], col_max) + col_spacing

        for first, second in iter_rows(rows, len(widths)):
            self.write('%*s%s' % (self.current_indent, '', first))
            if not second:
                self.write('\n')
                continue
            if term_len(first) <= first_col - col_spacing:
                self.write(' ' * (first_col - term_len(first)))
            else:
                self.write('\n')
                self.write(' ' * (first_col + self.current_indent))

            text_width = max(self.width - first_col - 2, 10)
            lines = iter(wrap_text(second, text_width).splitlines())
            if lines:
                self.write(next(lines) + '\n')
                for line in lines:
                    self.write('%*s%s\n' % (
                        first_col + self.current_indent, '', line))
            else:
                self.write('\n')

    @contextmanager
    def section(self, name):
        """Helpful context manager that writes a paragraph, a heading,
        and the indents.

        :param name: the section name that is written as heading.
        """
        self.write_paragraph()
        self.write_heading(name)
        self.indent()
        try:
            yield
        finally:
            self.dedent()

    @contextmanager
    def indentation(self):
        """A context manager that increases the indentation."""
        self.indent()
        try:
            yield
        finally:
            self.dedent()

    def getvalue(self):
        """Returns the buffer contents."""
        return ''.join(self.buffer)


def join_options(options):
    """Given a list of option strings this joins them in the most appropriate
    way and returns them in the form ``(formatted_string,
    any_prefix_is_slash)`` where the second item in the tuple is a flag that
    indicates if any of the option prefixes was a slash.
    """
    rv = []
    any_prefix_is_slash = False
    for opt in options:
        prefix = split_opt(opt)[0]
        if prefix == '/':
            any_prefix_is_slash = True
        rv.append((len(prefix), opt))

    rv.sort(key=lambda x: x[0])

    rv = ', '.join(x[1] for x in rv)
    return rv, any_prefix_is_slash
