

from __future__ import annotations

from services.ocr_port import OCRLine, OCRResult


def boxes_to_reading_order(items: list) -> OCRResult:
    """Group (box, text, score) detections into reading-order lines.

    Shared by every detection+recognition engine (EasyOCR, RapidOCR, ...).
    Box = 4 (x, y) corners, any order. Text joined with single spaces;
    scores clamped to the port's 0.0-1.0 contract then averaged per line.
    """

    def top(item: list) -> float:
        return min(float(p[1]) for p in item[0])

    def bottom(item: list) -> float:
        return max(float(p[1]) for p in item[0])

    def y_mid(item: list) -> float:
        return (top(item) + bottom(item)) / 2

    def x_left(item: list) -> float:
        return min(float(p[0]) for p in item[0])   # min over corners: rotation-safe

    grouped: list[list[list]] = []
    for item in sorted(items, key=top):
        if grouped:
            anchor = grouped[-1][0]
            if abs(y_mid(item) - y_mid(anchor)) <= (bottom(anchor) - top(anchor)) * 0.6:
                grouped[-1].append(item)
                continue
        grouped.append([item])

    return OCRResult(lines=tuple(
        OCRLine(
            text=" ".join(text for _, text, _ in sorted(line, key=x_left)),
            confidence=sum(min(1.0, max(0.0, float(score))) for _, _, score in line) / len(line),
        )
        for line in grouped
    ))