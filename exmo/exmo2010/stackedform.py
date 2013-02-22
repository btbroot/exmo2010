# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012, 2013 Institute for Information Freedom Development
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
http://djangosnippets.org/snippets/1783/
"""

from django import forms
from django.template import loader, Context
from django.core.context_processors import media as media_processor

class StackedItem(object):
    """ 
    An item inside a ``FieldStack``
    Can be either an actual form field, or a group of fields
    """
    def __init__(self, form, stackitem):
        self.form = form
        self.stackitem = stackitem
        
    def is_group(self):
        if isinstance(self.stackitem, tuple):
            return True
        return False
    
    def __iter__(self):
        if not self.is_group():
            raise AttributeError('This stacked item is not a group and therefore not iterable')
        
        for stackitem in self.stackitem:
            yield StackedItem(self.form, stackitem)

    def __unicode__(self):
        """ Either render the html, or print some information about this group of fields """
        if self.is_group():
            return u'StackGroup %s' % self.stackitem
        tpl = self.form.get_field_template()
        context_dict = dict(
            form=self.form,
            field=self.form[self.stackitem],
        )
        context_dict.update(media_processor(None))
        return tpl.render(
            Context(
                context_dict
            )
        )
        
        return unicode(self.form[self.stackitem])

class FieldStack(object):
    """
    A stack of fields yielded by ``StackedForm``
    """
    def __init__(self, form, stack):
        self.form = form
        self.stack = stack
    
    def __iter__(self):
        for stackitem in self.stack.get('fields', ()):
            yield StackedItem(self.form, stackitem)

    def __len__(self):
        # ... or the for templatetag throws an error
        return len(self.stack.get('fields', ()))
            
    def __getattr__(self, name):
        return self.stack.get(name, None)

class StackedForm(object):
    """
    Mixin to provide support for stacked forms with or without grouped fields.
    One particular example of such a form (without groups though) is the Basecamp
    signup page https://signup.37signals.com/basecamp/Plus/signup/new 
        
    Example:
    
        # ---------------------------------------------------------- Django form
    
        from django import forms
        from toolbox.forms import StackedForm
        
        class MyForm(forms.Form, StackedForm):
            username = forms.CharField()
            pw1 = forms.CharField()
            pw2 = forms.CharField()
            email1 = forms.CharField()
            email2 = forms.CharField()
            first_name = forms.CharField()
            last_name = forms.CharField()
            website = forms.CharField()
            twitter = forms.CharField()
            facebook = forms.CharField()
            
            class Stack:
                stack = (
                    dict(
                        label = 'User Information',
                        fields = ('username',('first_name','last_name'))
                    ),
                    dict(
                        label = 'Security Information',
                        css_class = 'smaller-h1',
                        fields = (('email1','email2'),('pw1','pw2'))
                    ),
                    dict(
                        label = 'Elsewhere',
                        fields = ('website','twitter','facebook')
                    )
                )
        
        # ------------------------------------------------------------- Template
        
        <form action="." method="POST">
            {{ form.as_stack }}
            <input type="submit" value="Submit" />
        </form>
        
        # ---------------------------------------------------- stacked_form.html
        
        <ul>
        {% for stack in form.get_stacks %}
            {% if stack.label %}
                <li>
                    <h1{% if stack.css_class %} class="{{ stack.css_class }}"{% endif %}>{{ stack.label }}</h1>
                </li>
            {% endif %}
            <li>
                <ul>
                    {% for field in stack %}
                        <li>
                            {% if field.is_group %}
                                <ul>
                                    {% for f in field %}
                                        <li>{{ f }}</li>
                                    {% endfor %}
                                </ul>
                            {% else %}
                                {{ field }}
                            {% endif %}
                        </li>
                    {% endfor %}
                </ul>
            </li>
        {% endfor %}
        </ul>
        
        # ----------------------------------------------------- stack_field.html
        
        <p{% if field.errors %} class="error"{% endif %}>
            <label for="{{ field.auto_id }}">{{ field.label.title }}</label>
            {{ field }}
            <span class="tooltip-help">{{ field.help_text }}</span>
        </p>
        
        # --------------------------------------------------------------- Output
        <ul>
            <li>
                <h1>User Information</h1>
            </li>
            <li>
                <ul>
                    <li>
                        <p>
                            <label for="id_username">Username</label>
                            <input type="text" name="username" id="id_username" />
                            <span class="tooltip-help"></span>
                        </p>
                    </li>
                    <li>
                        <ul>
                            <li>
                                <p>
                                    <label for="id_first_name">First Name</label>
                                    <input type="text" name="first_name" id="id_first_name" />
                                    <span class="tooltip-help"></span>
                                </p>
                            </li>                                                    
                            <li>
                                <p>
                                    <label for="id_last_name">Last Name</label>
                                    <input type="text" name="last_name" id="id_last_name" />
                                    <span class="tooltip-help"></span>
                                </p>
                            </li>
                        </ul>
                    </li>
                </ul>
            </li>
            <li>
                <h1 class="smaller-h1">Security Information</h1>
            </li>
            <li>
                <ul>
                    <li>
                        <ul>
                            <li>
                                <p>
                                    <label for="id_email1">Email1</label>
                                    <input type="text" name="email1" id="id_email1" />
                                    <span class="tooltip-help"></span>
                                </p>
                            </li>
                            <li>
                                <p>
                                    <label for="id_email2">Email2</label>
                                    <input type="text" name="email2" id="id_email2" />
                                    <span class="tooltip-help"></span>
                                </p>
                            </li>                            
                        </ul>
                    </li>
                    <li>
                        <ul>
                            <li>
                                <p>
                                    <label for="id_pw1">Pw1</label>
                                    <input type="text" name="pw1" id="id_pw1" />
                                    <span class="tooltip-help"></span>
                                </p>
                            </li>
                            <li>
                                <p>
                                    <label for="id_pw2">Pw2</label>
                                    <input type="text" name="pw2" id="id_pw2" />
                                    <span class="tooltip-help"></span>
                                </p>    
                            </li>
                        </ul>
                    </li>            
                </ul>
            </li>
            <li>
                <h1>Elsewhere</h1>
            </li>
            <li>
                <ul>
                    <li>
                        <p>
                            <label for="id_website">Website</label>
                            <input type="text" name="website" id="id_website" />
                            <span class="tooltip-help"></span>
                        </p>
                    </li>
                    <li>                                            
                        <p>
                            <label for="id_twitter">Twitter</label>
                            <input type="text" name="twitter" id="id_twitter" />
                            <span class="tooltip-help"></span>
                        </p>                    
                    </li>            
                    <li>                    
                        <p>
                            <label for="id_facebook">Facebook</label>
                            <input type="text" name="facebook" id="id_facebook" />
                            <span class="tooltip-help"></span>
                        </p>            
                    </li>            
                </ul>
            </li>
        </ul>        
    """
    
    form_template = 'toolbox/forms/stacked_form.html'
    field_template = 'toolbox/forms/stack_field.html'
    
    def get_template(self):
        if getattr(self, '_form_tpl', None) is None:
            self._form_tpl = loader.get_template(self.form_template)
        return self._form_tpl
    
    def get_field_template(self):
        if getattr(self, '_field_tpl', None) is None:
            self._field_tpl = loader.get_template(self.field_template)
        return self._field_tpl
   
    def get_stacks(self):
        for stack in self.Stack.stack:
            yield FieldStack(self, stack)
    
    def __iter__(self):
        """ If this is the first inherit we can loop directly, else we'd have
        to use ``get_stacks`` """
        return self.get_stacks()
    
    def as_stack(self):
        """
        Renders a form like specified by the inner class ``Stack``
        """
        if not hasattr(self, 'Stack'):
            raise AttributeError('No inner class ``Stack`` defined')
        if not hasattr(self.Stack, 'stack'):
            raise AttributeError('No attribute ``stack`` on the inner class ``Stack`` defined')
        
        tpl = self.get_template()
        
        context_dict = dict(
            form=self,
        )

        context_dict.update(media_processor(None))
        
        return tpl.render(
            Context(context_dict)
        )
        
        