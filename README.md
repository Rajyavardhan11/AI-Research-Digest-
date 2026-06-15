# AI Research Digest

AI Research Digest is a fully automated weekly newsletter pipeline for developers, founders, research teams, and AI-curious operators who want the best papers and articles without manually scanning feeds every day.

## What It Does

- Scrapes ArXiv, Hacker News, and Dev.to for fresh AI content
- Uses Ollama to rank the most important items and summarize them
- Compiles a premium HTML email digest
- Sends the digest to each subscriber individually with Resend
- Logs delivery history in SQLite
- Exposes a FastAPI admin dashboard for previewing and triggering runs

## Pipeline Diagram

```text
ArXiv RSS ----\
Hacker News ---+--> Deduplicate --> Ollama filter --> Ollama summaries --> HTML compile --> Resend email
Dev.to API ----/             \--> SQLite history + subscriber sync
                                    \
                                     --> FastAPI admin preview + manual trigger
```

## Setup

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your values.
4. Make sure Ollama is running locally and that `llama3.2` is installed:

```bash
ollama pull llama3.2
ollama serve
```

5. Add your Resend API key and verified sender email to `.env`.

## How To Run

```bash
uvicorn main:app --reload
```

The admin dashboard will be available at `http://127.0.0.1:8000/`.

## Subscribers

Subscribers are stored in `subscribers.json` and mirrored into SQLite on startup.

- Add a subscriber with `POST /api/subscribers`
- Remove a subscriber with `DELETE /api/subscribers/{email}`

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","name":"Your Name"}'
```

## Manual Trigger And Preview

- Trigger a live run and send email:

```bash
curl -X POST http://127.0.0.1:8000/api/trigger
```

- Preview the generated email without sending:

```bash
curl http://127.0.0.1:8000/api/preview
```

## Customizing The Topic

Change `DIGEST_TOPIC` in `.env` to target a niche such as `multimodal AI`, `agentic coding`, or `robotics`.

## Deployment

Railway’s free tier is a good fit for this app. Provision a Python service, set your environment variables, expose port `8000`, and point the start command at:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Admin Dashboard Screenshot

Add a screenshot here after the first successful local run.
