"""
Signals relating to claims.
"""
from django.dispatch import Signal

# Sent just after a claim was posted. See above for how this differs
# from the claim object's post-save signal.
claim_was_posted = Signal(providing_args=["claim", "request"])
score_was_changed = Signal(providing_args=["form", "request"])
