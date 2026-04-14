# Sorting Algorithms

## Overview

This project implements seven sorting algorithms in Python. It provides an interactive mode to sort a user-entered list, a benchmark module measuring execution time and operation counts, and an animated pygame visualization in single-algorithm or race mode (all seven running side by side).

## Installation

Requires Python 3.11+

```bash
git clone https://github.com/claude-forgeot/sorting-algorithms.git
cd sorting-algorithms
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Interactive mode

```bash
python3 main.py
```

Enter a list of space-separated numbers, then pick an algorithm: `bubble`, `selection`, `insertion`, `merge`, `quick`, `heap`, `comb`. The program prints the input list and the sorted result.

### Benchmarks

```bash
python3 main.py --benchmark
```

Runs all seven algorithms on 1,000 random integers. Prints a comparison table (time, comparisons, swaps) and exports results to two timestamped files: `benchmark_YYYYMMDD_HHMMSS.json` and `benchmark_YYYYMMDD_HHMMSS.csv`.

### Visualization

```bash
python3 main.py --visual
```

Opens a pygame window showing the sort on a color wheel in real time. Enter the algorithm and array size at startup.

| Key | Action |
|-----|--------|
| Space | Pause / Resume |
| `+` / `-` | Speed up / Slow down |
| `R` | New random array |
| `S` | Sorted array |
| `I` | Reverse-sorted array |
| `D` | Array with duplicates |
| `Q` | Quit |

### Race mode

```bash
python3 main.py --race
```

Runs all seven algorithms in parallel on the same array. Each algorithm occupies a sector of the wheel. A counter shows how many algorithms have finished.

| Key | Action |
|-----|--------|
| Space | Pause / Resume |
| `+` / `-` | Speed up / Slow down |
| `Q` | Quit |

## Algorithms

### Bubble sort

Walks through the list comparing adjacent elements and swapping them if needed. After each full pass, the largest element ends up in its final position. The process repeats until no swap occurs.

| Case | Complexity |
|------|-----------|
| Best | O(n) |
| Average | O(n^2) |
| Worst | O(n^2) |
| Space | O(1) |

Stable: yes

### Selection sort

Splits the list into a sorted part (initially empty) and an unsorted part. On each iteration, finds the minimum of the unsorted part and appends it to the sorted part. Requires exactly n - 1 swaps.

| Case | Complexity |
|------|-----------|
| Best | O(n^2) |
| Average | O(n^2) |
| Worst | O(n^2) |
| Space | O(1) |

Stable: no

### Insertion sort

Builds the sorted list one element at a time. For each new element, shifts it to its correct position in the already-sorted part by moving larger elements to the right. Efficient on data that is already partially sorted.

| Case | Complexity |
|------|-----------|
| Best | O(n) |
| Average | O(n^2) |
| Worst | O(n^2) |
| Space | O(1) |

Stable: yes

### Merge sort

Recursively splits the list into two halves until each sublist contains a single element. Then merges the sublists by comparing elements pairwise. Guarantees O(n log n) in all cases, at the cost of O(n) extra memory.

| Case | Complexity |
|------|-----------|
| Best | O(n log n) |
| Average | O(n log n) |
| Worst | O(n log n) |
| Space | O(n) |

Stable: yes

### Quicksort

Picks a pivot element and partitions the list into two sublists: elements less than the pivot and elements greater. Applies the same process recursively. Fast in practice, but degrades to O(n^2) on already-sorted data if the pivot is poorly chosen.

| Case | Complexity |
|------|-----------|
| Best | O(n log n) |
| Average | O(n log n) |
| Worst | O(n^2) |
| Space | O(log n) |

Stable: no

### Heapsort

Builds a max-heap from the list, then repeatedly extracts the maximum element and places it at the end. The heap structure guarantees each extraction costs O(log n). Sorts in place with no extra allocation.

| Case | Complexity |
|------|-----------|
| Best | O(n log n) |
| Average | O(n log n) |
| Worst | O(n log n) |
| Space | O(1) |

Stable: no

### Comb sort

A variant of bubble sort that compares distant elements instead of adjacent ones. The initial gap is large and shrinks by a factor of 1.3 on each pass. Eliminates small values stuck near the beginning of the list well before the sort ends.

| Case | Complexity |
|------|-----------|
| Best | O(n log n) |
| Average | O(n log n) |
| Worst | O(n^2) |
| Space | O(1) |

Stable: no

## Benchmark results

Measured on 1,000 random integers (no duplicates, range 0-9,999).

| Algorithm | Time (s) | Comparisons | Swaps |
|-----------|----------|-------------|-------|
| Bubble sort | 1.175745 | 499 500 | 246 039 |
| Selection sort | 0.675543 | 499 500 | 997 |
| Insertion sort | 0.710995 | 247 031 | 246 039 |
| Merge sort | 0.028500 | 8 691 | 9 976 |
| Quicksort | 0.025969 | 11 168 | 6 844 |
| Heapsort | 0.037626 | 16 852 | 9 097 |
| Comb sort | 0.038227 | 22 709 | 4 541 |

The O(n log n) algorithms -- quicksort, merge sort, heapsort, comb sort -- are 20 to 50 times faster than the O(n^2) algorithms on this data. Quicksort is the fastest, followed by merge sort. Among the O(n^2) algorithms, selection sort performs the fewest swaps (n - 1) because it moves each element to its final position only once. Bubble sort is the slowest: its many adjacent swaps are costly.

## Conclusion

The benchmarks confirm the theoretical complexities: O(n log n) algorithms outperform O(n^2), and the gap becomes obvious past a few hundred elements. The visualization shows how each algorithm operates: merge sort divides and merges, bubble sort pushes each value up step by step. For general use, quicksort is the best pick; merge sort is preferable when stability matters. Insertion sort remains useful on small arrays or nearly-sorted data.
