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
