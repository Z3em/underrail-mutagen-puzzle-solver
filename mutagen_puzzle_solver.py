#!/usr/bin/env python3.9
import sys
from threading import Thread
import itertools
import queue
import time
from functools import total_ordering
import logging
import argparse


class Compound:
    def __init__(self, name, rawAtoms):
        self.name = name
        self.positiveAtoms = []
        for a in rawAtoms:
            if a[0] != '-':
                self.positiveAtoms.append(a)

    def __add__(self, other):
        newAtoms = []
        newAtoms += self.positiveAtoms
        for p in other.positiveAtoms:
            AddPositiveAtom(newAtoms, p)
        if hasattr(other, "negativeAtoms"):
            for n in other.negativeAtoms:
                AddNegativeAtom(newAtoms, n)
        return(Compound(self.name + " " + other.name, newAtoms))

    def __iadd__(self, other):
        result = self+other
        return result

    def __str__(self):
        atomsString = ""
        for a in self.positiveAtoms:
            atomsString += (a + " ")
        return (self.name+": "+atomsString)

    def __eq__(self, other):
        return (self.positiveAtoms == other.positiveAtoms)

    def __ne__(self, other):
        return not (self == other)


class Reagent(Compound):
    def __init__(self, name, rawAtoms):
        super().__init__(name, rawAtoms)
        self.negativeAtoms = []
        for a in rawAtoms:
            if a[0] == '-':
                self.negativeAtoms.append(a[1:])

    def __str__(self):
        negativeAtomsString = ""
        for a in self.negativeAtoms:
            negativeAtomsString += ("-"+a+" ")
        return (super().__str__()+negativeAtomsString)


class Solution:
    def __init__(self):
        self.isFound = False

    def Save(self, exitus2):
        self.isFound = True
        self.compound = exitus2


class CheckCompoundThread(Thread):
    def __init__(self, reagents, exitus, reagentIndexQueue, maxIndexLength, solution):
        Thread.__init__(self)
        self.reagents = reagents
        self.exitus = exitus
        self.reagentIndexQueue = reagentIndexQueue
        self.maxIndexLength = maxIndexLength
        self.solution = solution

    def run(self):
        indexLength = 0
        while (not self.reagentIndexQueue.empty()):
            if self.solution.isFound:
                return
            indexSequence = self.reagentIndexQueue.get().sequence
            indexLength = len(indexSequence)
            compound = BuildCompound(self.reagents, indexSequence)
            logging.info("Checking %s", str(compound))
            if (compound == self.exitus):
                self.solution.Save(compound)
                logging.info("Success!")
                return
            else:
                logging.info("Fail")
            for i in range(len(self.reagents)):
                if (indexLength > 0):
                    # Dump the sequence if its length is over the specified limit
                    if (indexLength >= self.maxIndexLength):
                        continue
                    # Dump the new sequence if it contains a duplicate
                    if (i == indexSequence[indexLength - 1]):
                        continue
                newSequence = indexSequence.copy()
                newSequence.append(i)
                self.reagentIndexQueue.put(
                    PriorityReagentIndexSequence(indexLength, newSequence))
        return


@total_ordering
class PriorityReagentIndexSequence(object):
    def __init__(self, priority, sequence):
        self.priority = priority
        self.sequence = sequence

    def __eq__(self, other):
        return (self.priority == other.priority)

    def __gt__(self, other):
        return (self.priority > other.priority)


def AddPositiveAtom(atoms, positiveAtom):
    for a in atoms:
        if a == positiveAtom:
            return
    atoms.append(positiveAtom)
    return


def AddNegativeAtom(atoms, negativeAtom):
    for i in range(len(atoms)):
        if atoms[i] == negativeAtom:
            atoms.pop(i)
            return
    return


def GetExitusIndex(reagents):
    for i in range(len(reagents)):
        if (reagents[i].name.lower() == "exitus-1" or reagents[i].name.lower() == "exitus"):
            return i
    logging.error("Unable to find Exitus-1 reagent")
    sys.exit(100)


def GetExitus(reagents):
    return reagents.pop(GetExitusIndex(reagents))


def ParseFile(fileName):
    reagentsRaw = []
    try:
        file = open(fileName)
    except:
        logging.error("File \"%s\" not found", fileName)
        sys.exit()
    for line in file:
        if line[0] != '#':
            splitString = line.split()
            for r in reagentsRaw:
                if splitString[0] == r[0]:
                    logging.error(
                        "Reagent name %s is encountered in the list more than once", r[0])
                    sys.exit()
            reagentsRaw.append(splitString)
    file.close()
    reagents = []
    for r in reagentsRaw:
        reagent = Reagent(r[0], r[1:])
        reagents.append(reagent)
    return reagents


def BuildCompound(reagents, indexSequence):
    if (len(indexSequence) == 0):
        return Compound("", [])
    compound = reagents[indexSequence[0]]
    for i in range(len(indexSequence)-1):
        addition = reagents[indexSequence[i+1]]
        compound += addition
    return compound


def FindExitus2(reagents, exitus, threadNumber, maxIndexLength):
    solution = Solution()
    reagentIndexQueue = queue.PriorityQueue()
    reagentIndexQueue.put(PriorityReagentIndexSequence(0, []))
    threads = []
    for i in range(threadNumber):
        threads.append(CheckCompoundThread(
            reagents, exitus, reagentIndexQueue, maxIndexLength, solution))
    for t in threads:
        t.start()
        time.sleep(0.1)
    for t in threads:
        t.join()
    return solution


def PruneImpossibleReagents(reagents, exitus):
    negatedAtoms = []
    negatedAtoms.extend(exitus.positiveAtoms)
    pruningFinished = True
    # Add all negative atoms in reagents to the list of potentially negated atoms
    for r in reagents:
        for a in r.negativeAtoms:
            if not a in negatedAtoms:
                negatedAtoms.append(a)
    # Find all reagents that have atoms can't be negated and aren't present in Exitus
    reagentsToPrune = list()
    for i in range(len(reagents)):
        pruningNecessary = False
        for a in reagents[i].positiveAtoms:
            if not a in negatedAtoms:
                pruningNecessary = True
                break
        if pruningNecessary:
            pruningFinished = False
            reagentsToPrune.append(i)
    # Purge all found reagents
    for i in reversed(reagentsToPrune):
        reagents.pop(i)
    # If some reagents were pruned call the function recursively, otherwise return
    if pruningFinished:
        return
    else:
        PruneImpossibleReagents(reagents, exitus)
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated mutithreaded solver for mutagen puzzle")
    verbosity = parser.add_mutually_exclusive_group()
    parser.add_argument("file", type=str,
                        help="path to reagent list")
    verbosity.add_argument("-v", "--verbose", help="increase output verbosity",
                           action="store_true")
    verbosity.add_argument("-q", "--quiet", help="decrease output verbosity",
                           action="store_true")
    parser.add_argument("-t", "--threads", type=int, default=4,
                        help="specify the number of threads used (default 4)")
    parser.add_argument("-l", "--length", type=int, default=5,
                        help="specify the maximum number of reagents to be used in a compound (default 5)")
    args = parser.parse_args()

    if args.verbose:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING
    logging.basicConfig(format='%(levelname)s:%(message)s', level=loglevel)

    reagents = ParseFile(args.file)
    exitus = GetExitus(reagents)
    logging.info("Exitus-1 found")
    logging.info(exitus)
    PruneImpossibleReagents(reagents, exitus)

    logging.info("Checking compounds...")
    solution = FindExitus2(reagents, exitus, args.threads, args.length)

    if solution.isFound:
        if not args.quiet:
            print("Exitus-2 successfully constructed")
            print(exitus)
        print(solution.compound)
    else:
        if not args.quiet:
            print("Failed to construct Exitus-2")
    sys.exit(0)
