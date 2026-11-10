def merge_intervals(intervals):
    ordered = []
    for start, end in intervals:
        if start > end:
            raise ValueError("start exceeds end")
        ordered.append((start, end))
    ordered.sort(key=lambda interval: interval[0])
    if not ordered:
        return []
    result = [list(ordered[0])]
    for start, end in ordered[1:]:
        previous = result[-1]
        if start > previous[1]:
            result.append([start, end])
        else:
            previous[1] = max(previous[1], end)
    return result
