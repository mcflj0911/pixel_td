"""The game draws to a fixed-size canvas. This fits that canvas into the window, keeping its proportions, and maps
mouse positions in the window back onto the canvas."""


def fit(window_w, window_h, canvas_w, canvas_h):
    """The rectangle (x, y, w, h) where the canvas is drawn in the window: as large as possible, centred, with
    black bars where the window's proportions differ."""
    scale = min(window_w / canvas_w, window_h / canvas_h)
    w = max(1, int(canvas_w * scale))
    h = max(1, int(canvas_h * scale))
    return ((window_w - w) // 2, (window_h - h) // 2, w, h)


def to_canvas(pos, dest, canvas_w, canvas_h):
    """A window position as a canvas position. Positions in the black bars fall outside the canvas."""
    x, y, w, h = dest
    return (int((pos[0] - x) * canvas_w / w), int((pos[1] - y) * canvas_h / h))
