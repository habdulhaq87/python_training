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

# Directory setup
image_directory = 'images/'
output_directory = 'docs/'  # Updated to save in the 'docs' folder
os.makedirs(output_directory, exist_ok=True)  # Create output directory if it doesn't exist

# Google Sheets API Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))  # Load credentials from GitHub secrets
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# Access the Google Sheet and load data
sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1EcEWYavEFsQIJkmr0VGgGiHbqXIrJKFIW_d3mM_teXc/edit?usp=sharing')
points_df = pd.DataFrame(sheet.worksheet('points').get_all_records())
positions_df = pd.DataFrame(sheet.worksheet('positions').get_all_records())
profiles_df = pd.DataFrame(sheet.worksheet('profiles').get_all_records())

# Load background image and initialize SVG code
image_path = os.path.join(image_directory, 'background_image.jpg')
img = Image.open(image_path)
img_width, img_height = img.size
svg_code = f'''<svg viewBox="0 0 {img_width} {img_height}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
  <image href="https://habdulhaq87.github.io/python_training/images/background_image.jpg" x="0" y="0" width="{img_width}" height="{img_height}"/>
'''
svg_elements = []  # Collect all SVG elements here

# Utility Functions
def parse_tuple_string(tuple_string):
    """Parse a string representing a tuple into an actual tuple."""
    try:
        return ast.literal_eval(tuple_string)
    except (ValueError, SyntaxError):
        return None

def check_overlap(existing_positions, new_position, buffer=20):
    """Check if the new position overlaps with any existing positions."""
    new_x, new_y, new_width, new_height = new_position
    for (ex_x, ex_y, ex_width, ex_height) in existing_positions:
        if (abs(new_x - ex_x) < (new_width + ex_width) / 2 + buffer and
            abs(new_y - ex_y) < (new_height + ex_height) / 2 + buffer):
            return True  # Overlap detected
    return False

def get_non_overlapping_position(existing_positions, x, y, text_width, text_height, max_attempts=10, offset_step=15):
    """Adjust position if overlap is detected, within a maximum number of attempts."""
    attempt = 0
    while check_overlap(existing_positions, (x, y, text_width, text_height)) and attempt < max_attempts:
        x += offset_step * (attempt % 2 * 2 - 1)  # Alternates left-right or up-down
        y += offset_step * (1 if attempt % 2 else -1)
        attempt += 1
    return x, y

# Function to calculate the center of the rectangle and wrap the label text
def get_centered_position(x0, y0, x1, y1, label, font_size):
    """Calculate the centered position for the label and wrap text."""
    center_x = (x0 + x1) // 2
    center_y = (y0 + y1) // 2
    max_line_length = 20
    wrapped_text = textwrap.fill(label, width=max_line_length)

    lines = wrapped_text.split('\n')
    text_height = font_size * len(lines)
    text_width = max(len(line) for line in lines) * font_size * 0.6
    text_x = center_x - text_width // 2
    text_y = center_y - text_height // 2
    return text_x, text_y, wrapped_text

# Process Positions and Labels
existing_text_positions = []  # Track text positions to prevent overlaps
for index, row in positions_df.iterrows():
    label = row['Label']
    corner1 = parse_tuple_string(row['Corner Position 1'])
    corner3 = parse_tuple_string(row['Corner Position 3'])
    font_size = row.get('font_size', 40)

    if corner1 and corner3:
        x0, y0 = corner1
        x1, y1 = corner3
        width, height = x1 - x0, y1 - y0
        rect_element = f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" style="stroke:black; fill:none; stroke-width:2"/>'
        svg_elements.append(rect_element)

        # Position label within rectangle, avoiding overlap
        text_x, text_y, wrapped_text = get_centered_position(x0, y0, x1, y1, label, font_size)
        lines = wrapped_text.split('\n')
        text_height = font_size * len(lines)
        text_width = max(len(line) for line in lines) * font_size * 0.6
        text_x, text_y = get_non_overlapping_position(existing_text_positions, text_x, text_y, text_width, text_height)
        existing_text_positions.append((text_x, text_y, text_width, text_height))

        # Create SVG text element
        text_element = f'<text x="{text_x}" y="{text_y + font_size}" font-size="{font_size}" fill="black">'
        for line in lines:
            text_element += f'<tspan x="{text_x}" dy="{font_size}">{line}</tspan>'
        text_element += '</text>'
        svg_elements.append(text_element)

# Circle Drawing for Profile Points
profiles_mapping = {row['Profile']: {'color': f"rgb{tuple(int(row['Color'].strip('#')[i:i+2], 16) for i in (0, 2, 4))}", 'name': row['Name']}
                    for _, row in profiles_df.iterrows()}
circle_radius = 10

def generate_offsets(num_points, radius):
    offsets = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        offsets.append((radius * 2 * math.cos(angle), radius * 2 * math.sin(angle)))
    return offsets

offsets = {profile: offset for profile, offset in zip(profiles_mapping.keys(), generate_offsets(len(profiles_mapping), circle_radius))}

for _, row in points_df.iterrows():
    position = parse_tuple_string(row['Position'])
    if position:
        x, y = position
        for profile, info in profiles_mapping.items():
            if row.get(profile) == 1:
                color_rgb_str = info['color']
                name = info['name']
                offset_x, offset_y = offsets[profile]
                x_adj, y_adj = x + offset_x, y + offset_y
                circle_element = f'<circle cx="{x_adj}" cy="{y_adj}" r="{circle_radius}" fill="{color_rgb_str}" stroke="{color_rgb_str}"/>'
                svg_elements.append(circle_element)
                text_x, text_y = x_adj + circle_radius + 5, y_adj + circle_radius / 2
                svg_elements.append(f'<text x="{text_x}" y="{text_y}" font-size="20" fill="black">{name}</text>')

# Finalize and Save HTML
svg_code += "\n".join(svg_elements) + '</svg>'
html_code = f"""<!DOCTYPE html>
<html><head><title>Output Image</title><style>body,html{{margin:0;padding:0;height:100%;width:100%;display:flex;justify-content:center;align-items:center;overflow:hidden;}}</style></head>
<body>{svg_code}</body></html>"""

output_html_path = os.path.join(output_directory, 'index.html')
with open(output_html_path, 'w') as html_file:
    html_file.write(html_code)

print(f"HTML file generated successfully at: {output_html_path}")
