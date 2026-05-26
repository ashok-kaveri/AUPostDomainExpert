---
name: aupost-signoff-message
description: Use inside AUPostDomainExpert when QA asks Claude to prepare or send the final QA sign-off message for a Trello release/list/line. Fetch all cards from the Trello line, prepare the dashboard-style Slack sign-off message, ask QA for any Backlog bug links if bugs were created, review the message with QA, and send to the Slack channel only after QA provides the channel and explicitly confirms.
---

# AU Post Sign-Off Message

Use this skill to prepare and send the QA sign-off message for an AU Post release.

## Flow

1. Identify the Trello list/release name from QA
2. Fetch all cards from that list using `aupost-trello-operator`
3. Prepare the verified cards list
4. Ask QA: "Were any Backlog bug cards raised during testing? If yes, please provide the links."
5. Ask QA for: Slack channel, any mentions (@here / @channel / specific person), QA lead name
6. Compose message and show preview
7. Send to Slack only after QA explicitly confirms

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-signoff-message/references/signoff_flow.md`
3. Use `aupost-trello-operator` to fetch cards
4. Use `aupost-slack-operator` to send the message

## Message Format

```
<!here> ✅ QA Sign-Off — <Release Name>

The following cards have been verified and are ready for release:

✅ <Card Name> — <Trello Card URL>
✅ <Card Name> — <Trello Card URL>
...

<If bugs exist:>
🐛 Backlog Bugs Raised:
• <Bug Title> (P<N>) — <Trello Backlog Card URL>
• ...

QA: <QA Lead Name>
```

## Mention Handling

| User writes | Convert to |
|---|---|
| `here` | `<!here>` |
| `channel` | `<!channel>` |
| Slack user ID | `<@ID>` |
| Person's name | search Slack for user, use `<@ID>` |

## Required Before Sending

- Trello list identified and cards fetched ✅
- Backlog bugs asked about (include even if none) ✅
- QA confirmed Slack channel ✅
- QA explicitly confirmed message content ✅

## Channel Resolution

QA specifies the channel name or ID.
Use `aupost-slack-operator` to resolve channel name → ID and to send the message — this skill has no direct Slack send logic; all Slack sends delegate to `aupost-slack-operator`.
Requires `SLACK_BOT_TOKEN` from `.env`.

Configured default channel: `SLACK_CHANNEL` in `.env` (ID: `C09F65XF4ER`)

**SLACK_WEBHOOK_URL caveat**: The webhook only posts to its single fixed channel. For any other channel, use `SLACK_BOT_TOKEN` via `aupost-slack-operator`.

## Do Not

- Do not send without explicit QA confirmation
- Do not guess the Slack channel — always confirm
- Do not skip the Backlog bug prompt — always ask even if QA says there are none
- Do not include cards that QA says did not pass — ask which cards to include
