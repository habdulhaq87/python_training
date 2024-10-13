# Import required libraries
from PIL import Image, ImageDraw
import pandas as pd
import textwrap
import ast
import math
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Directory setup
image_directory = 'images/'
output_directory = 'docs/'  # Updated to save in the 'docs' folder

# Create output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)

# Google Sheets API Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
client = gspread.authorize(creds)

# Access the Google Sheet
sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1EcEWYavEFsQIJkmr0VGgGiHbqXIrJKFIW_d3mM_teXc/edit?usp=sharing')

# Fetch data from the 'points' tab
points_sheet = sheet.worksheet('points')
points_data = points_sheet.get_all_records()
points_df = pd.DataFrame(points_data)

# Fetch data from the 'positions' tab
positions_sheet = sheet.worksheet('positions')
positions_data = positions_sheet.get_all_records()
positions_df = pd.DataFrame(positions_data)

# Load the profiles data from the local CSV file
profiles_df = pd.read_csv(os.path.join('data/', 'profiles.csv'))

# Load the background image (ensure the filename matches exactly)
image_path = os.path.join(image_directory, 'background_image.jpg')
img = Image.open(image_path)
draw = ImageDraw.Draw(img)

# Get image dimensions
img_width, img_height = img.size

# Initialize SVG code with responsive settings
svg_elements = []

# Add the image as the background using the absolute URL and responsive viewBox
svg_code = f'''<svg viewBox="0 0 {img_width} {img_height}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
  <image href="https://habdulhaq87.github.io/python_training/images/background_image.jpg" x="0" y="0" width="{img_width}" height="{img_height}"/>
'''

# Function to parse string tuples (e.g., "(2103, 167)") into real tuple objects
def parse_tuple_string(tuple_string):
    try:
        return ast.literal_eval(tuple_string)
    except (ValueError, SyntaxError):
        return None

# Parse the 'Position' column to get the coordinates in points_df
points_df['Position'] = points_df['Position'].apply(parse_tuple_string)

# Function to calculate the center of the rectangle and wrap the label text
def get_centered_position(x0, y0, x1, y1, label, font_size):
    center_x = (x0 + x1) // 2
    center_y = (y0 + y1) // 2

    # Approximate text dimensions
    average_char_width = font_size * 0.6
    max_line_length = 20  # Maximum characters per line
    wrapped_text = textwrap.fill(label, width=max_line_length)

    lines = wrapped_text.split('\n')
    text_height = font_size * len(lines)
    text_width = max([len(line) for line in lines]) * average_char_width

    text_x = center_x - text_width // 2
    text_y = center_y - text_height // 2

    return text_x, text_y, wrapped_text

# Loop through the positions data and add rectangles and labels to the SVG
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

        # Add text label
        lines = wrapped_text.split('\n')
        text_element = f'<text x="{text_x}" y="{text_y + font_size}" font-size="{font_size}" fill="black">'
        dy = 0
        for line in lines:
            text_element += f'<tspan x="{text_x}" dy="{dy}">{line}</tspan>'
            dy = font_size
        text_element += '</text>'
        svg_elements.append(text_element)

# ------------------- Circle Drawing Code -------------------

# Build a mapping from Profile to color and name
profiles_mapping = {}
profiles_list = []

for index, row in profiles_df.iterrows():
    profile = row['Profile']
    color_hex = row['Color']
    name = row['Name']
    color_rgb = tuple(int(color_hex.strip('#')[i:i+2], 16) for i in (0, 2, 4))
    color_rgb_str = f'rgb{color_rgb}'
    profiles_mapping[profile] = {'color': color_rgb_str, 'name': name}
    profiles_list.append(profile)

# Generate offsets dynamically around the circle to prevent overlap
def generate_offsets(num_points, radius):
    offsets = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        offset_x = radius * 2 * math.cos(angle)
        offset_y = radius * 2 * math.sin(angle)
        offsets.append((offset_x, offset_y))
    return offsets

# Circle properties
circle_radius = 10
offsets_list = generate_offsets(len(profiles_list), circle_radius)
offsets = {profile: offset for profile, offset in zip(profiles_list, offsets_list)}

# Draw circles based on points and profiles data
for index, row in points_df.iterrows():
    position = row['Position']
    if position:
        x, y = position
        for profile in profiles_list:
            value = row.get(profile, 0)
            if value == 1:
                profile_info = profiles_mapping.get(profile)
                if profile_info:
                    color_rgb_str = profile_info['color']
                    name = profile_info['name']
                    offset_x, offset_y = offsets[profile]
                    x_adj = x + offset_x
                    y_adj = y + offset_y

                    # Add circle to SVG
                    circle_element = f'<circle cx="{x_adj}" cy="{y_adj}" r="{circle_radius}" fill="{color_rgb_str}" stroke="{color_rgb_str}"/>'
                    svg_elements.append(circle_element)

                    # Add profile name
                    text_x = x_adj + circle_radius + 5
                    text_y = y_adj + 20 / 2
                    text_element = f'<text x="{text_x}" y="{text_y}" font-size="20" fill="black">{name}</text>'
                    svg_elements.append(text_element)

# ------------------- End of Circle Drawing Code -------------------

# Combine all SVG elements
for element in svg_elements:
    svg_code += element + '\n'

# Close the SVG tag
svg_code += '</svg>'

# Wrap the SVG code into an HTML template with responsive styling
html_code = f'''<!DOCTYPE html>
<html>
<head>
    <title>Output Image</title>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }}
    </style>
</head>
<body>
    {svg_code}
</body>
</html>
'''

# Define the path where you want to save the HTML file in the 'docs/' folder
output_html_path = os.path.join(output_directory, 'index.html')

# Save the HTML code to the file
with open(output_html_path, 'w') as html_file:
    html_file.write(html_code)

print(f"New HTML file saved to {output_html_path}")

# Add this check at the end of your script
if os.path.exists(output_html_path):
    print(f"HTML file generated successfully at: {output_html_path}")
else:
    raise FileNotFoundError(f"HTML file not found at: {output_html_path}")

# Debugging: Check if the output directory exists
print(f"Output directory: {output_directory}")
print(f"Output file path: {output_html_path}")
print(f"Current working directory: {os.getcwd()}")

# Debugging: List files in the output directory
print("Files in the output directory:")
print(os.listdir(output_directory))

# Check if the file is written
if os.path.exists(output_html_path):
    print(f"HTML file generated successfully at {output_html_path}")
else:
    raise FileNotFoundError(f"Failed to generate HTML file at {output_html_path}")
