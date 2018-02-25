import random
import os

def random_init():
    rnd_string = os.urandom(4)
    rnd_num = int(rnd_string.encode('hex'), 16)
    random.seed(rnd_num)

def get_int(low, high):
    random_init()
    return random.randint(low, high)
    
def shuffle(obj):
    random_init()
    random.shuffle(obj)
