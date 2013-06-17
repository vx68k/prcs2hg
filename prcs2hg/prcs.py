#
# Copyright (C) 2012-2013  Kaz Nishimura
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

import re
from time import mktime
from email.utils import parsedate
from subprocess import Popen, PIPE
import sexpdata

class Project(object):

    def __init__(self, name):
        """construct a Project object."""
        self.name = name

    def revisions(self):
        out, err = self._run_prcs(["info", "-f", self.name]);

        revisions = {}
        if (not err):
            for line in out.splitlines():
                m = re.match("^[^ ]+ ([^ ]+) (.+) by (.+)", line)
                revisions[m.group(1)] = {
                    "date": mktime(parsedate(m.group(2))),
                    "user": m.group(3)
                }
        else:
            sys.stderr.write(err)
        return revisions

    def _run_prcs(self, args, input = None):
        """run a PRCS subprocess."""
        prcs = Popen(["prcs"] + args, stdin = PIPE, stdout = PIPE,
                stderr = PIPE)
        return prcs.communicate(input)
