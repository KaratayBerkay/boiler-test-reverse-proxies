#!/bin/sh
# mod_md MDMessageCmd hook: a renewed certificate only becomes active after a graceful reload. The hook runs as the
# unprivileged child user and cannot signal the parent, so it drops a flag that the root-level loop in compose.yaml
# turns into `httpd -k graceful`. $1 = reason (renewed|installed|expiring|errored|...), $2 = domain
echo "md-message: $1 $2" >&2
if [ "$1" = "renewed" ] || [ "$1" = "installed" ]; then
    touch /md/reload.flag
fi
exit 0
