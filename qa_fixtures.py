"""Imágenes sintéticas con verdad conocida, compartidas por las suites de QA."""
import os
import tempfile

import cv2
import numpy as np

TMP = tempfile.mkdtemp(prefix="qa_")


def make_ruler(spacing, angle=0, bright=1.0, w=900, h=1200, noise=0,
               tick_len=120, major_every=10):
    img = np.full((h, w, 3), 245, np.uint8)
    cx = w // 2
    for i, y in enumerate(range(0, h, spacing)):
        L = tick_len + (60 if i % major_every == 0 else 0)
        cv2.line(img, (cx, y), (cx + L, y), (20, 20, 20), 2)
    cv2.line(img, (cx, 0), (cx, h), (60, 60, 60), 2)  # borde
    if angle:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderValue=(245, 245, 245))
    if bright != 1.0:
        img = (img.astype(np.float32) * bright).astype(np.uint8)
    if noise:
        img = np.clip(img.astype(np.int16) +
                      np.random.randint(-noise, noise + 1, img.shape), 0, 255
                      ).astype(np.uint8)
    path = os.path.join(TMP, f"r_{spacing}_{angle}_{int(bright*100)}_{noise}.jpg")
    cv2.imwrite(path, img)
    return path


def make_drops(diams, upp_w=700, upp_h=500):
    img = np.full((upp_h, upp_w, 3), 235, np.uint8)
    n = len(diams)
    for i, d in enumerate(diams):
        cx = int((i + 1) * upp_w / (n + 1))
        cv2.circle(img, (cx, upp_h // 2), max(1, d // 2), (5, 5, 5), -1)
    path = os.path.join(TMP, "drops_" + "_".join(map(str, diams)) + ".jpg")
    cv2.imwrite(path, img)
    return path
