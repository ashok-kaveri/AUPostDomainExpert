# AU Post Sign-Off Message Flow

## Dashboard Source

`ui/pipeline_dashboard.py` → Sign Off tab
`pipeline/slack_client.py` → `SlackClient.post_signoff_message`

## Data Needed

Required:
- Release / list name (from Trello list)
- Verified cards: name + Trello URL
- Slack channel (QA provides or confirm default `SLACK_CHANNEL`)
- QA lead name
- QA explicit confirmation before send

Optional:
- Backlog bug cards: title + severity + Trello URL
- Mentions: @here, @channel, specific Slack users
- CC names

## Trello Line / List

Fetch all cards from the release list.
Include all cards by default.
If not all passed, ask QA which to include.

## Backlog Bug Prompt

Always ask before composing the final message:
"Were any Backlog bug cards raised during testing of this release? If yes, please provide the card links and severities."

Include the Backlog section only if bugs exist. Omit section cleanly if none.

## Preview Before Send

Always show the composed message to QA before sending.
Exception: if QA gives an explicit single-command like "send sign-off for <list> to #qa-channel now" — still show preview and require a short confirmation ("looks good" or "send it").

## Slack Channel

QA specifies channel name (e.g. `#au-post-qa`) or uses default.
Resolve channel name to ID using `list_slack_channels`.
Send using `SLACK_BOT_TOKEN` (not webhook URL — webhooks only work for fixed channel).

Default channel from `.env`: `SLACK_CHANNEL=C09F65XF4ER`

## Message Components

```
<mention if any> <emoji> QA Sign-Off — <Release Name>

The following cards have been verified and are ready for release:

✅ <Card Name> — <URL>
✅ <Card Name> — <URL>

🐛 Backlog Bugs Raised:   ← omit section if no bugs
• <Bug Title> (P<N>) — <URL>

QA: <QA Lead Name>
```

## After Send

Report:
- Slack channel name/ID
- Message timestamp
- Any send errors
