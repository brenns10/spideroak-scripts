"""Script to (hopefully) fix messed up size 0 files in SpiderOak."""

from spideroak import file_changelog
from subprocess import check_output


def last_nonzero(filename):
    """Return the last ChangelogEntry where size != 0  for a file."""
    for e in reversed(file_changelog(filename)):
        if e.size != 0:
            return e
    return None


def main():
    """Main entry point for SpiderOak repair script."""
    find_output = check_output(['find', '-size', '0c'],
                               universal_newlines=True)
    filenames = [f for f in find_output.split('\n') if f]
    print('# empties: ', len(filenames))

    for f in filenames:
        ln = last_nonzero(f)
        if ln is None:
            print('*file %s was NEVER nonzero')
        else:
            print('file %s was %d bytes at %r' % (f, ln.size, ln.time))


if __name__ == '__main__':
    main()
