# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Node.js/Express web application with session-based authentication. Uses `express-session` for session management and `bcryptjs` for password hashing.

## Commands

- `npm start` — Run the server (default port 3000)
- `npm test` — Run tests

## Architecture

- `app.js` — Main Express app. Defines auth routes (`/api/register`, `/api/login`, `/api/logout`, `/api/me`), session config, and `requireAuth` middleware. Exports the app for testing.
- In-memory user store (Map) — intended to be replaced with a database.

## Repository

- Default branch: `main`
- Hosted at `georgiaked4-tech/cloude`
