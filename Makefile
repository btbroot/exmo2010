#!/usr/bin/make -f
#
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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
OBJECT := HEAD
NAME := exmo2010
PREFIX := $(NAME)/
RELEASE := $(shell git describe --tags $(OBJECT))
RELEASE_ALL := $(shell git describe --long --all $(OBJECT))
RELEASE_FILE := exmo/templates/release
TARBALL := $(NAME)-$(RELEASE)
TARBALL_FILE := $(TARBALL).tar

ifeq ($(RELEASE),)
$(error OBJECT $(OBJECT) is unknown)
endif

dist: releaseinfo
	git archive --format tar --prefix $(PREFIX) $(OBJECT) -o $(TARBALL_FILE)
	tar -r $(RELEASE_FILE) --xform 's,^,$(PREFIX),S' -f $(TARBALL_FILE)
	gzip -f $(TARBALL_FILE)

dist-clean: releaseinfo-clean
	$(RM) $(TARBALL_FILE) $(TARBALL_FILE).gz

releaseinfo:
	echo $(RELEASE) $(RELEASE_ALL) > $(RELEASE_FILE)

releaseinfo-clean:
	$(RM) $(RELEASE_FILE)

clean: dist-clean

.PHONY: dist dist-clean releaseinfo releaseinfo-clean clean
