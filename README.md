timetap.vim CLI
===============
An unofficial commandline interface for Rainer Borene's time tracking
plugin for Vim, [vim-timetap](https://github.com/rainerborene/vim-timetap).


Installation
------------
```shell
# clone the repository
$ git clone https://github.com/HunterBaines/vim-timetap-cli.git

# change into the project's root directory
$ cd vim-timetap-cli/

# make sure the program is executable
$ chmod +x vim-timetap.py

# copy the program (minus its extension) to some directory in your PATH, e.g.:
$ cp vim-timetap.py ~/.local/bin/vim-timetap
```

If you already have
[vim-timetap](https://github.com/rainerborene/vim-timetap) installed, you
should now be able to do something like this:

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
