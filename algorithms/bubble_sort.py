def bubble_sort(arr, on_step=None):
    arr = arr[:]
    n = len(arr)
    for i in range(n):
        for j in range(n - i - 1):
            if on_step:
                on_step(arr[:], j, j + 1, "compare")
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                if on_step:
                    on_step(arr[:], j, j + 1, "swap")
    return arr
