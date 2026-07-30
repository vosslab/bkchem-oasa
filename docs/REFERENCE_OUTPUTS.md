# REFERENCE_OUTPUTS.md

Reference SVG and PNG outputs used to validate Haworth rendering.

## Files
- [haworth_reference.svg](reference_outputs/haworth_reference.svg)
- [haworth_reference.png](reference_outputs/haworth_reference.png)

## Regenerate
Run the renderer script (requires pycairo for PNG output):

```
/opt/homebrew/opt/python@3.12/bin/python3.12 tools/render_reference_outputs.py
```

To write elsewhere:

```
/opt/homebrew/opt/python@3.12/bin/python3.12 tools/render_reference_outputs.py --output-dir /path/to/output
```
