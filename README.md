timetap.vim CLI
===============
An unofficial commandline interface for Rainer Borene's time-tracking
plugin for Vim, [vim-timetap](https://github.com/rainerborene/vim-timetap).


Installation
------------
```shell
# clone the repository
$ git clone https://github.com/HunterBaines/vim-timetap-cli.git

# change into the project's root directory
$ cd vim-timetap-cli/

# copy the program into what you want the executable to be called, e.g.:
$ cp vimtimetap.py vim-timetap

# make this newly copied file executable
$ chmod +x vim-timetap

# move this newly executable file to somewhere in your PATH, e.g.:
$ mv vim-timetap ~/.local/bin/
```

If you already have
[vim-timetap](https://github.com/rainerborene/vim-timetap#installation)
installed, you should now be able to do something like this:

```shell
# edit a random file in Vim and write the changes
$ vim temp.c

# display the time spent editing this file and any others today
$ vim-timetap --name
        Today
======================
temp.c      0h 00m 04s
----------------------
   SUM      0h 00m 04s
```


Usage
-----
To generate a summary, the program needs to know an end date and the number
of days up until that end date to include. By default, the end date is
today and the number to include is 1. Therefore, the command with no
arguments displays a summary of today:

```shell
$ vim-timetap
            Today
==============================
          *.py      6h 00m 58s
          *.md      1h 09m 07s
           *.c      0h 09m 10s
COMMIT_EDITMSG      0h 02m 43s
------------------------------
           SUM      7h 21m 58s

```

The number of days to include is specified via the program's only
positional argument. So to print a summary of the last week on 2017
November 11, for example, this works:

```shell
$ vim-timetap 7
      2017 Nov 05 to 11
==============================
          *.py      9h 25m 17s
          *.md      1h 25m 14s
 .bash_profile      0h 50m 21s
COMMIT_EDITMSG      0h 24m 27s
           *.c      0h 09m 10s
       .muttrc      0h 07m 21s
 .bash_aliases      0h 04m 34s
       .bashrc      0h 01m 15s
         *.txt      0h 00m 05s
------------------------------
           SUM     12h 27m 44s

```


### Changing the Unit ###
Use `--years`, `--months`, or `--weeks` to change the unit from days to
365-day years, 30-day months, or weeks, respectively. Thus, the command
`vim-timetap 7` is equivalent to `vim-timetap --weeks` or, since the
default unit amount is still 1, `vim-timetap --weeks 1`


### Changing the End Date ###
Use the arguments `--end-year YEAR`, `--end-month MONTH`, and `--end-day
DAY` to specify the end date. Any missing arguments will default to the
current year, month, or day, respectively. So, for example, to see what you
were working on in 2016 on this day, `vim-timetap --end-year 2016` could be
used.

To subtract one day from the end date, use `--exclude`: `vim-timetap
--exclude`, therefore, displays a summary of yesterday. 


### Changing the Format of Output ###
By default, entries are grouped by file extension. Use `--names` to display
filenames instead (e.g., "vimtimetap.py") and `--paths` to display the
full path to each file (e.g., "/home/user/vim-timetap-cli/vimtimetap.py").
To display paths organized as a tree, use `--tree`. And, finally, use
`--dates` to display dates instead of file information.


### Changing What's Included in Output ###
To ignore other time options and simply include all data, use `--all`.

To filter the output, use `--filter REGEX`. For example, time spent on this
project could be found using `vim-timetap --all --paths --filter
".*/vim-timetap-cli/.*"`.
