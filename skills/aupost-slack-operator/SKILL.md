---
name: aupost-slack-operator
description: Use inside AUPostDomainExpert when the user asks Claude to work with Slack using project .env credentials: search Slack users, list channels, fetch messages from any visible channel, read a thread, send a channel message, reply in a Slack thread, send a DM to a user by name or ID, or coordinate with Trello developer assignment. Requires explicit user intent before any Slack send.
---

# AU Post Slack Operator

Use this skill for Slack operations inside the AUPostDomainExpert project.

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Load `.env` from `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/.env`
3. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-slack-operator/references/slack_ops.md`

## Credentials

From project `.env`:
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL` (default channel ID: `C09F65XF4ER`)
- `SLACK_WEBHOOK_URL` (webhook — only works for configured channel)

## Read Tasks (allowed freely)

- Search Slack users by name
- List visible channels
- Fetch recent messages from a channel
- Read a thread by timestamp
- Search for a user profile

## Write Tasks (require explicit user intent)

Clear user intent required:
- Send a channel message
- Reply in a thread
- Send a DM to a user by name or ID

## Common Operations

| Operation | How |
|---|---|
| Search users | `search_slack_users(name)` — returns ID, display name, real name |
| List channels | `list_slack_channels()` — returns name + ID pairs |
| Read channel messages | fetch recent messages with limit parameter |
| Read thread | fetch with `thread_ts` |
| Send channel message | `post_content_to_slack_channel(channel_id, text)` |
| Send DM | `send_dm_to_user(user_id, text)` |
| Send DM by name | search user → get ID → send DM |
| Reply in thread | post with `thread_ts` |

## Trello Developer DM Flow

When QA asks to notify a developer about a card:
1. Get developer names from `aupost-trello-operator`
2. Search Slack for each developer name
3. Match user by display name or real name
4. Send concise DM with: card name, Trello URL, request/question
5. Report: recipient, Slack user ID, message timestamp or error

## Output Format

**For reads**: summarize with channel/user/timestamp/sender/text/thread_ts
**For writes**: return recipient + channel + timestamp + status

## Message Style

Concise QA language. Include:
- Card name
- Trello card URL
- Issue or request
- Evidence if relevant (screenshot path, JSON field, verdict)

## Required Slack Scopes

`users:read`, `channels:read`, `groups:read`, `channels:history`, `groups:history`, `im:write`, `chat:write`, `files:write`

## Do Not

- Do not send any message unless user explicitly asks to send/post/DM
- Do not assume a channel — always confirm or use `SLACK_CHANNEL` default
- Do not expose SLACK_BOT_TOKEN in output
