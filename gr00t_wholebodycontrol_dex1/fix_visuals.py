#!/usr/bin/env python3
"""Simple fix for visuals_utls.py dataclass issue"""

import re

filepath = "/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py"

with open(filepath, 'r') as f:
    content = f.read()

# Add field import if not present
if 'from dataclasses import field' not in content:
    content = content.replace('from dataclasses import dataclass', 'from dataclasses import dataclass, field')

# Fix rgba_a: np.array([...])
content = re.sub(r'rgba_a:\s*np\.ndarray\s*=\s*np\.array\((.*?)\)',
                 r'rgba_a: np.ndarray = field(default_factory=lambda: np.array(\1))',
                 content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)

print("✓ Fixed visuals_utls.py")
