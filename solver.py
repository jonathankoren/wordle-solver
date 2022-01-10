#!/usr/bin/env python3

import sys
import re

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

    def guess(self, length, include_letters, exclude_letters, pattern, return_scores=False):
        print(include_letters, exclude_letters)
        candidates = list(self.unroll(self.search(length, include_letters, exclude_letters, pattern)))

        # build unigram, bigram, and position frequencies
        used_letters = include_letters.union(exclude_letters)
        letter_freqs = {}
        for word in candidates:
            for i in range(len(word)):
                for stop in range(2):
                    if i + stop + 1 <= len(word):
                        letter = word[i:i+stop+1]
                        if letter not in used_letters:
                            letter_freqs[letter] = letter_freqs.get(letter, 0) + 1
                        letter = letter + str(i)
                        if letter not in used_letters:
                            letter_freqs[letter] = letter_freqs.get(letter, 0) + 1

        # score the candidates
        scores = {}
        eligible_letters = self.single_letters - used_letters
        for word in candidates:
            scores[word] = 0
            scored_letters = set()
            for i in range(len(word)):
                for stop in range(2):
                    if i + stop + 1 <= len(word):
                        letter = word[i:i+stop+1]
                        if (letter[:1] in eligible_letters) or (letter[1:2] in eligible_letters):
                            if letter not in scored_letters:
                                scores[word] += letter_freqs[letter]
                                scored_letters.add(letter)
                                scores[word] += letter_freqs[f"{letter}{i}"]
                            else:
                                scores[word] -= letter_freqs[letter] / 2
                                scores[word] += letter_freqs[f"{letter}{i}"]

        scored = sorted(scores.items(), key=lambda p: p[1], reverse=True)
        if return_scores:
            return scored
        else:
            return list(map(lambda p: p[0], scored))

    def unroll(self, ids):
        return map(lambda id: self.words[id], ids)


def parse_line(line, contains, does_not_contain, bad_positions, good_positions):
    last_letter = None
    position = 0
    read_special = False
    for l in list(line):
        read_special = False
        if l == ' ':
            continue
        elif l == '?':
            position -= 1
            bad_positions[position].add(last_letter)
            contains.add(last_letter)
            read_special = True
        elif l == '*':
            position -= 1
            good_positions[position] = last_letter
            contains.add(last_letter)
            read_special = True
        elif last_letter is not None and last_letter not in '?*':
            does_not_contain.add(last_letter)

        position += 1
        last_letter = l
    if not read_special:
        does_not_contain.add(last_letter)

def make_regexp(bad_positions, good_positions):
    r = ''
    for i in range(5):
        if good_positions[i] is not None:
            r += good_positions[i]
        elif len(bad_positions[i]) > 0:
            r += '[^'+ ''.join(bad_positions[i]) + ']'
        else:
            r += '.'
    return re.compile(r)

def rescore(deep, common):
    new_deep = [None] * len(deep)
    deep_norm = sum(map(lambda p: p[1], deep))
    for i in range(len(deep)):
        new_deep[i] = (deep[i][0], deep[i][1] / deep_norm)
    new_common = [None] * len(common)
    common_norm = sum(map(lambda p: p[1], common))
    for i in range(len(common)):
        new_common[i] = (common[i][0], common[i][1] / common_norm)

    ret = []
    added = set()
    for p in sorted(new_common + new_deep, key=lambda p: p[1], reverse=True):
        if p[0] not in added:
            ret.append(p[0])
            added.add(p[0])
    return ret


##############################################################################
if __name__ == '__main__':
    word_length = 5
    if len(sys.argv) > 1:
        word_length = int(sys.argv[1])

    deep_dict_filename = '5_letter_words_alpha.txt'
    common_dict_filename = '5_letter_google-10000-english.txt'
    if word_length != 5:
        deep_dict_filename = 'words_alpha.txt'
        common_dict_filename = 'google-10000-english.txt'

    print('loading...')
    d = Dictionary(deep_dict_filename, word_length)
    common_d = Dictionary(common_dict_filename, word_length)
    print('Enter result of guess, with marking each letter with a * if it is in the correct')
    print('position, or ? if it is in the wrong position.')
    print('Example: "a?rose*" means the a is in the incorrect position. and e is in the')
    print('correct position.')
    print('Hit enter for initial guess.')
    print()
    contains = set()
    does_not_contain = set()
    bad_positions = [None] * word_length
    for i in range(word_length):
        bad_positions[i] = set()
    good_positions = [None] * word_length
    while True:
        sys.stdout.write("\n> ")
        try:
            parse_line(input(), contains, does_not_contain, bad_positions, good_positions)
            rescored = rescore(d.guess(word_length, contains, does_not_contain, make_regexp(bad_positions, good_positions), True), \
                    common_d.guess(word_length, contains, does_not_contain, make_regexp(bad_positions, good_positions), True))
            print(rescored[:10])
        except EOFError:
            break
