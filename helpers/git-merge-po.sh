#!/bin/sh
#
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
#
#
# Custom Git merge driver - merges PO files using msgcat(1)
#
# Add this to your .git/config:
#
#   [merge "pofile"]
#     name = Gettext merge driver
#     driver = helpers/git-merge-po.sh %O %A %B
#
# When merging branches, conflicts in PO files will be marked with "#-#-#-#".
# You can use tools like lokalize(1) or gtranslator(1) to resolve them.


O=$1
A=$2
B=$3

# Extract the PO header from the current branch
#(top of file until first empty line)
header=$(mktemp)
sed -e '/^$/q' < $A > $header

# Merge files, then repair header
temp=$(mktemp)
msgcat -o $temp $A $B
msgcat --use-first -o $A $header $temp

# Clean up
rm -f $header $temp

# Check for conflicts
conflicts=$(grep -c "#-#" $A)
test $conflicts -gt 0 && exit 1
