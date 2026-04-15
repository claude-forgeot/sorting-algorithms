"""Compact step history for a sorting algorithm.

Stores only deltas without copying the array at each step. The state at
any position is reconstructed on demand by replaying operations from
the initial array.

Two delta formats:
    SwapDelta = (i, j, "swap")           -- real swap of arr[i] and arr[j]
    SwapDelta = (i, j, "compare")        -- read-only comparison (no mutation)
    SetDelta  = (k, old_val, new_val, "set")  -- direct write: arr[k] = new_val

Space complexity: O(n + k)
    n = initial array size
    k = number of recorded steps
    (vs O(n * k) if we copied arr at every step)
"""

from __future__ import annotations

# A delta represents a single algorithm step.
# Internally, steps are either:
#   - SwapDelta: (i, j, event_type)  -- compare/swap on two indices
#   - SetDelta:  (k, old_val, new_val, "set")  -- direct write at index k
# The public API (highlighted, get_state) always exposes the 3-tuple form.
Delta = tuple[int, int, str] | tuple[int, int, int, str]

# RendererState is a plain dict with keys:
#   "arr":         list           -- current array
#   "highlighted": Delta | None   -- (i, j, event_type) or None
#   "done":        bool           -- sort complete


class StepHistory:
    """Step history for a sorting algorithm.

    Typical usage::

        history = StepHistory(initial_array)

        def on_step(arr_copy, i, j, event_type):
            history.add_step(i, j, event_type)

        algo(array, on_step=on_step)

        # read step 42
        state = history.get_state(42)
    """

    def __init__(self, arr_initial: list) -> None:
        """Initialize the history with the original array.

        The array is copied once here and serves as the base for all
        subsequent reconstructions.

        Args:
            arr_initial: array before any sorting
        """
        self._arr_initial: list = arr_initial[:]
        self._steps: list[Delta] = []

    # ------------------------------------------------------------------ #
    # Main interface                                                       #
    # ------------------------------------------------------------------ #

    def add_step(self, i: int, j: int, event_type: str) -> None:
        """Record a swap or compare delta without copying the array.

        Args:
            i:          first index involved in the operation
            j:          second index involved in the operation
            event_type: "compare" (read-only) or "swap" (actual swap)
        """
        self._steps.append((i, j, event_type))

    def add_set(self, index: int, old_val: object, new_val: object) -> None:
        """Record a direct write: arr[index] = new_val.

        Used by algorithms that write from temporary arrays (merge sort)
        or shift elements (insertion sort), where the operation is not a
        symmetric swap.

        Args:
            index:   position written to
            old_val: value at arr[index] before the write
            new_val: value written to arr[index]
        """
        self._steps.append((index, old_val, new_val, "set"))

    def get_state(self, index: int) -> dict:
        """Reconstruct the full array state at the requested step.

        Replays all mutations from steps 0..index (inclusive) to produce
        the array as it was after that step. Supports two delta formats:

        - 3-tuple ``(i, j, "swap")``: symmetric swap of arr[i] and arr[j]
        - 4-tuple ``(k, old, new, "set")``: direct write arr[k] = new

        Comparisons (event_type == "compare") are read-only and skipped.

        Args:
            index: position in the history (0-based)

        Returns:
            dict with reconstructed arr, highlighted and done.
        """
        arr: list = self._arr_initial[:]

        limit = min(index + 1, len(self._steps))
        for k in range(limit):
            step = self._steps[k]
            if len(step) == 4 and step[3] == "set":
                # SetDelta: (index, old_val, new_val, "set")
                arr[step[0]] = step[2]
            elif step[2] == "swap":
                # SwapDelta: (i, j, "swap")
                arr[step[0]], arr[step[1]] = arr[step[1]], arr[step[0]]

        # Build highlight for the renderer (always a 3-tuple: i, j, event_type)
        highlighted: Delta | None = None
        if 0 <= index < len(self._steps):
            step = self._steps[index]
            if len(step) == 4 and step[3] == "set":
                # SetDelta -> expose as (index, index, "set") for renderers
                highlighted = (step[0], step[0], "set")
            else:
                highlighted = step

        # step is done when index reaches or exceeds the last step
        done: bool = len(self._steps) == 0 or index >= len(self._steps) - 1

        return {"arr": arr, "highlighted": highlighted, "done": done}

    def __len__(self) -> int:
        """Number of recorded steps in the history."""
        return len(self._steps)

    def step_event(self, index: int) -> str | None:
        """Return the event type at step index without reconstructing the array.

        O(1) direct access. Used by widgets to iterate through history
        efficiently (e.g. precomputing swap markers).

        Args:
            index: position in the history (0-based)

        Returns:
            "compare", "swap", "set", or None if index is out of bounds.
        """
        if 0 <= index < len(self._steps):
            step = self._steps[index]
            # 4-tuple: (k, old, new, "set") -- event type is at index 3
            # 3-tuple: (i, j, event_type) -- event type is at index 2
            return step[3] if len(step) == 4 else step[2]
        return None
