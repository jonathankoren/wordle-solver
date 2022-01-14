#!/usr/bin/env python3

import argparse
import math
import sys
import re

import logging
logging.basicConfig()
logger = logging.getLogger('solver.py')

class Dictionary:
    def __init__(self, filename, required_word_length=None):
        self.length_index = {}
        self.letter_index = {}
        self.single_letters = set()
        self.words = []
        word_id = 0
        with open(filename, 'r') as infile:
            for word in infile.read().split("\n"):
                # index by length
                word_length = len(word)
                if required_word_length is not None and word_length != required_word_length:
                    continue
                self.words.append(word)
                if word_length not in self.length_index:
                    self.length_index[word_length] = set()
                self.length_index[word_length].add(word_id)

                # index by letter, and repeated letters
                last_letter = None
                letter_repeats = 1
                for letter in sorted(list(word)):
                    if letter == last_letter:
                        letter_repeats += 1
                    else:
                        self.single_letters.add(letter)
                        letter_repeats = 1
                    multi = letter * letter_repeats
                    if multi not in self.letter_index:
                        self.letter_index[multi] = set()
                    self.letter_index[multi].add(word_id)
                    last_letter = letter
                word_id += 1

    def search(self, length, include_letters, exclude_letters, pattern):
        candidates = self.length_index[length]
        keys = {}
        for letter in include_letters:
            keys[letter] = keys.get(letter, 0) + 1
        for (letter, repeats) in keys.items():
            candidates = candidates.intersection(self.letter_index[letter * repeats])
        for letter in exclude_letters:
            candidates = candidates - self.letter_index[letter]
        return filter(lambda w: pattern.match(self.words[w]), candidates)

    def unroll(self, ids):
        return map(lambda id: self.words[id], ids)


class GameState:
    def __init__(self, word_length, dictionaries):
        self.word_length = word_length
        self.dictionaries = dictionaries
        self.reset()

    def reset(self):
        self.contains = set()
        self.does_not_contain = set()
        self.bad_positions = [None] * self.word_length
        for i in range(self.word_length):
            self.bad_positions[i] = set()
        self.good_positions = [None] * self.word_length

    def parse_line(self, line):
        last_letter = None
        position = 0
        read_special = False
        for l in list(line):
            read_special = False
            if l == ' ':
                continue
            elif l == '?':
                position -= 1
                self.bad_positions[position].add(last_letter)
                self.contains.add(last_letter)
                read_special = True
            elif l == '*':
                position -= 1
                self.good_positions[position] = last_letter
                self.contains.add(last_letter)
                read_special = True
            elif last_letter is not None and last_letter not in '?*':
                if last_letter not in self.contains:
                    self.does_not_contain.add(last_letter)

            position += 1
            last_letter = l
        if not read_special and last_letter is not None and last_letter not in self.contains:
            self.does_not_contain.add(last_letter)

    def _letter_freqs(self, candidates, NGRAM_LENGTH, USE_POS_FREQ):
        # build unigram, bigram, and position frequencies
        used_letters = self.contains.union(self.does_not_contain)
        letter_freqs = {}
        for word in candidates:
            for i in range(len(word)):
                for stop in range(NGRAM_LENGTH):
                    if i + stop + 1 <= len(word):
                        letter = word[i:i+stop+1]
                        if letter not in used_letters:
                            letter_freqs[letter] = letter_freqs.get(letter, 0) + 1
                        if USE_POS_FREQ:
                            letter = letter + str(i)
                            if letter not in used_letters:
                                letter_freqs[letter] = letter_freqs.get(letter, 0) + 1
        return letter_freqs

    def _single_guess(self, d, **kwargs):
        NGRAM_LENGTH = kwargs.get('ngrams', 2)
        USE_POS_FREQ = kwargs.get('pos_freq', True)

        candidates = list(d.unroll(d.search(self.word_length, self.contains, self.does_not_contain, self._make_regexp())))

        letter_freqs = self._letter_freqs(candidates, NGRAM_LENGTH, USE_POS_FREQ)

        # score the candidates
        scores = {}
        eligible_letters = d.single_letters - self.contains.union(self.does_not_contain)
        for word in candidates:
            scores[word] = 0
            scored_letters = set()
            for i in range(len(word)):
                for stop in range(NGRAM_LENGTH):
                    if i + stop + 1 <= len(word):
                        letter = word[i:i+stop+1]
                        if (letter[:1] in eligible_letters) or (letter[1:2] in eligible_letters):
                            if letter not in scored_letters:
                                scores[word] += letter_freqs[letter]
                                scored_letters.add(letter)
                                if USE_POS_FREQ:
                                    scores[word] += letter_freqs[f"{letter}{i}"]
                            else:
                                scores[word] -= letter_freqs[letter] / 2
                                if USE_POS_FREQ:
                                    scores[word] += letter_freqs[f"{letter}{i}"]

        return sorted(scores.items(), key=lambda p: p[1], reverse=True)

    def _single_guess_greedy_entropy(self, d, **kwargs):
        scores = {}
        tmp_contains = set(self.contains)
        candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp()))
        logger.debug('_sgre initial canidates: %d', len(candidate_ids))
        while (len(candidate_ids) > 1) and len(tmp_contains) < self.word_length:
            max_entropy = 0
            max_entropy_letter = None
            for letter in d.single_letters - tmp_contains.union(self.does_not_contain):
                p = len(candidate_ids - d.letter_index[letter]) / len(candidate_ids)
                entropy = 0
                if 0 < p and p < 1:
                    entropy = -(p * math.log2(p)) - ((1 - p) * math.log2(1 - p))
                if max_entropy_letter is None or max_entropy < entropy:
                    max_entropy_letter = letter
                    max_entropy = entropy
            logger.debug('_sgre MAX ENTROPY letter %s entrop %f', max_entropy_letter, max_entropy)
            tmp_contains.add(max_entropy_letter)
            candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp()))

        for candidate_id in candidate_ids:
            scores[d.words[candidate_id]] = 1

        return sorted(scores.items(), key=lambda p: p[1], reverse=True)


    def guess(self, return_scores=False, **kwargs):
        logger.debug('STATE: wl %d, contains %s, dnc %s, regexp %s', self.word_length, self.contains, self.does_not_contain, self._make_regexp().pattern)
        GUESS_LAMBDA = kwargs.get('glam', lambda d: self._single_guess(d))
        NORMALIZE_SCORES = kwargs.get('normalize', True)
        new_scores = {}
        for d in self.dictionaries:
            guesses = GUESS_LAMBDA(d)
            norm = sum(map(lambda p: p[1], guesses))
            if norm == 0:
                norm = 1
            logger.debug("num guesss %d  norm %f", len(guesses), norm )
            if len(guesses) < 10:
                logger.debug("guesses %s", guesses)

            for (guess, score) in guesses:
                if NORMALIZE_SCORES:
                    new_scores[guess] = max(new_scores.get(guess, float('-inf')), score / norm)
                else:
                    new_scores[guess] = score

        scored = sorted(new_scores.items(), key=lambda p: p[1], reverse=True)
        if return_scores:
            return scored
        else:
            return list(map(lambda p: p[0], scored))

    def _make_regexp(self):
        r = ''
        for i in range(self.word_length):
            if self.good_positions[i] is not None:
                r += self.good_positions[i]
            elif len(self.bad_positions[i]) > 0:
                r += '[^'+ ''.join(self.bad_positions[i]) + ']'
            else:
                r += '.'
        return re.compile(r)

##############################################################################
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wordle solver')
    parser.add_argument('word_length', type=int, default=5, nargs='?', help='length of word')
    parser.add_argument('--game', action='store_true', default=False)
    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--strategy', type=int, default=0, help='ID of guessing strategy')
    parser.add_argument('--dictionaries', type=str, default='words_alpha.txt,google-10000-english.txt', help='CSV of dictionary files to load')
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)


    dictionaries = []
    for filename in args.dictionaries.split(','):
        filename = filename.strip()
        if args.word_length == 5:
            filename = '5_letter_' + filename
        dictionaries.append(Dictionary(filename, args.word_length))

    if (not args.game):
        print('loading...')
    game_state = GameState(args.word_length, dictionaries)

    strategies = [
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess(d, ngrams=2, pos_freq=True)),
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess(d, ngrams=2, pos_freq=False)),
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess(d, ngrams=1, pos_freq=True)),
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess(d, ngrams=1, pos_freq=False)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess(d, ngrams=2, pos_freq=True)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess(d, ngrams=2, pos_freq=False)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess(d, ngrams=1, pos_freq=True)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess(d, ngrams=1, pos_freq=False)),
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_greedy_entropy(d)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_greedy_entropy(d)),
    ]
    if args.strategy >= len(strategies):
        args.strategy = 0

    if (not args.game):
        print('Using strategy', args.strategy)
        print()
        print('Enter result of guess, with marking each letter with a * if it is in the correct')
        print('position, or ? if it is in the wrong position.')
        print('Example: "a?rose*" means the a is in the incorrect position. and e is in the')
        print('correct position.')
        print('Hit enter for initial guess.')
        print()
    else:
        logger.info('Using strategy %d', args.strategy)

    line = ''
    while True:
        logger.debug('RECVD <%s>', line)
        if line == 'CORRECT' or line == 'YOU LOSE':
            if line == 'YOU LOSE':
                logger.info('LOST c: %s dnc: %s regep %s', game_state.contains, game_state.does_not_contain, game_state._make_regexp().pattern)

            game_state.reset()
            line = ''

        game_state.parse_line(line)
        rescored = strategies[args.strategy]()
        if len(rescored) == 0:
            if (not args.game):
                print('OUT OF GUESSES')
                game_state.reset()
                line = ''

        if (not args.game):
            print(rescored[:10])
            try:
                line = input()
            except EOFError:
                sys.exit(0)
        else:
            for guess in rescored:
                logger.debug('SENDING <%s>', guess)
                print(guess)
                try:
                    line = input()
                except EOFError:
                    sys.exit(2)
                if (line != 'INVALID WORD'):
                    break

        if (not args.game):
            sys.stdout.write("\n> ")
