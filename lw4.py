from collections import Counter
from multiprocessing import Pool
import time

def mapper(text):
    words = text.split()
    return Counter(words)

def reducer(counters):
    return sum(counters, Counter())

def mapreduce(data, num_workers):
    start_time = time.time()
    pool = Pool(num_workers)
    mapped_data = pool.map(mapper, data)
    reduced_data = reducer(mapped_data)
    end_time = time.time()
    time_lasted = end_time - start_time
    return reduced_data, time_lasted

if __name__ == "__main__":
    # Example usage
    with open('data.txt') as f:
        data = f.readlines()
    print(type(data))
    result, time_lasted = mapreduce(data, num_workers=2)
    print(result, time_lasted)