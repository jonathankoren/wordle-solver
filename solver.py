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
        self.filename = filename
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

    def _single_guess_heuristics(self, d, **kwargs):
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
        USE_MULTIPATH = kwargs.get('multipath', False)
        scores = {}
        tmp_contains = set(self.contains)
        candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp()))
        logger.debug('_sgge initial canidates: %d', len(candidate_ids))
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
            logger.debug('_sgge MAX ENTROPY letter %s entrop %f', max_entropy_letter, max_entropy)
            if max_entropy_letter is not None:
                tmp_contains.add(max_entropy_letter)
                candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp()))
            else:
                break

        for candidate_id in candidate_ids:
            scores[d.words[candidate_id]] = 1
        return sorted(scores.items(), key=lambda p: p[1], reverse=True)

    def _single_guess_greedy_pointwise_mutual_info(self, d, **kwargs):
        scores = {}
        tmp_contains = set(self.contains)
        candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp()))
        logger.debug('_sggpmi initial canidates: %d', len(candidate_ids))
        while (len(candidate_ids) > 1) and len(tmp_contains) < self.word_length:
            max_pmi = None
            max_pmi_letter = None
            for letter in d.single_letters - tmp_contains.union(self.does_not_contain):
                pmi = None
                if len(candidate_ids) == len(d.words):
                    # initial guess with the most frequent letter
                    pmi = len(d.letter_index[letter])
                    logger.debug('_sggpmi %s, pmi faked by frequency as %f', letter, pmi)
                else:
                    p_letter_in_candidates = 1 - (len(candidate_ids - d.letter_index[letter]) / len(candidate_ids))
                    p_letter = len(d.letter_index[letter]) / len(d.words)
                    if p_letter_in_candidates == 0:
                        continue

                    pmi = math.log2(p_letter_in_candidates / p_letter)
                    logger.debug('_sggpmi %s, p_letter_in_candidates %f  p_letter %f  %f pmi %f', letter, p_letter_in_candidates, p_letter, p_letter_in_candidates / p_letter, pmi)
                if max_pmi_letter is None or pmi > max_pmi:
                    max_pmi = pmi
                    max_pmi_letter = letter
            logger.debug('_sggpmi MAX PMI letter %s pmi %f', max_pmi_letter, max_pmi)
            if max_pmi_letter is not None:
                tmp_contains.add(max_pmi_letter)
                candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp()))
            else:
                break

        for candidate_id in candidate_ids:
            scores[d.words[candidate_id]] = 1

        return sorted(scores.items(), key=lambda p: p[1], reverse=True)

    def _single_guess_greedy_most_cond_prob(self, d, **kwargs):
        USE_POS_FREQ = kwargs.get('pos_freq', True)
        USE_MULTIPATH = kwargs.get('multipath', False)
        scores = {}

        tmp_contains = set(self.contains)
        candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp()))
        last_max_freq = None
        overrides = None
        if USE_POS_FREQ:
            overrides = [None] * self.word_length
        while (len(candidate_ids) > 1) and len(tmp_contains) < self.word_length:
            letter_freqs = self._letter_freqs(list(d.unroll(candidate_ids)), 1, USE_POS_FREQ)
            eligible_letters = d.single_letters - tmp_contains.union(self.does_not_contain)
            max_freq = None
            max_freq_letter = None
            max_freq_position = None
            logger.debug('_sggmcp eligible_letters %s  overrides %s', sorted(eligible_letters), str(overrides))
            for letter in eligible_letters:
                if USE_POS_FREQ:
                    eligible_positions = []
                    for i in range(self.word_length):
                        if ((self.good_positions[i] is None) or (letter not in self.bad_positions[i])) or overrides[i] is None:
                            eligible_positions.append(i)
                    for position in eligible_positions:
                        key = f'{letter}{position}'
                        if max_freq is None or letter_freqs.get(key, 0) > max_freq:
                            max_freq = letter_freqs.get(key, 0)
                            max_freq_letter = letter
                            max_freq_position = position
                else:
                    if max_freq is None or letter_freqs.get(letter, 0) > max_freq:
                        max_freq = letter_freqs.get(letter, 0)
                        max_freq_letter = letter
                        last_max_freq = max_freq

            logger.debug('_sggmcp max freq letter %s  position %s  freq %d  regexp %s', max_freq_letter, str(max_freq_position), max_freq, self._make_regexp(overrides).pattern)
            tmp_contains.add(max_freq_letter)
            if USE_POS_FREQ:
                overrides[max_freq_position] = max_freq_letter
            candidate_ids = set(d.search(self.word_length, tmp_contains, self.does_not_contain, self._make_regexp(overrides)))

        logger.debug('_sggmcp overrides %s', str(overrides))
        for candidate_id in candidate_ids:
            if last_max_freq is None:
                scores[d.words[candidate_id]] = 1
            else:
                scores[d.words[candidate_id]] = last_max_freq

        return sorted(scores.items(), key=lambda p: p[1], reverse=True)

    def guess(self, return_scores=False, **kwargs):
        logger.debug('STATE: wl %d, contains %s, dnc %s, regexp %s', self.word_length, self.contains, self.does_not_contain, self._make_regexp().pattern)
        GUESS_LAMBDA = kwargs.get('glam', lambda d: self._single_guess_heuristics(d))
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
            else:
                logger.debug("guesses %s ...", guesses[:10])

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

    def _make_regexp(self, overrides=None):
        r = ''
        for i in range(self.word_length):
            if overrides is not None and overrides[i] is not None:
                r += overrides[i]
            elif self.good_positions[i] is not None:
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
        print('loading...', list(map(lambda d: d.filename, dictionaries)))
    game_state = GameState(args.word_length, dictionaries)

    strategies = [
        # 0
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=2, pos_freq=True)),    # 0.log:Number of attempts to win: mean: 4.430554 stddev: 63.349
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=2, pos_freq=False)),   # 1.log:Number of attempts to win: mean: 4.422290 stddev: 63.482
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=1, pos_freq=True)),    # 2.log:Number of attempts to win: mean: 4.414069 stddev: 63.569
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=1, pos_freq=False)),   # 3.log:Number of attempts to win: mean: 4.432977 stddev: 63.521
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=2, pos_freq=True)),   # 4.log:Number of attempts to win: mean: 4.353128 stddev: 64.394
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=2, pos_freq=False)),  # 5.log:Number of attempts to win: mean: 4.366832 stddev: 64.002
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=1, pos_freq=True)),   # 6.log:Number of attempts to win: mean: 4.335903 stddev: 64.753
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_heuristics(d, ngrams=1, pos_freq=False)),  # 7.log:Number of attempts to win: mean: 4.376372 stddev: 64.488

        # 8
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_greedy_entropy(d)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_greedy_entropy(d)),

        # 10
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_greedy_pointwise_mutual_info(d)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_greedy_pointwise_mutual_info(d)),

        # 12
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_greedy_most_cond_prob(d, pos_freq=True)),
        lambda: game_state.guess(normalize=True, glam=lambda d: game_state._single_guess_greedy_most_cond_prob(d, pos_freq=False)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_greedy_most_cond_prob(d, pos_freq=True)),
        lambda: game_state.guess(normalize=False, glam=lambda d: game_state._single_guess_greedy_most_cond_prob(d, pos_freq=False))
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
        logger.debug('RECVD.top <%s>', line)
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
                sys.stdout.write("\n> ")
                line = input()
                logger.debug('RECVD.notgame <%s>', line)
            except EOFError:
                sys.exit(0)
        else:
            accepted = False
            for (cnt, guess) in enumerate(rescored):
                logger.debug('SENDING <%s>', guess)
                print(guess)
                try:
                    line = input()
                except EOFError:
                    sys.exit(2)
                if (line == 'INVALID WORD'):
                    logger.debug('RECVD.invalid %d %d <%s>', cnt + 1, len(rescored), line)
                else:
                    accepted = True
                    break
            if not accepted:
                logger.debug('out of guesses? %d', len(rescored))
                print('OUT OF GUESSES')
                game_state.reset()
                line = ''
