"""New form field creation with appearance streams.

This module handles the creation of new AcroForm fields at a given page
location, including generating correct appearance streams (normal, rollover,
down states) so that the fields render correctly in PDF viewers.

Planned public API:
    FieldFactory     -- Creates new form field dictionaries with appearance streams
                        for text fields, checkboxes, radio buttons, dropdowns,
                        and push buttons.
"""
from __future__ import annotations
