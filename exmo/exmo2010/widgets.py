# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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

from django.forms.widgets import Textarea
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.safestring import mark_safe

class TagAutocomplete(Textarea):
	input_type = 'text'
	
	def render(self, name, value, attrs=None):
		json_view = reverse('tagging_autocomplete-list')
		html = super(TagAutocomplete, self).render(name, value, attrs)
		js = u'<script type="text/javascript">jQuery().ready(function() { jQuery("#%s").autocomplete("%s", { multiple: true }); });</script>' % (attrs['id'], json_view)
		return mark_safe("\n".join([html, js]))
	
	class Media:
		js_base_url = getattr(settings, 'TAGGING_AUTOCOMPLETE_JS_BASE_URL','%s/jquery-autocomplete' % settings.MEDIA_URL)
		css = {
		    'all': ('%s/jquery.autocomplete.css' % js_base_url,)
		}
		js = (
		        '%sjs/jquery.js' % settings.ADMIN_MEDIA_PREFIX,
			'%s/jquery.autocomplete.js' % js_base_url,
			)
