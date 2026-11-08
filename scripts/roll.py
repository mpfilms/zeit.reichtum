#!/usr/bin/env python3
"""Zufall für den Workflow (statt LLM-Bauchgefühl).

  roll.py pitch-nurture     -> Pitch | Nurture (50/50)
  roll.py caption-variant   -> a | b (50/50)
"""
import random
import sys

rng = random.SystemRandom()
CHOICES = {
    "pitch-nurture": ["Pitch", "Nurture"],
    "caption-variant": ["a", "b"],
}

if len(sys.argv) != 2 or sys.argv[1] not in CHOICES:
    sys.exit(__doc__)
print(rng.choice(CHOICES[sys.argv[1]]))
