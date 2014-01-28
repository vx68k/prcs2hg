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

"""provide command line interface to PRCS
"""

import sys, re, os, subprocess, time, email.utils
from subprocess import Popen, PIPE
from time import mktime
from email.utils import parsedate
import prcs.sexpdata as sexpdata

class PrcsProject(object):

    def __init__(self, name):
        """construct a Project object."""
        self.name = name
        self.info_re = re.compile(
                "^([^ ]+) ([^ ]+) (.+) by ([^ ]+)( \*DELETED\*|)")

    def revisions(self):
        out, err = self._run_prcs(["info", "-f", self.name]);

        revisions = {}
        if (not err):
            # We use iteration over lines so that we can detect parse errors.
            for line in out.splitlines():
                m = self.info_re.search(line)
                if (m):
                    revisions[m.group(2)] = {
                        "project": m.group(1),
                        "id": m.group(2),
                        # The prcs info command returns the local time.
                        "date": mktime(parsedate(m.group(3))),
                        "author": m.group(4),
                        "deleted": bool(m.group(5))
                    }
        else:
            sys.stderr.write(err)
        return revisions

    def descriptor(self, id = None):
        return PrcsDescriptor(self, id)

    def checkout(self, revision = None, *files):
        args = ["checkout", "-fqu"]
        if not files:
            args.append("-P")
        if revision is not None:
            args.extend(["-r", revision])
        args.append(self.name)
        args.extend(files)
        out, err = self._run_prcs(args)
        if err:
            sys.stderr.write(err)

    def _run_prcs(self, args, input = None):
        """run a PRCS subprocess."""
        prcs = Popen(["prcs"] + args, stdin = PIPE, stdout = PIPE,
                stderr = PIPE)
        return prcs.communicate(input)

class PrcsDescriptor(object):

    def __init__(self, project, id = None):
        prj_name = project.name + ".prj"
        project.checkout(id, prj_name)
        self.properties = _readdescriptor(prj_name)
        os.unlink(prj_name)

    def parent(self):
        pv = self.properties["Parent-Version"]
        if len(pv) >= 3:
            if pv[1].value() != "-*-" and pv[2].value() != "-*-":
                return "{0}.{1}".format(pv[1].value(), pv[2].value())
            else:
                return None
        else:
            sys.stderr.write("Failed to get the parent for {0}\n".format(id))
            return None

    def files(self):
        """Return the file information as a dictionary."""
        files = {}
        for i in self.properties["Files"]:
            name = i[0].value()
            symlink = False
            for j in i[2:]:
                if j.value() == ":symlink":
                    symlink = True
            if symlink:
                files[name] = {
                    "symlink": i[1][0].value(),
                }
            else:
                files[name] = {
                    "id": i[1][0].value(),
                    "revision": i[1][1].value(),
                    "mode": int(i[1][2].value(), 8),
                }
        return files

def _readdescriptor(name):
    with open(name, "r") as f:
        string = f.read()

    descriptor = {}
    # Encloses the project descriptor in a single list.
    for i in sexpdata.loads("(\n" + string + "\n)"):
        if isinstance(i, list) and isinstance(i[0], sexpdata.Symbol):
            descriptor[i[0].value()] = i[1:]
    return descriptor
