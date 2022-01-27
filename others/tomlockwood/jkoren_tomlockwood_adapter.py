#!/usr/bin/env python3

import argparse
import logging

from lib.games import FrequencyGame
from lib.games.prune import prune_wordlist
from wordle import Guess

def start_game(game_instance):
    super(FrequencyGame, game_instance).run()
    game_instance.targetlist = set(game_instance.orig_targetlist)

def guess(game_instance):
    game_instance.targetlist = prune_wordlist(game_instance.guesses, game_instance.targetlist)
    candidate, score = game_instance.get_candidate(game_instance.targetlist)

    guesses = get_all_candidates(game_instance, game_instance.targetlist)
    logger.debug('candidates %s ... %d', guesses[:10], len(guesses))
    logger.debug('guessing %s', candidate)
    return candidate

def get_all_candidates(game_instance, possible_guesses):
    indexes = game_instance.letter_frequency_in_position(game_instance.targetlist)
    scores = {}

    for word in possible_guesses:
        word_score = 0
        for idx, letter in enumerate(word):
            word_score += indexes[idx + 1][letter]
        scores[word] = word_score

    return sorted(scores.items(), key=lambda p: p[1], reverse=True)

def convert_feedback_to_guess(guessed_word, line):
    pattern = []
    last_letter = None
    read_special = False
    for l in list(line):
        read_special = False
        if l == ' ':
            continue
        elif l == '?':
            pattern.append(1)
            read_special = True
        elif l == '*':
            pattern.append(2)
            read_special = True
        elif last_letter is not None and last_letter not in '?*':
            pattern.append(0)
        last_letter = l
    if not read_special and last_letter is not None:
        pattern.append(0)
    return Guess(guessed_word, pattern)

def update(game_instance, guessed_word, feedback):
    game_instance.guesses.append(convert_feedback_to_guess(guessed_word, feedback))


##############################################################################
logging.basicConfig()
logger = logging.getLogger('jkoren_tomlockwood_adapter.py')

parser = argparse.ArgumentParser(description="Tom Lockwood's solver")
parser.add_argument('--dictionaries', type=str, default='5_letter_wordle_targets.txt', help='CSV of dictionary files to load')
parser.add_argument('--expanded_list_guesses', type=int, default=0)
parser.add_argument('--debug', action='store_true', default=False)
parser.add_argument('--verbose', action='store_true', default=False)
args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.INFO)
if args.debug:
    logger.setLevel(logging.DEBUG)

dictionaries = []
for filename in args.dictionaries.split(','):
    filename = filename.strip()
    dictionaries.append(set())
    with open(filename, 'r') as infile:
        for word in infile.read().split("\n"):
            if len(word) > 0:
                dictionaries[-1].add(word)

game_instance = FrequencyGame(expanded_list_guesses=args.expanded_list_guesses)

if args.expanded_list_guesses > 0:
    game_instance.orig_targetlist = dictionaries[0]
    if len(dictionaries) > 1:
        game_instance.orig_guesslist = dictionaries[1]
    else:
        game_instance.orig_guesslist = game_instance.orig_targetlist
else:
    dd = None
    for d in dictionaries:
        if dd is None:
            dd = d
        else:
            dd = dd.union(d)
    game_instance.orig_targetlist = dd
    game_instance.orig_guesslist = game_instance.orig_targetlist

start_game(game_instance)
while True:
    guessed_word = guess(game_instance)
    if len(guessed_word) == 0:
        print('OUT OF GUESSES')
    else:
        print(guessed_word)
    feedback = input() # feedback is a jkoren wordle string or 'YOU LOSE' or 'YOU WIN'
    update(game_instance, guessed_word, feedback)
    if feedback == 'CORRECT' or feedback == 'YOU LOSE':
        start_game(game_instance)
