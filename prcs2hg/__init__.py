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
from string import join
from prcs import PrcsProject

class Converter(object):

    def __init__(self, name, verbose = False):
        """Construct a Converter object."""
        self.name = name
        self.verbose = verbose
        self.revisionmap = {}
        self.symlink_warned = {}

        self.prcs = PrcsProject(self.name)
        self.revisions = self.prcs.revisions()

        self.hgclient = hglib.open(".")

    def convert(self):
        """Convert all revisions in a project."""
        list = sorted(self.revisions, key = lambda id:
            self.revisions[id]["date"])

        for i in list:
            self.convertrevision(i)

    def convertrevision(self, version):
        if self.revisions[version].get("deleted"):
            sys.stderr.write("Ignored deleted version {0}\n".format(version))
            return

        if self.verbose:
            sys.stderr.write("Converting version {0}\n".format(version))

        descriptor = self.prcs.descriptor(version)
        parent = descriptor.parentversion()
        if parent[0] is None:
            # It is a root revision.
            self.hgclient.update("null")
            parent_filemap = {}
        else:
            parent = join(parent, ".")
            if self.revisionmap.get(parent) is None:
                self.convertrevision(parent)
                # TODO: If the parent is not converted, do it here.
                sys.exit("Parent revision {0} not converted"
                    .format(parent))

            mergeparents = descriptor.mergeparents()
            if mergeparents:
                sys.exit("Merge found")

            # Makes the working directory clean.
            self.hgclient.update(self.revisionmap[parent])
            for i in self.hgclient.status():
                if i[0] != "C":
                    os.unlink(i[1])
            self.hgclient.revert([], "null", all = True)

            parent_filemap = self.revisions[parent].get("filemap")
            if parent_filemap is None:
                sys.exit("No parent filemap")
                parent_descriptor = self.prcs.descriptor(parent)
                parent_filemap = _makefilemap(parent_descriptor.files())

        self.prcs.checkout(version)
        files = descriptor.files()
        filemap = _makefilemap(files)
        self.revisions[version]["filemap"] = filemap

        # Checks for files.
        addlist = []
        for name, file in files.iteritems():
            # We cannot include symbolic links in Mercurial repositories.
            if "symlink" in file:
                if not self.symlink_warned.get(name, False):
                    sys.stderr.write("{0}: warning: symbolic link\n"
                        .format(name))
                    self.symlink_warned[name] = True
            else:
                file_id = file.get("id")
                if file_id is None:
                    sys.exit("{0}: Missing file identity".format(name))

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
        revision = self.hgclient.commit(message = message,
            date = self.revisions[version]["date"],
            user = self.revisions[version]["author"])

        self.revisionmap[version] = revision[1]
        # Keeps the revision identifier as a local tag for convenience.
        self.hgclient.tag([version], local = True, force = True)

def _makefilemap(files):
    filemap = {}
    for name, file in files.iteritems():
        id = file.get("id")
        if id is not None:
            if filemap.get(id) is not None:
                sys.stderr.write(
                    "warning: Duplicate file identifier in a revision\n")
            filemap[id] = name
    return filemap

def convert(name, verbose = False):
    """convert revisions."""
    converter = Converter(name, verbose = verbose)
    converter.convert()
