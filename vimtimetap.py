#!/usr/bin/env python3

# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""Collect and display time data saved by Vim TimeTap.

Gather, filter, and summarize time data saved by the Vim time-tracking
plugin by Rainer Borene, vim-timetap: github.com/rainerborene/vim-timetap.

"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta
from enum import IntEnum, auto


class DatabaseDisplayKey(IntEnum):
    DATE = auto()
    PATH = auto()
    TREE = auto()
    FILENAME = auto()
    FILETYPE = auto()


class TrieNode(object):

    def __init__(self, value):
        self.value = value
        self.goto = {}


TIMETAP_DIR = os.path.expanduser("~/.timetap")


def main():
    """Print summaries of the data collected by Vim TimeTap.

    """
    parser = _get_parser()
    args = parser.parse_args()

    if args.check:
        check_database()
        return

    # It's not worth throwing an error if negative: just fix it
    args.units_past = abs(args.units_past)

    try:
        end_date = datetime(year=args.end_year, month=args.end_month, day=args.end_day)
    except ValueError as err:
        # An invalid end date
        parser.error(err.message.lower())

    # Each arg returns the number of days in its unit or 0 (and only one
    # can be nonzero)
    unit_size = max(1, args.years + args.months + args.weeks)
    if args.all or args.units_past == 0:
        start_date = None
    else:
        start_date = end_date - timedelta(days=(unit_size*args.units_past-1))

    # args.exclude need not be evaluated if args.all is True or
    # (equivalently) units_past is 0
    if args.exclude and start_date is not None:
        end_date = end_date - timedelta(days=1)
        if end_date < start_date:
            start_date = end_date

    if start_date and end_date < start_date:
        error_msg = "end date (" + end_date.strftime("%Y %b %d") + ") precedes "
        error_msg += " start date (" + start_date.strftime("%Y %b %d") + ")"
        parser.error(error_msg)

    key_type = _parse_database_display_key(args)

    time_per_type = {}
    database = []
    for database_filename in generated_database_filenames(start_date, end_date):
        populate_database_dict(database_filename, time_per_type, key_type=key_type)
        if key_type == DatabaseDisplayKey.DATE:
            # `generated_database_filenames` already returns them in order
            # from earliest to latest
            date = _parse_date(database_filename)
            try:
                database.append((date, time_per_type[date]))
            except KeyError:
                pass

    # By default, the regex used for filtering matches everything
    regex = r"(^.*$)"
    if args.filter is not None:
        regex = args.filter
        filter_database_dict(time_per_type, regex)

    tree = False
    if key_type == DatabaseDisplayKey.DATE:
        # Don't alter database: it's already been set up above
        pass
    elif key_type == DatabaseDisplayKey.TREE:
        tree = True
        # Conversion to list is not strictly required since the function
        # this will be passed to just expects an iterable
        database = time_per_type.items()
    else:
        # Sort from most to least time
        database = sorted(time_per_type.items(), key=lambda tup: tup[1], reverse=True)

    if args.verbose:
        _print_filter_and_sort(key_type, regex)
        print()
        print("{} entries".format(len(database)))
        print()

    print_database(database, start_date, end_date=end_date, tree=tree)


def _parse_database_display_key(args):
    # Return a `DatabaseDisplayKey` constant based on `argparse` args
    if args.dates:
        return DatabaseDisplayKey.DATE
    elif args.tree:
        return DatabaseDisplayKey.TREE
    elif args.paths:
        return DatabaseDisplayKey.PATH
    elif args.names:
        return DatabaseDisplayKey.FILENAME

    return DatabaseDisplayKey.FILETYPE


def _print_filter_and_sort(key_type, regex):
    # Print how the data is being filtered and sorted
    print('{} -> {}'.format(key_type.name, regex))
    print()

    if key_type == DatabaseDisplayKey.DATE:
        print("sorted from least to most recent date")
    elif key_type == DatabaseDisplayKey.TREE:
        print("sorted hierarchically and then alphabetically")
    else:
        print("sorted from max to min time")


def check_database():
    """Check for inconsistencies between full database and date databases.

    """
    key_type = DatabaseDisplayKey.PATH

    # Get data from all database files of the 'YYYYMMDD.db' variety
    by_date_time_per_file = {}
    for filename in os.listdir(TIMETAP_DIR):
        if filename != "full.db":
            populate_database_dict(filename, by_date_time_per_file, key_type=key_type)

    # Get data from 'full.db'
    full_time_per_file = {}
    populate_database_dict("full.db", full_time_per_file, key_type=key_type)

    # Combine data
    joined_per_file = {}
    for filename, time in by_date_time_per_file.items():
        # The last elem in the list will be the time for the same file from
        # `full_time_per_file` (if it exists there)
        joined_per_file[filename] = [time, 0]
    for filename, time in full_time_per_file.items():
        try:
            joined_per_file[filename][1] = time
        except KeyError:
            # Filename in `full_time_per_file` that was not in
            # `by_date_time_per_file`
            joined_per_file[filename] = [0, time]

    # Find and display differences
    total_seconds_difference = 0
    # Where `x` represents (filename, [by_date_time, full_time])
    inconsistent_entries = filter(lambda x: x[1][0] != x[1][1], joined_per_file.items())
    for filename, times in sorted(inconsistent_entries, key=lambda x: x[0]):
        print("{}:".format(filename))
        print("\t{} vs {} s (date database vs full)".format(*times))
        total_seconds_difference += abs(times[1] - times[0])
    print("TOTAL:")
    print("\t{} s".format(total_seconds_difference))
    print()


def generated_database_filenames(start_date, end_date=None):
    """Return sorted filenames matching the given date range.

    Generate TimeTap-style filenames (YYYYMMDD.db) for all dates from
    `start_date` to `end_date` inclusive in order from filenames representing
    the earliest data to those representing the latest.

    Parameters
    ----------
    start_date : datetime instance
        The earliest date to generate the TimeTap-style filename for.
    end_date : datetime instance, optional
        The latest date to generate the TimeTap-style filename for (default
        today).

    Returns
    -------
    list of str
        A list of TimeTap-style filenames between `start_date` and
        `end_date` inclusive or a list containing only the filename of the
        full database if `start_date` is None.

    Examples
    --------
    >>> from datetime import datetime
    >>> import vimtimetap
    >>> start_date = datetime(year=2017, month=10, day=29)
    >>> end_date = datetime(year=2017, month=11, day=2)
    >>> vimtimetap.generated_database_filenames(start_date, end_date=end_date)
    ['20171029.db', '20171030.db', '20171031.db', '20171101.db', '20171102.db']

    """
    if start_date is None:
        return ["full.db"]
    elif end_date is not None and end_date < start_date:
        return []

    database_filenames = []
    end_date = datetime.today() if end_date is None else end_date

    while not _equal_dates(start_date, end_date):
        # The files are of the form YYYYMMDD.db, e.g., 20170310.db
        filename = start_date.strftime("%Y%m%d") + ".db"
        database_filenames.append(filename)
        start_date = start_date + timedelta(days=1)

    # Include the file for `end_date`
    filename = start_date.strftime("%Y%m%d") + ".db"
    database_filenames.append(filename)

    # This will be in order from earliest date to latest
    return database_filenames


def populate_database_dict(database_filename, database_dict, key_type=None):
    """Populate given database dictionary with data from given file.

    Add or update mappings of names (e.g., filenames, dates---the exact
    format is determined by `key_type`) to the number of seconds associated
    with that name based on data in the file called `database_filename`,
    which has a format like the following:

    {'/tmp/crontab.t1M3Tp/crontab': {'total': 134}}
    {'/etc/ssmtp/ssmtp.conf': {'total': 1873}}
    {'/home/user/.bashrc': {'total': 636}}

    Parameters
    ----------
    database_filename : str
        The name of a file in `TIMETAP_DIR` from which data will be pulled
        to add to or update `database_dict`.
    database_dict : dict of str to int
        A mapping of names (e.g., of filenames, paths, dates, etc.) to the
        number of seconds associated with each name, which will be updated
        with new mappings or incremented times.
    key_type : DatabaseDisplayKey constant, optional
        A constant that determines what type of key is used in populating
        the `database_dict` (default DatabaseDisplayKey.FILETYPE).

    """
    key_type = DatabaseDisplayKey.FILETYPE if key_type is None else key_type
    timetap_db = os.path.join(TIMETAP_DIR, database_filename)

    try:
        with open(timetap_db, "r") as database:
            data = database.read().splitlines()
    except IOError:
        return

    if key_type == DatabaseDisplayKey.DATE:
        # This will be the same for all lines in `data`, so it's not worth
        # recalculating it each iteration
        file_date = _parse_date(database_filename)

    for line in data:
        # For lines like "{'/home/user/test.py': {'total': 104}}"
        # json properties should use double quotes; the lines use single
        line_dict = json.loads(line.replace("'", '"'))

        # Only one path key should be in each `line_dict`
        assert len(line_dict) == 1
        path = list(line_dict).pop()
        seconds = line_dict[path]["total"]

        if key_type == DatabaseDisplayKey.DATE:
            filetitle = file_date
        elif key_type == DatabaseDisplayKey.PATH or key_type == DatabaseDisplayKey.TREE:
            filetitle = path
        elif key_type == DatabaseDisplayKey.FILENAME:
            filetitle = os.path.basename(path)
        else:
            filetitle = _parse_filetype(path)

        try:
            database_dict[filetitle] += seconds
        except KeyError:
            database_dict[filetitle] = seconds


def _parse_date(filename):
    # Return a %Y %b %d formatted string based on TimeTap database filename
    try:
        # `filename` has the form "YYYYMMDD.db"
        file_year = int(filename[:4])
        file_month = int(filename[4:6])
        file_day = int(filename[6:8])
    except ValueError:
        # "full.db", the datebase containing all data, is the only TimeTap
        # database file whose name doesn't follow the "YYYYMMDD.db" format
        assert filename == "full.db"
        return "ALL"

    # These should always be valid
    file_date = datetime(year=file_year, month=file_month, day=file_day)
    return file_date.strftime("%Y %b %d")


def _parse_filetype(path):
    # Return filetype of filename at end of given path
    _, extension = os.path.splitext(path)
    extension = "*" + extension if extension else os.path.basename(path)
    extension = extension if extension else "OTHER"
    return extension


def filter_database_dict(database_dict, regex):
    """Remove items in database dict whose keys don't matching the regex.

    Parameters
    ----------
    database_dict : dict of str to int
        A mapping of names (e.g., of filenames, paths, dates, etc.) to the
        number of seconds associated with each name, whose keys will be
        filtered according to regular expression defined by `regex`.
    regex : str
        A string representing a regular expression; only items in
        `database_dict` whose keys match this regular expression will be
        remain in `database_dict`.

    """
    regex_engine = re.compile(regex)
    filetitles_to_delete = []

    for filetitle in database_dict:
        if regex_engine.match(filetitle) is None:
            filetitles_to_delete.append(filetitle)

    for filetitle in filetitles_to_delete:
        del database_dict[filetitle]


def print_database(database, start_date, end_date=None, tree=False):
    """Print database in sequential order with a title and sum.

    Print the number of hours, minutes, and seconds associated with each
    filename, path, or date in `database` along with a title based on
    `start_date` and `end_date` at the beginning and a sum at the end.

    Parameters
    ----------
    database : iterable of (str, int) tuple
        An iterable of tuples of the form (NAME, SECONDS), where NAME is a
        string representing, for instance, a filename, path, or date, and
        SECONDS is the number of seconds associated with that filename,
        path, or date.
    start_date : datetime instance
        The earliest date covered by data in `database`, which is used in
        creating the title printed.
    end_date : datetime instance, optional
        The latest date covered by data in `database`, which is used in
        creating the title printed (default today).
    tree : bool, optional
        True if the database should be printed in tree order (which assumes
        the keys in `database` are paths), and False if they should be
        printed in the order given without any hierarchy (default False).

    """
    if tree:
        _print_database_as_tree(database, start_date, end_date=end_date)
        return

    title = _get_title(start_date, end_date)
    foottype = "SUM"

    # The max length of the label before a given time (e.g., "*.py",
    # "crontab", etc.)
    try:
        max_type_len = max([len(filetitle) for filetitle, _ in database])
    except ValueError:
        # `database` is empty
        max_type_len = 0
    max_type_len = max(max_type_len, len(foottype))

    # 16 is the length of the part after the type, e.g., "      3h 01m 15s"
    max_entry_len = max_type_len + 16
    text_width = max(len(title), max_entry_len)
    # Padding to center the title
    padding = " " * ((text_width - len(title)) // 2)

    # Increase width to make title truly centered
    if len(padding) % 2:
        padding += " "
        text_width += 1

    print("{}{}".format(padding, title))
    print("=" * text_width)

    # Adjust max_type_len to center data as best as possible below
    max_type_len += ((text_width - max_entry_len) // 2)
    overall_seconds = 0

    for filetitle, raw_seconds in database:
        overall_seconds += raw_seconds
        padding = " " * (max_type_len - len(filetitle))
        # >6: 1000000h+ programmers can deal with misaligned text
        print("{}{} {:>6}h {:02}m {:02}s".format(padding, filetitle,
                                                 *_seconds_to_hms(raw_seconds)))

    padding = " " * (max_type_len - len(foottype))

    print("-" * text_width)
    print("{}{} {:>6}h {:02}m {:02}s".format(padding, foottype, *_seconds_to_hms(overall_seconds)))
    print()


def _get_title(start_date, end_date=None):
    # Return string title based on given days to include up to end date
    if start_date is None:
        title = "All Time"
    elif end_date is not None and _equal_dates(start_date, end_date):
        today = datetime.today()
        yesterday = today + timedelta(days=-1)
        if _equal_dates(end_date, today):
            title = "Today"
        elif _equal_dates(end_date, yesterday):
            title = "Yesterday"
        else:
            title = end_date.strftime("%Y %b %d")
    else:
        end_date = datetime.today() if end_date is None else end_date
        start_date_str = start_date.strftime("%Y %b %d")
        end_date_str = end_date.strftime("%d")
        if start_date.month != end_date.month or start_date.year != end_date.year:
            end_date_str = end_date.strftime("%b") + " " + end_date_str
        if start_date.year != end_date.year:
            end_date_str = end_date.strftime("%Y") + " " + end_date_str
        title = "{} to {}".format(start_date_str, end_date_str)

    return title


def _seconds_to_hms(seconds):
    # Convert seconds into a sum of hours, minutes, and seconds
    minutes = seconds // 60
    seconds %= 60
    hours = minutes // 60
    minutes %= 60
    return hours, minutes, seconds


def _equal_dates(date1, date2):
    # Return True if dates equal based on years, months, and days of month
    return date1.strftime("%x") == date2.strftime("%x")


def _print_database_as_tree(database, start_date, end_date=None):
    # Print database in tree order.
    path_trie = TrieNode(0)

    # Assumes the database contains paths, not file types or filenames
    for file_path, raw_seconds in database:
        node = path_trie
        node.value += raw_seconds
        for directory in _directories_in_path(file_path):
            try:
                node = node.goto[directory]
                node.value += raw_seconds
            except KeyError:
                node.goto[directory] = TrieNode(raw_seconds)
                node = node.goto[directory]

    tree_entries = []
    _populate_database_tree_entries(path_trie, tree_entries)

    title = _get_title(start_date, end_date)
    print(title)
    print()

    if not tree_entries:
        tree_entries.append("0h 00m 00s /")
    for entry in tree_entries:
        print(entry)

    print()


def _populate_database_tree_entries(database_trie, entries, indent=0, time_width=0):
    # Populate entries with formatted strings derived from database_trie
    tab_width = 2
    # The band of characters connecting times to directories/filenames
    leader = "- " * (indent // 2)

    if not database_trie.goto:
        return
    for directory in sorted(database_trie.goto):
        seconds = database_trie.goto[directory].value
        time = "{}h {:02}m {:02}s ".format(*_seconds_to_hms(seconds))
        # Set `time_width` based on root, which has longest `len(time)`
        # since it's the overall sum
        if time_width == 0:
            time_width = len(time)
        entry = " " * (time_width - len(time))
        entry += time
        entry += leader
        entry += directory
        # Append '/' to directories (aside from root)
        if database_trie.goto[directory].goto and indent:
            entry += "/"
        entries.append(entry)
        _populate_database_tree_entries(database_trie.goto[directory], entries,
                                        indent=indent+tab_width, time_width=time_width)


def _directories_in_path(path):
    # Return an iterator of directories/file along a given path
    directories = []
    head, tail = os.path.split(path)

    while tail:
        directories.append(tail)
        # `os.path.split("/")` equals `("/", "")`, so this loop ends when
        # `head` is the path to the root directory
        head, tail = os.path.split(head)

    # Append root directory
    directories.append(head)

    # Return directories in order from closest to root to farthest
    return reversed(directories)


def _get_parser():
    # Return the commandline argument parser for the application
    parser = argparse.ArgumentParser(description="Display summaries for Vim TimeTap.")

    parser.add_argument("units_past", metavar="UNITS", nargs="?", type=int, default=1,
                        help="number of days up through the end date to summarize (default: 1)")

    # For universally modifying the time range
    parser.add_argument("-a", "--all", action="store_true",
                        help="ignore other time options and summarize all time")
    parser.add_argument("-x", "--exclude", action="store_true",
                        help="subtract one day from the end date")

    # For specifying an absolute end date
    today = datetime.today()
    parser.add_argument("-Y", "--end-year", metavar="YEAR", type=int, default=today.year,
                        help="specify the end year instead of using the current year")
    parser.add_argument("-M", "--end-month", metavar="MONTH", type=int, default=today.month,
                        help="specify the end month instead of using the current month")
    parser.add_argument("-D", "--end-day", metavar="DAY", type=int, default=today.day,
                        help="specify the end day of month instead of using the current day")

    # For changing the time unit from days
    unit_size_group = parser.add_mutually_exclusive_group()
    unit_size_group.add_argument("-y", "--years", action="store_const", const=365, default=0,
                                 help="change the time unit from days to 365-day years")
    unit_size_group.add_argument("-m", "--months", action="store_const", const=30, default=0,
                                 help="change the time unit from days to 30-day months")
    unit_size_group.add_argument("-w", "--weeks", action="store_const", const=7, default=0,
                                 help="change the time unit from days to weeks")

    # For changing how data is displayed
    display_group = parser.add_mutually_exclusive_group()
    display_group.add_argument("-d", "--dates", action="store_true",
                               help="display dates instead of file types")
    display_group.add_argument("-n", "--names", action="store_true",
                               help="display filenames instead of file types")
    display_group.add_argument("-p", "--paths", action="store_true",
                               help="display full path instead of file types")
    display_group.add_argument("-t", "--tree", action="store_true",
                               help="display path tree instead of file types")

    # For changing what data is included
    parser.add_argument("-f", "--filter", metavar="REGEX",
                        help="filter entries according to the provided regex")

    # other
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="display filter and sort information")
    parser.add_argument("-c", "--check", action="store_true",
                        help="check for inconsistencies in the databases then exit")

    return parser


if __name__ == "__main__":
    main()
