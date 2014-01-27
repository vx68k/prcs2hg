#
# Copyright (C) 2012-2014 Kaz Nishimura
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

"""convert PRCS revisions to Mercurial changesets
"""

import sys
import hglib
import prcs.sexpdata as sexpdata
from prcs import PrcsProject

class Converter(object):

    def __init__(self, name, verbose = False):
        """Construct a Converter object."""
        self.name = name
        self.verbose = verbose

        self.project = PrcsProject(self.name)
        self.revisions = self.project.revisions()

    def convert(self):
        """Convert all revisions in a project."""
        list = sorted(self.revisions, key = lambda id:
            self.revisions[id]["date"])

        for i in list:
            self.convertrevision(i)

#        # TODO: Refactor this section.
#        roots = filter(_isroot, revisions.itervalues())
#        if len(roots) != 1:
#            sys.stderr.write("Not a single root\n")
#            return False

    def convertrevision(self, id):
        if not self.revisions[id].get("deleted", False):
            if self.verbose:
                sys.stderr.write("Converting revision {0}\n".format(id))
            # TODO: Rewrite.
            descriptor = self.project.descriptor(id)
        else:
            sys.stderr.write("warning: revision {0} was deleted\n".format(id))

def convert(name, verbose = False):
    """convert revisions."""
    converter = Converter(name, verbose = verbose)
    converter.convert()

def _isroot(revision):
    """return a true value if a revision is root."""
    if 'descriptor' in revision:
        p = revision['descriptor']['Parent-Version']
        return isinstance(p[0], sexpdata.Symbol) and p[0].value() == "-*-"
    else:
        return False

