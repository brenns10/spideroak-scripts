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

    __regex = None

    def _set_datetime(self, kwargs, name):
        v = kwargs.pop(name)
        if isinstance(v, str):
            v = datetime.strptime(v, TIME_FORMAT)
        setattr(self, name, v)

    def __init__(self, **kwargs):
        """Create a ChangelogEntry with given arguments."""
        self._set_datetime(kwargs, 'time')
        self.action = str(kwargs.pop('action'))
        self.target = str(kwargs.pop('target'))
        self.type = str(kwargs.pop('type'))
        self.mode = int(kwargs.pop('mode'))
        self.uid = int(kwargs.pop('uid'))
        self.gid = int(kwargs.pop('gid'))
        self.size = int(kwargs.pop('size'))
        self._set_datetime(kwargs, 'mtime')
        self._set_datetime(kwargs, 'ctime')
        if kwargs:
            raise ValueError('too many arguments to ChangelogEntry()')

    @classmethod
    def regex(cls):
        """Return the regular expression for a ChangelogEntry."""
        if cls.__regex is not None:
            return cls.__regex

        # Regular expression for a time
        time_re = (
            r'[a-zA-Z]{3}\s+'        # Month (eg Jun)
            r'[a-zA-Z]{3}\s+'        # Day   (eg Mon)
            r'\d+\s+'                # Day of month (eg 1 or 20)
            r'\d\d:\d\d:\d\d \d{4}'  # hour:minute:second year
        )

        # l1 eg: Mon Jun 1 12:34:56 2015: add u'blah blah blah.pdf'
        l1 = (
            r'(?P<time>' + time_re + '):\s+'  # capture the time
            r'(?P<action>\w+)\s+'             # capture the action
            'u(?P<q>\'|")'                    # capture the quoting style
            r'(?P<target>.*)'                 # capture the filename
            r'(?P=q)'                         # match consistent quote
        )
        # l2 eg:   type:add mode:123456 uid:1000 gid:1000 size:4096
        l2 = (
            r'\s*'                       # consume initial whitespace
            r'type:(?P<type>\w+)\s+'     # type (has whitespace in front)
            r'mode:(?P<mode>\d+)\s+'     # mode (integer)
            r'uid:(?P<uid>\d+)\s+'       # uid (integer)
            r'gid:(?P<gid>\d+)\s+'       # gid (integer)
            r'size:(?P<size>\d+)'        # size (integer)
        )
        # l3 eg:   mtime:Mon Jun 1 12:34:56 2015  ctime:Mon Jun 1 12:34:56 2015
        l3 = (
            r'\s*'                                   # consume whitespace
            r'mtime:(?P<mtime>' + time_re + r')\s+'  # mtime
            r'ctime:(?P<ctime>' + time_re + r')'     # ctime
        )

        # Combine the three lines into a single regular expression.
        final_re = '\n'.join([l1, l2, l3])

        cls.__regex = re.compile(final_re)
        return cls.__regex

    @classmethod
    def parse(cls, triplet):
        """Create Changelog Entry using triplet of string lines."""
        # Match the regular expression against the input.
        string = '\n'.join(triplet)
        match = cls.regex().fullmatch(string)
        if match is None:
            raise ParseError('SpiderOak output matched incorrectly.')

        # Update this object with the captured groups.
        capture = match.groupdict()
        del capture['q']
        return ChangelogEntry(**capture)

    def __str__(self):
        return '<ChangelogEntry: %s %r at %s>' % \
            (self.action, self.target, self.time.strftime(TIME_FORMAT))

    def __repr__(self):
        return 'ChangelogEntry(' + \
            ', '.join(['%s=%r' % x for x in self.__dict__.items()]) + ')'


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
    entries = [ChangelogEntry.parse(t) for t in n_tuples(lines, n=3)]
    return entries


def file_changelog(filename):
    """Return the changelog for a single file."""
    fullname = os.path.abspath(filename)
    directory = os.path.dirname(fullname)
    name = os.path.basename(fullname)
    log = journal_changelog(directory)
    log = [l for l in log if l.target == name]
    return log
