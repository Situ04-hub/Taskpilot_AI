# TaskPilot AI - architecture

## the gist

taskpilot pulls tasks from a bunch of places, figures out which ones are hiding in raw emails/chat that never made it into a tracker, merges the dupes, scores everything with reasons attached so its not a black box, builds a schedule out of it, and lets u ask it stuff. theres also a bg process watching for sla critical things and just handling them on its own.

## pipeline

```
ingest (structured + real gmail)
  -> extract (pull tasks outta raw text)
    -> dedupe (merge the similar ones)
      -> prioritize (score + explain)
        -> plan (deep work schedule)
        -> converse (chat using live task state)
        -> autonomous agent watching for escalated stuff, resolves on its own
```

## files, what they do

models.py - the Task schema. everything from every source gets normalized into this same shape so the rest of the code doesnt care where it came from

mock_data.py - fake jira tickets, a servicenow incident, github issue, plus a raw outlook email thread and slack convo as plain text (these two go thru extraction since theyre unstructured)

gmail_loader.py - actually real. connects to a real gmail inbox over imap, read only, pulls real emails. creds come from .env, never hardcoded. if it cant connect it just returns empty and logs why, doesnt break anything

pipeline.py - runs everything in order. ingestion, extraction on the unstructured stuff, dedup, and flags which tasks count as "escalated". also does the roi math for the focus time tracker

agent_engine.py - takes the deduped list and scores each task. formula's below. writes a plain english reason for every score too so nothing's just a mystery number

planner.py - takes top 3 after scoring, lays em into 90 min deep work blocks w/ 30 min buffers between, starting 9am

main.py - fastapi backend, all the actual routes live here (get tasks, schedule, roi numbers, chat post, etc). keeps task list in memory while server's up

app.py - streamlit dashboard, talks to main.py over http, shows the queue, roi card, sla banner, schedule, chat, agent activity feed

autonomous_agent.py - own separate process. checks every few sec if theres anything OPEN + ESCALATED, if yes grabs the top one and works thru it step by step on its own, logging as it goes. this is the actual agentic part, not the dashboard buttons

## scoring formula

```
score = severity_points        (p1=4.0, p2=2.5, p3=1.0, p4=0.5)
      + deadline_points        (3.0 at <=24h left, scales down to 0 at 7+ days)
      + dependency_points      (0.5 per blocker, capped at 2.0)
      + business_impact_points (0.1 per impact pt, capped at 1.0)
```

every task gets a sentence explaining its score, so its never just a number with no context

## how "escalated" gets decided

a task counts as escalated if either:
- deadline is within 24 hrs, or
- its p1 AND the text has words like urgent/critical/production/down/outage/asap in it

reason i split these two apart - the problem statement literally calls out how engineers chase whatevers loudest instead of whats actually closest to breaching. so instead of letting that bias happen quietly, it gets called out directly

## real data

gmail's the one actual real integration. logs in over imap w/ an app password (not the real google pw) loaded from .env at runtime. if creds are missing/wrong or no internet it just fails quiet and tells u exactly what broke thru a status endpoint, dashboard shows it directly instead of pretending everythings fine

## autonomy

dashboard buttons (sync, refresh gmail, simulate p1, auto remediate) all need a human to click them. the actual autonomous piece is autonomous_agent.py, runs on its own in bg, decides by itself what needs attention (OPEN + ESCALATED), works thru it, writes logs back to the task as it goes. u can watch it happen live in the activity panel without clicking anything once its running

## stack

backend: fastapi + pydantic, state's just in memory
frontend: streamlit
real integration: gmail over imap
dedup: tf based cosine similarity, no embedding api needed
python 3.10+

## stuff id improve given more time

- task state resets if backend restarts since its in memory, would do sqlite given more time
- only gmail's actually live, rest are simulated on purpose so demo doesnt depend on 5 diff apis all working during the presentation
- dedup is just tf-cosine, works fine for obviously similar text but prob misses subtler dupes, sentence-transformers would be the next step