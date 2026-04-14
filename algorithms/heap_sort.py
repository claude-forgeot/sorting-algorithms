def heap_sort(arr, on_step=None):
    arr = arr[:]
    n = len(arr)

    # Build max heap
    for i in range(n // 2 - 1, -1, -1):
        _heapify(arr, n, i, on_step)

    # Extract elements one by one
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        if on_step:
            on_step(arr[:], 0, i, "swap")
        _heapify(arr, i, 0, on_step)

    return arr


def _heapify(arr, n, i, on_step):
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2

    if left < n:
        if on_step:
            on_step(arr[:], left, largest, "compare")
        if arr[left] > arr[largest]:
            largest = left
    if right < n:
        if on_step:
            on_step(arr[:], right, largest, "compare")
        if arr[right] > arr[largest]:
            largest = right

    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        if on_step:
            on_step(arr[:], i, largest, "swap")
        _heapify(arr, n, largest, on_step)
