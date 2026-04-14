def comb_sort(arr, on_step=None):
    arr = arr[:]
    n = len(arr)
    gap = n
    shrink = 1.3
    sorted_flag = False

    while not sorted_flag:
        gap = int(gap / shrink)
        if gap <= 1:
            gap = 1
            sorted_flag = True

        i = 0
        while i + gap < n:
            if on_step:
                on_step(arr[:], i, i + gap, "compare")
            if arr[i] > arr[i + gap]:
                arr[i], arr[i + gap] = arr[i + gap], arr[i]
                sorted_flag = False
                if on_step:
                    on_step(arr[:], i, i + gap, "swap")
            i += 1

    return arr
