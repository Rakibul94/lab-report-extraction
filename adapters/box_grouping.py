

from __future__ import annotations

from services.ocr_port import OCRLine, OCRResult


def boxes_to_reading_order(items: list, gap_factor: float = 3.0) -> OCRResult:
    def top(i):    return min(float(p[1]) for p in i[0])
    def bottom(i): return max(float(p[1]) for p in i[0])
    def y_mid(i):  return (top(i) + bottom(i)) / 2
    def x_left(i): return min(float(p[0]) for p in i[0])
    def x_right(i):return max(float(p[0]) for p in i[0])

    rows: list[list[list]] = []
    for item in sorted(items, key=top):
        if rows:
            anchor = rows[-1][0]
            if abs(y_mid(item) - y_mid(anchor)) <= (bottom(anchor) - top(anchor)) * 0.5:
                rows[-1].append(item)
                continue
        rows.append([item])

    lines = []
    for row in rows:
        row.sort(key=x_left)
        heights = [bottom(i) - top(i) for i in row]
        med_h = sorted(heights)[len(heights) // 2]
        segment = [row[0]]
        for prev, cur in zip(row, row[1:]):
            gap = x_left(cur) - x_right(prev)
            if gap > gap_factor * med_h:          # column boundary
                lines.append(segment)
                segment = [cur]
            else:
                segment.append(cur)
        lines.append(segment)

    return OCRResult(lines=tuple(
        OCRLine(
            text=" ".join(text for _, text, _ in sorted(line, key=x_left)),
            confidence=sum(min(1.0, max(0.0, float(s))) for _, _, s in line) / len(line),
        )
        for line in lines
    ))