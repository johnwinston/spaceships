import sys
import numpy as np
from subprocess import PIPE, Popen
from random import randrange, sample
import os

from . import config

class AUTO_NTZFIND:
    def __init__(self, iterations, period):
        self.golly_file_path = os.path.join(config.GOLLY_BASE, "ntzfind_patterns/")
        self.period_file_path = self.golly_file_path + str(period) + "/"
        if not os.path.exists(self.period_file_path):
            os.makedirs(self.period_file_path)
        self.iterations = iterations
        self.period = "p" + str(period)
        self.numbers = list(np.linspace(1,7,7,dtype=int))
        self.letters =\
          [
            ['c', 'e'],
            ['c', 'e', 'k', 'a', 'i', 'n'],
            ['c', 'e', 'k', 'a', 'i', 'n', 'y', 'q', 'j', 'r'],
            ['c', 'e', 'k', 'a', 'i', 'n', 'y', 'q', 'j', 'r', 't', 'w', 'z'],
            ['c', 'e', 'k', 'a', 'i', 'n', 'y', 'q', 'j', 'r'],
            ['c', 'e', 'k', 'a', 'i', 'n'],
            ['c', 'e']
          ]

    def generate_sub_rule(self):
        rule = ""
        for num in sample(self.numbers, randrange(1,8)):
            rule += str(num)
            number_of_letters = randrange(1, len(self.letters[num-1]))
            for letter in sample(self.letters[num-1], number_of_letters):
                rule += letter
        return rule

    def generate_rule(self):
        rule = "b" + self.generate_sub_rule() +\
               "/s" + self.generate_sub_rule()
        return rule

    def process(self, rule, iteration):
        i = 0
        result = False
        output = []

        process = Popen(
                    [config.NTZFIND_BIN, rule, "w6", self.period, "k1", "v", "l200"],
                    shell=False,
                    stdout=PIPE
                    )
        
        while True:
            output.append(process.stdout.readline().decode('utf-8'))
            if 'Starting search' in str(output[i]):
                start = i+2
            elif 'CPU time' in str(output[i]):
                start = i+1
            elif 'Length' in str(output[i]):
                end = i
            elif '0 spaceships' in str(output[i]):
                del output[:]
                break
            elif 'Spaceship found' in str(output[i]):
                if end - start < 13 or end - start > 18:
                    del output[:]
                    break

                with open(
                    self.period_file_path+"pattern"+str(iteration+1)+".lif",
                    'w'
                    ) as file:

                    file.write("#Life 1.05\n")
                    file.write('#' + rule + '\n')
                    file.write("#Period " + str(self.period) + '\n')
                    for k in range(end - start):
                        file.write(output[start+k].strip().replace('o','*') + '\n')
                        print(output[start+k].strip())
                    del output[:]
                    print('')
                    result = True
                    break
            i += 1
        return result

    def run(self):
        successes = 0
        while successes < self.iterations:
            rule = self.generate_rule()
            if self.process(rule, successes):
                successes += 1

