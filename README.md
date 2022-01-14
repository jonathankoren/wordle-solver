# Command Line Wordle Solver

## Solver
Usage: ./solver.py [word_length]

Defaults to words of length 5

See `--help` for all options.

Reads from STDIN the results of the previous guess, and outputs a list of next
guesses.

The initial guess is given by a blank line.

The result of a guess are inputed as a word, with letters in the incorrect
position indicated by a following `?`, and letters in the correct position with
a following `*`. For example, `a?rose*` indicates that the mystery words has
an `a` somewhere in it, an `e` in the fifth position, and does not contain
an `r`, `o`, or `s`.


## Wordle
Usage: ./wordle.py [word_length] [number_of_games]

Defaults to words of length 5

See `--help` for all options.

Reads from STDIN a guess, and outputs a `solver.py` compatible description of
the matching letters.

Prints out summary statistics when the games are completed.


## Advanced
`solver.py` can automatically play `wordle.py`. Pass `wordle.py` `--exec`
with the command line of a Wordle solver.

`solver.py` has multiple guessing strategies. Try passing `--strategy` with
the strategy ID, and compare how one strategy compares to the others.

## References
* `words_alpha.txt` taken from https://github.com/dwyl/english-words
* `common_english.txt` taken from https://www.ef.edu/english-resources/english-vocabulary/top-3000-words/
* `google-10000-english.txt` from https://github.com/first20hours/google-10000-english

All `5_letter_*` files are simply subsets of the the above listed files.
