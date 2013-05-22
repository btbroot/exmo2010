#! /usr/bin/make

# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
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

# Visualize the project activity

gource = gource --load-config gource.conf

show:
	$(gource)

commit.log:
	git log --pretty=format:"%at|%s" > $@

tag.log:
	for tag in $$(git tag); do git log -1 --pretty=format:"%at|$$tag%n" $$tag; done > $@

caption.log: commit.log tag.log
	cat $^ | sort > $@

movie.avi: caption.log
	$(gource) -o - | ffmpeg -y -f image2pipe -vcodec ppm -i - -qscale 2 $@

clean:
	-$(RM) commit.log tag.log caption.log movie.avi

.PHONY: show clean commit.log tag.log
