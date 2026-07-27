"""Piano matrix -> VexFlow-ready score document.

Filled by Epic 9. The backend stays notation-agnostic in the sense that it
never emits VexFlow objects; it emits a plain score format (measures,
voices, durations, annotations) that the frontend renders with VexFlow 5.
"""
