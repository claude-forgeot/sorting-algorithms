def insertion_sort(arr, on_step=None):
    arr = arr[:]
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0:
            if on_step:
                on_step(arr[:], j, j + 1, "compare")
            if arr[j] > key:
                arr[j + 1] = arr[j]
                if on_step:
                    on_step(arr[:], j, j + 1, "set")
                j -= 1
            else:
                break
        arr[j + 1] = key
        if on_step and j + 1 != i:
            on_step(arr[:], j + 1, j + 1, "set")
    return arr
