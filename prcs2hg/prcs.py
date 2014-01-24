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

import sys, re, subprocess, time, email.utils
from subprocess import Popen, PIPE
from time import mktime
from email.utils import parsedate
import sexpdata

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
                        "revision": m.group(2),
                        # The prcs info command returns the local time.
                        "date": mktime(parsedate(m.group(3))),
                        "author": m.group(4),
                        "deleted": bool(m.group(5))
                    }
        else:
            sys.stderr.write(err)
        return revisions

    def checkout(self, files = None, revision = None):
        flags = ["-fqu"]
        if files is None:
            files = []
        if revision is not None:
            flags.extend(["-r", revision])
        out, err = self._run_prcs(["checkout"] + flags + [self.name] + files)
        if err:
            sys.stderr.write(err)

    def _run_prcs(self, args, input = None):
        """run a PRCS subprocess."""
        prcs = Popen(["prcs"] + args, stdin = PIPE, stdout = PIPE,
                stderr = PIPE)
        return prcs.communicate(input)
