Use an xterm with more than 120 columns and execute is_prime.sh to check whether a number is prime.

How does this work?

I suggest replacing the `for ((;;))` with `while sleep 0.1` to see the evaluation in slow.
You will notice it is basically a turing machine with two tapes.

In src, there is a number of directories, each containing a series of cryptic symlinks and a file w.
Each directory corresponds to an element of "State x Symbol1 x Move1 x Symbol2 x Move2" from the transition function.

The file w contains the terminal escape codes necessary to modify the tapes and move them in the wanted direction.
It also contains two escape codes from the end which direct the terminal to report the checksum of the characters
under the read head.

This gets read using the read command in the loop of the is_prime.sh file. The symlink names correspond to the
possible responses from the terminal and they link to the new state/symbol/move directory.

The turing machine is specified manually in tools/generator.py and is basically just dumb trial division.
