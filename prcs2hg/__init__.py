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
import prcs2hg.sexpdata as sexpdata
from prcs import PrcsProject

class Converter(object):

    def __init__(self, name, verbose = False):
        """Construct a Converter object."""
        self.name = name
        self.verbose = verbose

        self.project = PrcsProject(name)
        revisions = self.project.revisions()

    def convert(self):
        """Convert all revisions."""
        list = sorted(revisions, key = lambda id: revisions[id]["date"])

def convert(name, verbose = False):
    """convert revisions."""
    project = PrcsProject(name)
    revisions = project.revisions()
    list = sorted(revisions, key = lambda id: revisions[id]["date"])

    if verbose:
        sys.stderr.write("Extracting project descriptors...\n");
    for i in list:
        if not revisions[i].get("deleted", False):
            prj_name = project.name + ".prj"
            project.checkout([prj_name], revision = i)
            revisions[i]["descriptor"] = _parsedescriptor(prj_name)
        else:
            sys.stderr.write("warning: revision " + i + " was deleted\n")

    roots = filter(_isroot, revisions.itervalues())
    if len(roots) != 1:
        sys.stderr.write("Not a single root\n")
        return False
    # TODO
    print "root revision is", roots[0]["id"]

def _parsedescriptor(name):
    with open(name, "r") as f:
        string = f.read()

    d = {}
    # Encloses the project descriptor in a single list.
    for i in sexpdata.loads("(\n" + string + "\n)\n"):
        if isinstance(i, list) and isinstance(i[0], sexpdata.Symbol):
            d[i[0].value().lower()] = i[1:]
    return d

def _isroot(revision):
    """return a true value if a revision is root."""
    if 'descriptor' in revision:
        p = revision['descriptor']['parent-version']
        return isinstance(p[0], sexpdata.Symbol) and p[0].value() == "-*-"
    else:
        return False

