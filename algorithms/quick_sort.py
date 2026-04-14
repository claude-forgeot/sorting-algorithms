def quick_sort(arr, on_step=None):
    arr = arr[:]
    stack = [(0, len(arr) - 1)]
    while stack:
        low, high = stack.pop()
        if low < high:
            pivot_idx = _partition(arr, low, high, on_step)
            stack.append((low, pivot_idx - 1))
            stack.append((pivot_idx + 1, high))
    return arr


def _partition(arr, low, high, on_step):
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if on_step:
            on_step(arr[:], j, high, "compare")
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
            if on_step:
                on_step(arr[:], i, j, "swap")
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    if on_step:
        on_step(arr[:], i + 1, high, "swap")
    return i + 1
