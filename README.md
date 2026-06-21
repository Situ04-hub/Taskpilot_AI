# TaskPilot AI

one agent. every task. zero noise.

this is my submission for the dell hackathon - taskpilot ai challenge. basically built an agent that pulls tasks from jira, servicenow, github, slack, outlook, and an actual real gmail inbox of mine, figures out what's hidden in emails/chats that never made it into a tracker, merges stuff that's duplicate across sources, ranks everything so its actually explainable not just some black box, and tells you what to work on next. theres also a background agent running that doesnt wait for you to click anything, it just goes and resolves SLA critical stuff on its own while youre doing other things.

## what it does

- pulls from 6 sources total, 5 are simulated (jira/servicenow/github/slack/outlook) and gmail is the real one, read only access
- reads through raw email and chat text and pulls out action items that arent sitting in any tracker
- merges duplicate tasks across sources
- scores every task with a formula, and every score comes with a reason attached so you can actually see why something ranked where it did
- builds a deep work schedule for your day out of the top 3 tasks
- tracks "focus time reclaimed" - counts up minutes saved every time it merges a dup or summarizes something, this was probably my favorite part to build ngl
- flags tasks separately for being loud (urgent sounding language) vs actually close to an SLA breach bc those two things arent always the same and thats kind of the whole point of the problem statement
- chat thing where you can type stuff like "whats my top priority" and itll answer using the real live task data
- separate process running in the bg that handles escalated tasks on its own, no button needed

## folder layout

```
taskpilot-ai/
  README.md
  architecture.md
  requirements.txt
  .env.example       <- copy to .env and put ur gmail creds in
  .gitignore
  models.py           <- task schema, everything gets normalized to this
  mock_data.py         <- fake jira/servicenow/github/outlook/slack stuff
  gmail_loader.py       <- the real gmail pull, imap, read only
  pipeline.py             <- ingest -> extract -> dedupe -> escalation check
  agent_engine.py           <- scoring + why explanations
  planner.py                  <- deep work schedule builder
  main.py                       <- fastapi backend, all routes
  app.py                          <- streamlit dashboard
  autonomous_agent.py               <- bg worker
  start_agent.py                      <- starts all 3 at once
```

## setup

install stuff
```
pip install -r requirements.txt
```

### real gmail (optional, skip if you dont care)

need 2FA turned on for ur google acct first, then make an app password here: https://myaccount.google.com/apppasswords

copy `.env.example` -> `.env`, fill in:
```
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=ur 16 char app password
```

.env is already gitignored so it wont get pushed by accident. if u skip this whole step the app still works fine off the simulated data, dashboard just tells u gmail isnt connected and why not.

### running it

need 3 terminals open

```
# term 1
python main.py

# term 2
streamlit run app.py

# term 3
python autonomous_agent.py
```

or just run `python start_agent.py` which does all 3 for u

then go to localhost:8501

## demo flow (matches the 7 steps from the problem statement)

1. dashboard loads, tasks already pulled in from all 6 sources
2. point at the OUTLOOK/SLACK cards, explain those came from raw text not structured fields
3. talk thru the dedup logic real quick
4. read the agent reason text on like top 3 cards
5. scroll to deep work schedule
6. ask the chat something like "whats my top priority"
7. hit simulate new p1 defect, watch it re-rank live, then point at the autonomous agent activity panel as it picks the new thing up and starts resolving it without me touching anything

## about the gmail thing

no passwords hardcoded anywhere in here. the app password only lives in a local .env that doesnt get committed. if gmail cant connect for whatever reason (no internet, wrong pw, whatever) it doesnt crash, just falls back to simulated data and tells u what broke