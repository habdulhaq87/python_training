name: Deploy HTML to GitHub Pages

on:
  push:
    branches:
      - main  # Triggers deployment when pushing to the main branch

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 10  # Increase the timeout to 10 minutes

    steps:
    - name: Checkout code
      uses: actions/checkout@v4  # Updated to v4 to support Node.js 20

    - name: Set up Python
      uses: actions/setup-python@v5  # Updated to v5 to support Node.js 20
      with:
        python-version: '3.x'  # Specify the Python version you need

    - name: Install dependencies
      run: |
        pip install pandas Pillow

    - name: Run Python script
      run: |
        python scripts/main_script.py  # Executes the main script that generates the HTML file

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}  # Automatically provided by GitHub Actions
        publish_dir: ./docs  # This is the directory where the HTML is generated
