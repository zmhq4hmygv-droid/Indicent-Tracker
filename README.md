# Incident Tracker 🚨

An automated system that monitors police events and sends email notifications to registered users.

## How it works

1. Users sign up via the web app and select their city
2. GitHub Actions runs a Python script every 5 minutes
3. The script fetches new events from the [Swedish Police API](https://polisen.se/api/events)
4. Relevant crimes are sent via email to users in the affected city

## Tech Stack

- Python 3.9
- Firebase (Authentication + Firestore)
- GitHub Actions
- Gmail SMTP

## Files

- `send_email.py` — Main script that fetches and sends notifications
- `index.html` — Web app for registration and settings
- `.github/workflows/run.yml` — GitHub Actions schedule
- `skickade.json` — Tracks already sent events

## Setup

1. Add `EMAIL_PASSWORD` and `FIREBASE_KEY` as GitHub Secrets
2. Enable Email/Password in Firebase Authentication
3. Deploy `index.html` to Firebase Hosting
