def merge_sort(arr, on_step=None):
    arr = arr[:]
    _merge_sort(arr, 0, len(arr) - 1, on_step)
    return arr


def _merge_sort(arr, left, right, on_step):
    if left >= right:
        return
    mid = (left + right) // 2
    _merge_sort(arr, left, mid, on_step)
    _merge_sort(arr, mid + 1, right, on_step)
    _merge(arr, left, mid, right, on_step)


def _merge(arr, left, mid, right, on_step):
    left_part = arr[left : mid + 1]
    right_part = arr[mid + 1 : right + 1]
    i = j = 0
    k = left
    while i < len(left_part) and j < len(right_part):
        if on_step:
            on_step(arr[:], left + i, mid + 1 + j, "compare")
        if left_part[i] <= right_part[j]:
            arr[k] = left_part[i]
            i += 1
        else:
            arr[k] = right_part[j]
            j += 1
        if on_step:
            on_step(arr[:], k, k, "set")
        k += 1
    while i < len(left_part):
        arr[k] = left_part[i]
        if on_step:
            on_step(arr[:], k, k, "set")
        i += 1
        k += 1
    while j < len(right_part):
        arr[k] = right_part[j]
        if on_step:
            on_step(arr[:], k, k, "set")
        j += 1
        k += 1
