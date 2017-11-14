#!/usr/bin/env bash

# Send monospaced text from stdin using mutt.
# Usage: ./cron-mail.sh SUBJECT ADDRESS

# You may need to change this to `$HOME/.mutt/muttrc` or use the full path
# since cron may not use the HOME you want
MUTTRC="$HOME/.muttrc"

SUBJECT="$1"
TO_ADDRESS="$2"

(
    # Even though /bin/ is likely in cron's PATH, it's best not to assume
    /bin/echo '<html><body>'
    /bin/echo '<pre style="font: monospace">'
    # Get body from stdin
    /bin/cat
    /bin/echo '</pre>'
    /bin/echo '</body></html>'
) | /usr/bin/mutt -F "$MUTTRC" -e "set content_type=text/html" -s "$SUBJECT" "$TO_ADDRESS"
