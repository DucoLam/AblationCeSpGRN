#!/bin/sh
# Password helper for ssh (SSH_ASKPASS): prints the DAIC password from the repo's .env (pass=...).
# Lets tools that cannot show ssh's password prompt, such as lazyslurm's remote mode on macOS, log in:
#   SSH_ASKPASS=ablation/tools/askpass.sh SSH_ASKPASS_REQUIRE=force lazyslurm -H ducolam@login.daic.tudelft.nl
. "$(dirname "$0")/../../.env"
printf '%s\n' "$pass"
