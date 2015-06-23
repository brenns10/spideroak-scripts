#!/usr/bin/env python3
"""Selected tools for interacting with SpiderOak on Linux."""

from subprocess import check_output
from datetime import datetime
import re
import os.path

TIME_FORMAT = '%a %b %d %H:%M:%S %Y'


class ParseError(ValueError):
    """An exception to raise when parsing stuff."""
    pass


class ChangelogEntry(object):
    """
    Represents an entry in the SpiderOak changelog.

    This is parsed directly out of SpiderOak's output.  Fields are:
    - time: Time of transaction (I assume)
    - action: What was done? (add, update, delete)
    - target: File name for the action (no path, just name)
    - type: file or dir
    - mode, uid, gid: exactly what you'd expect (ints)
    - size: File size in bytes, as int.
    - mtime, ctime: Times modified and created, respectively (I assume)
    """

    def __init__(self, triplet):
        """Create Changelog Entry using triplet of string lines."""
        # Regular expression construction for a changelog entry.
        time_re = r'[a-zA-Z]{3} [a-zA-Z]{3}\s+\d+ \d\d:\d\d:\d\d \d{4}'
        l1 = r'(?P<time>' + time_re + ')' r':\s+(?P<action>\w+)\s+u'\
             '(?P<q>\'|")' r'(?P<target>.*)(?P=q)'
        l2 = r'\s*type:(?P<type>\w+)\s+mode:(?P<mode>\d+)\s+uid:(?P<uid>\d+)' \
             r'\s+gid:(?P<gid>\d+)\s+size:(?P<size>\d+)'
        l3 = r'\s*mtime:(?P<mtime>' + time_re + r')\s+ctime:(?P<ctime>' + \
             time_re + r')'
        final_re = '\n'.join([l1, l2, l3])

        # Match the regular expression against the input.
        self.string = '\n'.join(triplet)
        match = re.fullmatch(final_re, self.string)
        if match is None:
            raise ParseError('SpiderOak output matched incorrectly.')

        # Update this object with the captured groups.
        self.__dict__.update(match.groupdict())

        # Convert to expected data types for each captured value
        self.time = datetime.strptime(self.time, TIME_FORMAT)
        self.mtime = datetime.strptime(self.mtime, TIME_FORMAT)
        self.ctime = datetime.strptime(self.ctime, TIME_FORMAT)
        self.mode = int(self.mode)
        self.uid = int(self.uid)
        self.gid = int(self.gid)
        self.size = int(self.size)

    def __str__(self):
        return '<ChangelogEntry: %r at %s>' % \
            (self.target, self.time.strftime(TIME_FORMAT))

    def __repr__(self):
        return self.string


def n_tuples(l, n=2):
    """
    Take any arbitrary iterable and return n-tuples from it (pairs by default).

    For example, n_tuples([1, 2, 3, 4, 5, 6]) returns a generator that yields
    [(1,2), (3,4), (5,6)].  Note that remainders from the input list are
    truncated, so you can be certain that every element in the output is a full
    tuple.
    """
    return (t for t in zip(*[l[i::n] for i in range(n)]))


def journal_changelog(folder):
    """
    Get the changelog for a SpiderOak folder or journal.

    This is a simple wrapper around "SpiderOak --journal-changelog".  However,
    it's nicer because it parses the output and returns a list of
    ChangelogEntrys instead of the text output that SpiderOak CLI gives you.
    The folder can be relative or absolute, but it has to resolve from the
    current directory.  That is, it can't start from the SpiderOak hive folder
    unless you are currently in that folder.
    """
    output = check_output(['SpiderOak', '--journal-changelog', folder],
                          universal_newlines=True)
    lines = output.split('\n')
    entries = [ChangelogEntry(t) for t in n_tuples(lines, n=3)]
    return entries


def file_changelog(filename):
    """Return the changelog for a single file."""
    fullname = os.path.abspath(filename)
    directory = os.path.dirname(fullname)
    name = os.path.basename(fullname)
    log = journal_changelog(directory)
    log = [l for l in log if l.target == name]
    return log
