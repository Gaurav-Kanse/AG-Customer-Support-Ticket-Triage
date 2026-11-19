"""Evaluation metrics helpers."""


def ratio(a, b):
    return a / b if b else 0.0


def binary_metrics(y_true, y_pred):
    tp = sum(a and b for a, b in zip(y_true, y_pred))
    fp = sum((not a) and b for a, b in zip(y_true, y_pred))
    fn = sum(a and (not b) for a, b in zip(y_true, y_pred))
    p = ratio(tp, tp + fp)
    r = ratio(tp, tp + fn)
    return {"precision": p, "recall": r, "f1": ratio(2 * p * r, p + r)}
