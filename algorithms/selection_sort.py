def selection_sort(arr, on_step=None):
    arr = arr[:]
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if on_step:
                on_step(arr[:], j, min_idx, "compare")
            if arr[j] < arr[min_idx]:
                min_idx = j
        if min_idx != i:
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
            if on_step:
                on_step(arr[:], i, min_idx, "swap")
    return arr
