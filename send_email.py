name: Run Python script

on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:

jobs:
  run-script:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.9"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run script
        run: python send_email.py
        env:
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
