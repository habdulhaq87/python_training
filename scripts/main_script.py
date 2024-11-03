# Import required libraries
from PIL import Image, ImageDraw
import pandas as pd
import textwrap
import ast
import math
import os
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# Other parts of the script remain the same...

# Function to detect overlaps between text positions
def check_overlap(existing_positions, new_position, buffer=10):
    """Check if the new position overlaps with any existing positions."""
    new_x, new_y, new_width, new_height = new_position
    for (ex_x, ex_y, ex_width, ex_height) in existing_positions:
        if (abs(new_x - ex_x) < (new_width + ex_width) / 2 + buffer and
            abs(new_y - ex_y) < (new_height + ex_height) / 2 + buffer):
            return True  # Overlap detected
    return False

# Function to get a non-overlapping position for text labels
def get_non_overlapping_position(existing_positions, x, y, text_width, text_height, max_attempts=10, offset_step=15):
    """Adjust position if overlap is detected, within a maximum number of attempts."""
    attempt = 0
    while check_overlap(existing_positions, (x, y, text_width, text_height)) and attempt < max_attempts:
        x += offset_step * (attempt % 2 * 2 - 1)  # Alternates left-right or up-down
        y += offset_step * (1 if attempt % 2 else -1)
        attempt += 1
    return x, y

# Modify the loop where text labels are added to the SVG
existing_text_positions = []  # Track existing text positions to avoid overlaps

for index, row in positions_df.iterrows():
    label = row['Label']
    corner1 = parse_tuple_string(row['Corner Position 1'])
    corner3 = parse_tuple_string(row['Corner Position 3'])
    font_size = row.get('font_size', 40)  # Default font size

    if corner1 and corner3:
        x0, y0 = corner1
        x1, y1 = corner3

        # Draw the rectangle
        width = x1 - x0
        height = y1 - y0
        rect_element = f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" style="stroke:black; fill:none; stroke-width:2"/>'
        svg_elements.append(rect_element)

        # Get centered text position
        text_x, text_y, wrapped_text = get_centered_position(x0, y0, x1, y1, label, font_size)

        # Calculate text dimensions
        lines = wrapped_text.split('\n')
        text_height = font_size * len(lines)
        text_width = max([len(line) for line in lines]) * font_size * 0.6  # Approximate width

        # Get a non-overlapping position
        text_x, text_y = get_non_overlapping_position(existing_text_positions, text_x, text_y, text_width, text_height)
        
        # Add this text position to the list of existing positions to check against
        existing_text_positions.append((text_x, text_y, text_width, text_height))

        # Add text label
        text_element = f'<text x="{text_x}" y="{text_y + font_size}" font-size="{font_size}" fill="black">'
        dy = 0
        for line in lines:
            text_element += f'<tspan x="{text_x}" dy="{dy}">{line}</tspan>'
            dy = font_size
        text_element += '</text>'
        svg_elements.append(text_element)

# Rest of the script remains unchanged...
