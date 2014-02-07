\[**Note**: this file _should not_ be distributed with the prcs2hg package.\]

This repository contains the source code for prcs2hg, which is a command to convert a [PRCS][] project to [Mercurial][] revisions.
It would help you publish the revision history of an obsolete project whose changes were maintained with [PRCS][].

prcs2hg is free software: you can redistribute it and/or modify it under the conditions specified in each file.
The main part of prcs2hg is licensed with the [OSI-approved MIT License][].

For more information about prcs2hg, visit the prcs2hg project at <http://www.vx68k.org/prcs2hg>.

[PRCS]: <http://prcs.sourceforge.net/>
[Mercurial]: <http://mercurial.selenic.com/>
[OSI-approved MIT License]: <http://opensource.org/licenses/MIT>

## Third-party components

The file 'prcs/sexpdata.py' was copied from the [sexpdata][] package and
modified not to parse numbers so that we can handle version numbers correctly.

[sexpdata]: <https://github.com/tkf/sexpdata>
