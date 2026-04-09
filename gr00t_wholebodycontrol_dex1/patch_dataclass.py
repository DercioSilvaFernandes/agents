#!/usr/bin/env python3
"""Patch Python 3.11 dataclass mutable defaults in gr00trobocasa"""
from dataclasses import field, is_dataclass
import ast
import re

files_to_patch = [
    "/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py",
    "/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/scene/configs.py",
]

for filepath in files_to_patch:
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Simple regex to fix  = np.array(...) patterns
        import re
        # Replace np.array  defaults with field(default_factory=...)
        pattern = r'(\s+\w+:\s*[^\s]+\s*=\s*)np\.array\('
        replacement = r'\1field(default_factory=lambda: np.array('
        content = re.sub(pattern, replacement, content)
        
        # Replace = SamplingConfig() with field(default_factory=SamplingConfig)
        pattern = r'(\s+\w+:\s*[^\s]+\s*=\s*)SamplingConfig\(\)'
        replacement = r'\1field(default_factory=SamplingConfig)'
        content = re.sub(pattern, replacement, content)
        
        # Add field import if not present
        if 'from dataclasses import' in content and 'field' not in content.split('from dataclasses import')[1].split('\n')[0]:
            content = content.replace('from dataclasses import', 'from dataclasses import field, ')
        
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Patched {filepath}")
    except Exception as e:
        print(f"✗ Error patching {filepath}: {e}")
