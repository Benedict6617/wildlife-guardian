"""
Computer-vision detection scoring for drone/camera-trap imagery.

This module simulates the *output contract* of a real snare/human/thermal
detection model (a fine-tuned YOLO-family object detector in production)
so the rest of the platform -- alert routing, patrol dispatch, dashboards --
can be built and tested against a stable interface before the vision model
is trained and deployed.

`score_frame()` takes lightweight, explainable "frame features" (rather
than raw pixels) and returns a detection verdict. Replace the body of
`score_frame()` with a real inference call (e.g. an ONNX Runtime or
Triton client) without touching any caller.
"""
import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class FrameFeatures:
    """Stand-in for real image features until a trained model is deployed."""
    scene: str            # "dense_bush", "riverline", "open_savanna", "treeline"
    time_of_day: str       # "day", "dusk", "night"
    motion_detected: bool = False
    thermal_hotspot: bool = False


DETECTION_BASE_RATES = {
    "dense_bush": 0.35,
    "riverline": 0.20,
    "open_savanna": 0.08,
    "treeline": 0.28,
}


def score_frame(features: FrameFeatures, seed: Optional[int] = None) -> dict:
    """Return a simulated detection verdict with a confidence score.

    kind: 'snare', 'human', 'none'
    """
    rng = random.Random(seed)
    base = DETECTION_BASE_RATES.get(features.scene, 0.15)

    if features.thermal_hotspot and features.time_of_day in ("dusk", "night"):
        if rng.random() < 0.7:
            return {
                "kind": "human",
                "confidence_pct": round(rng.uniform(72, 96), 1),
                "notes": "Thermal signature consistent with upright human gait.",
            }

    if features.motion_detected and rng.random() < base + 0.25:
        return {
            "kind": "human",
            "confidence_pct": round(rng.uniform(55, 85), 1),
            "notes": "Motion trigger with humanoid silhouette candidate.",
        }

    if rng.random() < base:
        return {
            "kind": "snare",
            "confidence_pct": round(rng.uniform(60, 94), 1),
            "notes": f"Wire-loop pattern detected in {features.scene.replace('_', ' ')}.",
        }

    return {"kind": "none", "confidence_pct": round(rng.uniform(0, 30), 1), "notes": "No threat pattern matched."}
