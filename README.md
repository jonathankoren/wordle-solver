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

## Addendum
Laurent Poirrier has written the most comprehenisve article on Wordle solvers.
https://www.poirrier.ca/notes/wordle-optimal/?utm_source=pocket_mylist
Using only the 2315 target dictionary (5_letter_wordle_targets.txt), the
optimal solution uses 3.4212 guesses on average, with a maximum of 5 guesses,
and a 100% success rate.  In hard mode, it is 3.5085 guesses on average, 6 at 
worst, and a 100% success rate.

If we uses the full 12972 word dictionary 
(5_letter_wordle_solver_guess_dict.txt  and 5_letter_wordle_targets.txt), 
then it can be solved with 100% of the time in at most 6 guesses.

"Hard Mode" forces the player to use words that contain every previously
guessed correct letter. 

An example of an optimal bot that uses both player dictionaries,
but evaluated only on the target is list is Jonathan Olson's bot.
https://jonathanolson.net/wordle-solver/ . Its statistics are:

Wins 2315 Losses: 0 Surrenders: 0 Played: 1 WinPct 100.000 %
Number of attempts to win: mean: 3.4212 stddev: ????
Score (lower better) ?????
Winning Histogram
 1 |   0.00 % |  (0)
 2 |   0.00 % |  (78)
 3 |   0.00 % |  (1223)
 4 |   0.00 % |  (975)
 5 |   0.00 % |  (39)
 6 |   0.00 % |  (0)

Interestingly, its first guess is `salet`, a word *not* in the
target dictionary. An example play for `cigar` is:

sa?let		2315 possible targets, 3.594 average guesses
br?ond		102 possible target words, 3.736 average guesses
c*ha?i?r*	8 possible target words, 4 average guesses
c*i*g*a*r*	CORRECT

