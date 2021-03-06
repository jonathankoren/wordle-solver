#!/usr/bin/env python3

import argparse
import logging
import math
import os.path
import random
import subprocess
import sys
import time

from solver import Dictionary

def evaluate(guess, target):
    target_letters = count_letters(target)
    guess_letters = count_letters(guess)
    codes = [''] * len(target)
    for (i, c) in enumerate(guess):
        if target[i] == c:
            codes[i] = '*'
            target_letters[c] -= 1
            guess_letters[c] -= 1
    for (i, c) in enumerate(guess):
        if (target[i] != c) and (guess_letters.get(c, 0) > 0) and (target_letters.get(c, 0) > 0):
            codes[i] = '?'
            target_letters[c] -= 1
            guess_letters[c] -= 1
    resp = ''
    for (i, c) in enumerate(guess):
        resp += c + codes[i]
    return resp

def count_letters(word):
    letters = {}
    for c in word:
        letters[c] = letters.get(c, 0) + 1
    return letters

class Statistics:
    def __init__(self):
        self.wins = 0
        self.losses = 0
        self.histogram = {}
        self.gave_up = 0

    def win(self, attempts):
        self.wins += 1
        self.histogram[attempts] = self.histogram.get(attempts, 0) + 1

    def lose(self):
        self.losses += 1

    def gaveup(self):
        self.gave_up += 1

    def played(self):
        return self.wins + self.losses + self.gave_up

    def mean(self):
        numerator = sum(map(lambda p: p[0] * p[1], self.histogram.items()))
        return numerator / float(self.wins)

    def stddev(self):
        mean = self.mean()
        return math.sqrt(sum(list(map(lambda p: ((p[0] - mean) ** 2) * p[1], self.histogram.items()))) / float(self.wins))

    def score(self):
        return sum(map(lambda p: p[0] * p[1], self.histogram.items())) + (7 * (self.losses + self.gave_up))

    def display_histogram(self, BAR_LENGTH=50):
        end = 0
        if len(self.histogram) > 0:
            end = max(self.histogram.keys())
        ret = ''
        for i in range(1, end + 1):
            fraction = self.histogram.get(i, 0) / float(self.wins)
            ret += f'{i:-2} | {fraction * 100:-6.02f} % | '
            for j in range(int(round(fraction * BAR_LENGTH, 0))):
                ret += '#'
            ret += f" ({self.histogram.get(i, 0)})\n"
        ret += "\n"
        return ret

def choose_target_word(d, num_games, exhaust):
    game_id = 0
    if exhaust:
        while (game_id < len(d.words)):
            yield d.words[game_id]
            game_id += 1
    else:
        while (game_id < num_games):
            word = random.choice(d.words)
            yield word
            game_id += 1

def safe_write(out_pipe, msg):
    if out_pipe != sys.stdout:
        msg = bytes(msg, 'utf-8')
    out_pipe.write(msg)
    out_pipe.flush()

def safe_readline(p):
    guess = in_pipe.readline()
    if type(guess) == bytes:
        guess = guess.decode('utf-8')
    return guess.strip()

##############################################################################


parser = argparse.ArgumentParser(description='Wordle')
parser.add_argument('num_games', type=int, default=1, nargs='?', help='number_of_games')
parser.add_argument('word_length', type=int, default=5, nargs='?', help='length of word')
parser.add_argument('--seed', type=int, default=int(time.time()), help='random number seed')
parser.add_argument('--exhaust', action='store_true', default=False, help='Systematically play with every word in the dictionary')
parser.add_argument('--exec', type=str, default=None, help='Program to run to play Wordle')
parser.add_argument('--debug', action='store_true', default=False)
parser.add_argument('--verbose', action='store_true', default=False)
parser.add_argument('--dictionary_dir', type=str, default='./dicts', help='Directory containing dictionaries')
parser.add_argument('--dictionary', type=str, default='5_letter_wordle_targets.txt', help='Alternate dictionary')
args = parser.parse_args()
word_length = args.word_length
seed = args.seed

logging.basicConfig()
logger = logging.getLogger('wordle.py')
if args.verbose:
    logger.setLevel(logging.INFO)
if args.debug:
    logger.setLevel(logging.DEBUG)

dict_filename = os.path.join(args.dictionary_dir, args.dictionary)

print(f'loading {dict_filename}...')
d = Dictionary(dict_filename, word_length)
valid_words = set(d.words)
random.seed(seed)

in_pipe = sys.stdin
out_pipe = sys.stdout
p = None
if args.exec is not None:
    spargs = list(filter(lambda x: len(x) > 0, args.exec.split(' ')))
    p = subprocess.Popen(spargs, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    in_pipe = p.stdout
    out_pipe = p.stdin

stats = Statistics()
max_attempts = word_length + 1
word_generator = choose_target_word(d, args.num_games, args.exhaust)
print('running...')
game_id = -1
while True:
    game_id += 1
    target = None
    try:
        target = next(word_generator)
    except StopIteration:
        break
    logger.info("New game (%d / %d). target: %s", game_id, args.num_games, target)
    correct = False
    gave_up = False
    attempt = 1
    while attempt <= max_attempts:
        guess = None
        target_letters = count_letters(target)
        try:
            if out_pipe == sys.stdout:
                safe_write(out_pipe, '> ')
            guess = safe_readline(in_pipe)
            logger.debug('Attempt %d received %s', attempt, str(guess))
        except EOFError:
            break;
        if guess == '':
            break
        guessed_letters = count_letters(guess)
        if guess == 'OUT OF GUESSES':
            logger.info('Player gave up')
            stats.gaveup()
            gave_up = True
            break
        elif guess not in valid_words or len(guess) != len(target):
            logger.info('invalid word %s', guess)
            safe_write(out_pipe, "INVALID WORD\n")
            attempt -= 1    # redo the attempt
        elif guess == target:
            safe_write(out_pipe, "CORRECT\n")
            if out_pipe == sys.stdout:
                safe_write(out_pipe, "\n")
            correct = True
            logger.info('Player won. %s Attempts %d', target, attempt)
            stats.win(attempt)
            break
        else:
            resp = evaluate(guess, target)
            if attempt != max_attempts:
                logger.debug('sending %s , attempt %d', resp, attempt)
                if out_pipe == sys.stdout:
                    print(f"{resp}\n")
                else:
                    safe_write(out_pipe, f"{resp}\n")
        attempt += 1

    if not correct and not gave_up:
        safe_write(out_pipe, f"YOU LOSE\n")
        if out_pipe == sys.stdout:
            safe_write(out_pipe, f"The word was {target}\n\n")
        stats.lose()
        logger.info('Player lost. %s != %s Attempts %d', target, guess, attempt)

if p is not None:
    p.stdin.close()
    p.terminate()

print()
print(f'Player: {args.exec}')
print(f'Dictionary: {dict_filename}  Word Length: {args.word_length}  Seed: {seed}')
if args.exhaust:
    print('Exhaust dictionary')
print(f'Wins {stats.wins} Losses: {stats.losses} Surrenders: {stats.gave_up} Played: {stats.played()} WinPct {(stats.wins / stats.played() * 100):.3f} %')
print(f'Number of attempts to win: mean: {stats.mean():3f} stddev: {stats.stddev():.3f}')
print(f'Score (lower better) {stats.score()}')
print('Winning Histogram')
print(stats.display_histogram())
