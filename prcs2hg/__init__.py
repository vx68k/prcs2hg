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
import re
import os
import hglib
from prcs import PrcsProject

class Converter(object):

    def __init__(self, name, verbose = False):
        """Construct a Converter object."""
        self.name = name
        self.verbose = verbose
        self.revisionmap = {}

        self.project = PrcsProject(self.name)
        self.revisions = self.project.revisions()

        self.hgclient = hglib.open(".")

    def convert(self):
        """Convert all revisions in a project."""
        list = sorted(self.revisions, key = lambda id:
            self.revisions[id]["date"])

        for i in list:
            self.convertrevision(i)

    def convertrevision(self, id):
        revision = self.revisions[id]
        if revision.get("deleted", False):
            sys.stderr.write("Revision {0} was deleted\n".format(id))
            return

        if self.verbose:
            sys.stderr.write("Converting revision {0}\n".format(id))

        descriptor = self.project.descriptor(id)
        parent = descriptor.parent()
        if parent is None:
            # It is a root revision.
            self.hgclient.update("null")
            parent_filemap = {}
        else:
            if self.revisionmap.get(parent) is None:
                self.convertrevision(parent)
                # TODO: If the parent is not converted, do it here.
                sys.exit("Parent revision {0} not converted"
                    .format(parent))

            # Makes the working directory clean.
            self.hgclient.update(self.revisionmap[parent])
            for i in self.hgclient.status():
                if i[0] != "C":
                    os.unlink(i[1])
            self.hgclient.revert([], "null", all = True)

            parent_filemap = self.revisions[parent].get("filemap")
            if parent_filemap is None:
                sys.exit("No parent filemap")
                parent_descriptor = self.project.descriptor(parent)
                parent_filemap = _makefilemap(parent_descriptor.files())

        self.project.checkout(id)
        files = descriptor.files()
        filemap = _makefilemap(files)
        revision["filemap"] = filemap

        # Checks for added files.
        addlist = []
        for name, i in files.iteritems():
            file_id = i.get("id")
            if file_id is None:
                if i.get("symlink", False):
                    sys.stderr.write("{0}: warning: symbolic link\n"
                        .format(name))
                else:
                    sys.stderr.write("{0}: error: no identity\n"
                        .format(name))
                    sys.exit("stop")
            else:
                parent_name = parent_filemap.get(file_id)
                if parent_name is not None and parent_name != name:
                    if self.verbose:
                        sys.stderr.write("{0}: renamed from {1}\n"
                            .format(name, parent_name))
                    self.hgclient.copy(parent_name, name, after = True)
                else:
                    addlist.append(name)

        if addlist:
            self.hgclient.add(addlist)

        # Sets the branch for the following commit.
        major, minor = descriptor.version()
        branch = "default"
        if not re.match("[0-9]+$", major):
            branch = major
        self.hgclient.branch(branch, force = True)

        message = descriptor.message()
        if not message:
            message = "(empty commit message)"
        node = self.hgclient.commit(message = message,
            date = revision["date"], user = revision["author"])[1]

        self.revisionmap[id] = node
        # Keeps the revision identifier as a local tag for convenience.
        self.hgclient.tag([id], local = True, force = True)

def _makefilemap(files):
    filemap = {}
    for name, i in files.iteritems():
        id = i.get("id")
        if id is not None:
            if filemap.has_key(id):
                sys.stderr.write(
                    "warning: Duplicate file identifier in a revision\n")
            filemap[id] = name
    return filemap

def convert(name, verbose = False):
    """convert revisions."""
    converter = Converter(name, verbose = verbose)
    converter.convert()

