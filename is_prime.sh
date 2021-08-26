#!/bin/bash
# interpreter for the symlink-based xterm turing machine
cd src
cat init
read
cat postinit
for ((;;)); do
	read -r -N22 input
	cd -P "${input}"
	cat w
done

