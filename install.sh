#!/usr/bin/env bash

# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

PS3="Where do you want to install the program? "

# Parse the paths in PATH into separate lines for easier manipulation
path_lines="$(tr ':' '\n' <<< "$PATH" | sort -u)"
path_count="$(wc -l <<< "$path_lines")"

# If any path in `preferred_paths` is in actual PATH, use it as a default
preferred_paths=("$HOME/bin" "$HOME/.local/bin")
default_path=
for path in "${preferred_paths[@]}"; do
    if grep -q "$path" <<< "$path_lines"; then
        default_path="$path"
        # Update prompt to indicate the default
        PS3="${PS3}[$default_path] "
        break
    fi
done

# Convert path lines into array for easier access to elements
readarray -t all_paths <<< "$path_lines"

# Get the path where the user wants to install the program
chosen_path=
while true; do
    # Print all path options
    for i in "${!all_paths[@]}"; do
        # Pad each selection number by the number of digits in `path_count`
        printf "%${#path_count}d) %s\n" "$(( i + 1 ))" "${all_paths[i]}"
    done
    echo

    # Get desired path option from user
    read -p "$PS3" chosen_number

    # If user just typed ENTER and a default path is defined, use it
    if [[ -z $chosen_number && -n $default_path ]]; then
        chosen_path="$default_path"
        break
    fi

    # If not using the default path option, validate the one chosen
    decimal_int='^[\+\-]?[0-9]+$'
    if ! [[ $chosen_number =~ $decimal_int ]]; then
        (>&2 echo "error: input is not an integer")
    elif [[ $chosen_number -le 0 || -z "${all_paths[chosen_number - 1]}" ]]; then
        # Bash allows negative indices, so the first test above is needed
        (>&2 echo "error: integer is out of range")
    else
        chosen_path="${all_paths[chosen_number - 1]}"
        break
    fi
    echo
done

# Install the program in the user-selected path
source_name="vimtimetap.py"
executable_name="vim-timetap"
if [[ -n $chosen_path ]]; then
    cp "$source_name" "$executable_name"
    chmod +x "$executable_name"
    if ! mv -vi "$executable_name" "$chosen_path"; then
        # mv failed, most likely due to permission problem
        (>&2 echo)
        (>&2 echo "To complete install, consider running this command:")
        (>&2 echo "sudo mv -vi \"$executable_name\" \"$chosen_path\"")
    fi
fi
