#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Rico Sennrich

"""Use byte pair encoding (BPE) to learn a variable-length encoding of the vocabulary in a text.
This script learns BPE jointly on a concatenation of a list of texts (typically the source and target side of a parallel corpus,
applies the learned operation to each and (optionally) returns the resulting vocabulary of each text.
The vocabulary can be used in apply_bpe.py to avoid producing symbols that are rare or OOV in a training text.

Reference:
Rico Sennrich, Barry Haddow and Alexandra Birch (2016). Neural Machine Translation of Rare Words with Subword Units.
Proceedings of the 54th Annual Meeting of the Association for Computational Linguistics (ACL 2016). Berlin, Germany.
"""

from __future__ import unicode_literals

import sys
import os
import inspect
import codecs
import argparse
import tempfile
import warnings
from collections import Counter

#hack to get imports working if running this as a script, or within a package
if __name__ == '__main__':
    import learn_bpe
    import apply_bpe
else:
    from . import learn_bpe
    from . import apply_bpe

import json

# hack for python2/3 compatibility
from io import open
argparse.open = open

def create_parser(subparsers=None):

    if subparsers:
        parser = subparsers.add_parser('learn-joint-bpe-and-vocab',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="learn BPE-based word segmentation")
    else:
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="learn BPE-based word segmentation")

    parser.add_argument(
        '--input', '-i', type=argparse.FileType('r'), required=True, nargs = '+',
        metavar='PATH',
        help="Input text (multiple allowed).")

    parser.add_argument(
        '--bpe_output', '-bo', type=argparse.FileType('w'), required=True,
        metavar='PATH',
        help="Output file for BPE merge file.")

    parser.add_argument(
        '--vocab_output', '-vo', type=argparse.FileType('w'), required=True,
        metavar='PATH',
        help="Output file for vocab.json file.")

    parser.add_argument(
        '--symbols', '-s', type=int, default=10000,
        help="Create this many new symbols (each representing a character n-gram) (default: %(default)s))")
    parser.add_argument(
        '--separator', type=str, default='', metavar='STR',
        help="Separator between non-final subword units (default: '%(default)s'))")

    parser.add_argument(
        '--min-frequency', type=int, default=2, metavar='FREQ',
        help='Stop if no symbol pair has frequency >= FREQ (default: %(default)s))')
    parser.add_argument(
        '--total-symbols', '-t', action="store_true",
        help="subtract number of characters from the symbols to be generated (so that '--symbols' becomes an estimate for the total number of symbols needed to encode text).")
    parser.add_argument(
        '--verbose', '-v', action="store_true",
        help="verbose mode.")

    return parser

def learn_joint_bpe_and_vocab(args):

    # read/write files as UTF-8
    args.input = [codecs.open(f.name, encoding='UTF-8') for f in args.input]

    # get combined vocabulary of all input texts
    full_vocab = Counter()
    for f in args.input:
        full_vocab += learn_bpe.get_vocabulary(f)
        f.seek(0)

    vocab_list = ['{0} {1}'.format(key, freq) for (key, freq) in full_vocab.items()]

    # learn BPE on combined vocabulary
    with codecs.open(args.bpe_output.name, 'w', encoding='UTF-8') as output:
        learn_bpe.learn_bpe(vocab_list, output, args.symbols, args.min_frequency, args.verbose, is_dict=True, total_symbols=args.total_symbols)

    with codecs.open(args.bpe_output.name, encoding='UTF-8') as codes:
        bpe = apply_bpe.BPE(codes, separator=args.separator)

    # apply BPE to each training corpus and get vocabulary
    for train_file in args.input:

        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()

        tmpout = codecs.open(tmp.name, 'w', encoding='UTF-8')

        train_file.seek(0)
        for line in train_file:
            tmpout.write(bpe.segment(line).strip())
            tmpout.write('\n')

        tmpout.close()
        tmpin = codecs.open(tmp.name, encoding='UTF-8')

        vocab = learn_bpe.get_vocabulary(tmpin)
        tmpin.close()
        os.remove(tmp.name)

        output_dict = {}
        for i, (key, freq) in enumerate(sorted(vocab.items(), key=lambda x: x[1], reverse=True)):
        #    entry = key.replace('@@', ' ')
            output_dict[key] = i
        print(output_dict)

        with open(args.vocab_output.name, 'w') as file:
            json.dump(output_dict, file)


if __name__ == '__main__':

    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    newdir = os.path.join(currentdir, 'subword_nmt')
    if os.path.isdir(newdir):
        warnings.simplefilter('default')
        warnings.warn(
            "this script's location has moved to {0}. This symbolic link will be removed in a future version. Please point to the new location, or install the package and use the command 'subword-nmt'".format(newdir),
            DeprecationWarning
        )

    # python 2/3 compatibility
    if sys.version_info < (3, 0):
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
        sys.stdin = codecs.getreader('UTF-8')(sys.stdin)
    else:
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr.buffer)
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout.buffer)
        sys.stdin = codecs.getreader('UTF-8')(sys.stdin.buffer)

    parser = create_parser()
    args = parser.parse_args()

    if sys.version_info < (3, 0):
        args.separator = args.separator.decode('UTF-8')

    learn_joint_bpe_and_vocab(args)
