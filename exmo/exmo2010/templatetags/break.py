from django import template

register = template.Library()


@register.filter('break')
def break_(loop):
    '''Breaks from a loop.

    The 'break' filter is used within a loop and takes as input a loop variable,
    e.g. 'forloop' in case of a for loop. For example, to display the items
    from list ``items`` up to the first item that is equal to ``end``::

        <ul>
        {% for item in items %}
            {% if item == 'end' %}
                {{ forloop|break }}
            {% endif %}
            <li>{{ item }}</li>
        {% endfor %}
        </ul>

    Breaking from nested loops is also supported by passing the appropriate loop
    variable, e.g. ``forloop.parentloop|break``.
    '''
    raise StopLoopException(loop, False)


@register.filter('continue')
def continue_(loop):
    '''Continues a loop by jumping to its beginning.

    The 'continue' filter is used within a loop and takes as input a loop
    variable, e.g. 'forloop' in case of a for loop. It can also be used (and is
    mostly useful) for nested loops by passing the appropriate loop variable,
    e.g. ``forloop.parentloop|continue``. For example::

        {% for key,values in mapping.iteritems %}<br/>
            {% for value in values %}
                {{ key }}: {{ value }}<br/>
                {% if value|divisibleby:3  %}
                    {{ value }} is divisible by 3<br/>
                    {{ forloop.parentloop|continue }}
                {% endif %}
            {% endfor %}
            {{ key }}: No value divisible by 3<br/>
        {% endfor %}
    '''
    raise StopLoopException(loop, True)


# monkeypatch NodeList to handle break/continue
def render(self, context):
    return template.mark_safe(''.join(map(template.force_unicode,
                                          _render_nodelist_items(self,context))))
template.NodeList.render = render


# monkeypatch ForNode to handle break/continue
def render(self, context):
    try:
        values = self.sequence.resolve(context, True)
    except template.VariableDoesNotExist:
        values = []
    if values is None:
        values = []
    if not hasattr(values, '__len__'):
        values = list(values)
    len_values = len(values)
    if len_values < 1:
        return self.nodelist_empty.render(context)
    if self.is_reversed:
        values = reversed(values)
    unpack = len(self.loopvars) > 1
    # push a forloop value onto the context
    loop = BoundedLoop('forloop', context, self.nodelist_loop, len_values)
    for value in values:
        if unpack:
            # if there are multiple loop variables, unpack the value into them
            context.update(dict(zip(self.loopvars, value)))
        else:
            context[self.loopvars[0]] = value
        status = loop.next()
        if unpack and status is loop.PASS:
            # The loop variables were pushed on to the context so pop them
            # off again. This is necessary because the tag lets the length
            # of loopvars differ to the length of each set of items and we
            # don't want to leave any vars from the previous loop on the
            # context. If status is not PASS, all the additional dicts,
            # including the one with the loop variables, have already been
            # popped off in loop.next() so we don't have to pop it here
            context.pop()
        if status is loop.BREAK:
            break
    return loop.render(close=True)
template.defaulttags.ForNode.render = render


class StopLoopException(Exception):
    def __init__(self, loop, continue_, nodelist=None):
        if not isinstance(loop, Loop):
            raise TypeError('Loop instance expected, %s given' % loop.__class__.__name__)
        super(StopLoopException, self).__init__(loop, continue_, nodelist)
        self.loop, self.continue_, self.nodelist = self.args


class Loop(dict):
    '''Base class of loop variables passed in the context (e.g. 'forloop').

    A loop instance holds and keeps up to date the attributes exposed in the
    context. This class exposes ``counter``, ``counter0``, ``first`` and
    ``parentloop``; its :class:`BoundedLoop` subclass adds ``revcounter``,
    ``revcounter0`` and ``last``.

    Additionally, a loop instance renders the items of the nodelist that comprise
    the loop and accumulates the rendered strings on every call to :meth:`next`.
    :meth:`next` also handles continuing or breaking from the loop and informs
    the caller accordingly.
    '''

    PASS = object()
    BREAK = object()
    CONTINUE = object()

    def __init__(self, name, context, nodelist):
        self._name = name
        self._context = context
        self._nodelist = nodelist
        self._rendered_nodelist = template.NodeList()
        self['parentloop'] = context.get(name)
        context.push()
        context[name] = self

    def render(self, close=False):
        '''Renders the accumulated nodelist for this loop.

        As a convenience, if ``close`` is true, the loop is also :meth:`close`d.
        '''
        if close:
            self.close()
        return self._rendered_nodelist.render(self._context)
    render.alters_data = True

    def next(self):
        '''Updates this loop for one iteration step.

        :returns: The status of the loop after this step: :attr:`CONTINUE` if a
            ``continue`` targeting this loop was encountered, :attr:`BREAK` for
            a break, or :attr:`PASS` otherwise.
        :raises StopLoopException: If a ``break`` or ``continue`` for a loop
            other than this one (presumably an ancestor) was encountered.
        '''
        if self._nodelist is None:
            raise RuntimeError('This loop is inactive')
        try: # update the exposed attributes
            counter = self['counter']
            self.update(counter0=counter, counter=counter+1, first=False)
        except KeyError:
            # initialize the exposed attributes the first time this is called
            self.update(counter0=0, counter=1, first=True)
        try:
            _render_nodelist_items(self._nodelist, self._context, self._rendered_nodelist)
            status = self.PASS
        except StopLoopException, ex:
            # if this is not the target loop, keep bubbling up the exception
            if ex.loop is not self:
                raise
            # pop context until (but excluding) the dict that contains this loop
            self._pop_context_until_self(inclusive=False)
            status = ex.continue_ and self.CONTINUE or self.BREAK
        return status
    next.alters_data = True

    def close(self):
        '''Mark this loop as closed.

        After a loop is closed, subsequent calls to :meth:`next` are not allowed.
        This should be called when the loop is "done" to remove any loop-specific
        context entries.
        '''
        if self._nodelist:
            self._pop_context_until_self(inclusive=True)
            self._nodelist = None
    close.alters_data = True

    def _pop_context_until_self(self, inclusive):
        name = self._name
        dicts = self._context.dicts
        while len(dicts) > 1:
            if dicts[-1].get(name) is self:
                if inclusive:
                    del dicts[-1]
                break
            del dicts[-1]


class BoundedLoop(Loop):
    '''A :class:`Loop` of known length.

    ``BoundedLoop`` instances expose ``revcounter``, ``revcounter0`` and ``last``,
    in addition to the attributes exposed by ``Loop`` itself.
    '''

    def __init__(self, name, context, nodelist, length):
        if length < 1:
            raise ValueError('Length must be at least 1')
        self._length = length
        super(BoundedLoop, self).__init__(name, context, nodelist)

    def next(self):
        try: # update the exposed attributes
            revcounter0 = self['revcounter0']
            if revcounter0 <= 0:
                raise RuntimeError('Attempted to call `next()` more than %d times' % self._length)
            self.update(revcounter0=revcounter0-1, revcounter=revcounter0, last=revcounter0==1)
        except KeyError:
            # initialize the exposed attributes the first time this is called
            length = self._length
            self.update(revcounter0=length-1, revcounter=length, last=length==1)
        return super(BoundedLoop, self).next()
    next.alters_data = True


def _render_nodelist_items(nodelist, context, result=None):
    if result is None:
        result = []
    for node in nodelist:
        if not isinstance(node, template.Node):
            result.append(node)
        else:
            try:
                result.append(nodelist.render_node(node, context))
            except Exception, ex:
                # get the wrapped exception if settings.DEBUG is True
                if hasattr(ex, 'exc_info'):
                    ex = ex.exc_info[1]
                # let every exception other than StopLoopException propagate
                if not isinstance(ex, StopLoopException):
                    raise
                # reraise the StopLoopException with the updated nodelist
                if ex.nodelist:
                    result.extend(ex.nodelist)
                ex.nodelist = result
                raise ex
    return result
