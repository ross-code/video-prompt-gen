# video-prompt-gen

A CLI for generating highly detailed, cinematic prompts for AI video generation
models (Seedance 2.0, etc.).

It walks you through questions about your desired video — subject, camera
movement, lighting, style — then uses Claude to synthesize a polished,
model-ready prompt.

## Install

```bash
pip install -e .
```

## Setup

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Get a key at https://console.anthropic.com/.

## Usage

```bash
vpg
```

---

# Conference Finder

A web app that surfaces real, upcoming conferences tailored to your business.
Describe your **industry**, your **niche**, and **what you're selling**, and it
uses Claude with live web search to find relevant conferences, trade shows, and
summits in the coming months — with a **Refresh** button to pull a fresh sweep
any time.

## Run

```bash
pip install -e .          # installs Flask + the conference-finder command
export ANTHROPIC_API_KEY=sk-ant-...
conference-finder
```

Then open http://127.0.0.1:5050.

> **macOS note:** the app defaults to port **5050** because macOS uses port 5000
> for its AirPlay Receiver. If you force `PORT=5000` you'll hit AirPlay (an
> `AirTunes` 403/HTML response) instead of this app. Pick any free port with
> `PORT=5060 conference-finder` if 5050 is taken too.

Fill in your details, pick a time window (default: next 6 months), and hit
**Find conferences**. For each event you get the dates, location, format, a
plain-language reason it fits *your* niche and offering, topics, and a link to
the official site. Click **Refresh** to research again.

### How it works

- For each search, Claude is asked to use the `web_search` tool to find **real**
  events (real dates, real URLs — it's instructed never to invent them) whose
  start date falls inside your chosen window, then return them as structured
  JSON tailored to your profile.
- Your profile and the last results are cached locally (in
  `~/.conference-finder/` by default, override with `CONF_FINDER_DATA`) so the
  page shows your previous sweep on reload without spending another API call.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key. |
| `HOST` | `127.0.0.1` | Bind address for the web server. |
| `PORT` | `5050` | Port for the web server (avoids the macOS AirPlay conflict on 5000). |
| `CONF_FINDER_DATA` | `~/.conference-finder` | Where the profile + results are cached. |
| `FLASK_DEBUG` | off | Set to `1` to enable Flask debug mode. |
