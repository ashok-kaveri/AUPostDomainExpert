# AU Post Slack Operations Reference

## Project Helpers

Available in `pipeline/slack_client.py`:
- `search_slack_users(name)` — search by display name or real name
- `list_slack_channels()` — list visible channels with IDs
- `post_content_to_slack_channel(channel_id, text, thread_ts=None)`
- `send_dm_to_user(user_id, text)` — send direct message by Slack user ID
- `send_dm_by_name(name, text)` — search then send DM

## Required Slack Bot Scopes

```
users:read          — search users
channels:read       — list public channels
groups:read         — list private channels
channels:history    — read public channel messages
groups:history      — read private channel messages
im:write            — open DM conversations
chat:write          — send messages
files:write         — upload files if needed
```

## Channel Names and IDs

- APIs require channel IDs, not names
- Use `list_slack_channels()` to get IDs
- Match by exact name without `#` prefix
- Default channel: `SLACK_CHANNEL=C09F65XF4ER` from `.env`

## Reading Messages

Fetch recent messages from a channel with a limit (default 20).
For threads: provide `thread_ts` (timestamp string from original message).

## Sending Messages

Rules:
- Never send if QA only asked to draft
- Always search users before sending a DM — do not guess user IDs
- Preserve `thread_ts` for replies
- For sign-off messages: always preview before sending

## DM By Name Flow

```
1. search_slack_users(name)
2. If multiple matches → show options to QA
3. If one match → confirm with QA
4. send_dm_to_user(user_id, message)
5. Report: Slack username, user_id, timestamp, status
```

## Message Style For QA Operations

Keep messages concise and professional:

```
Hi <name>, 

QA is testing card: <card name>
Trello: <card URL>

<Request or question>

— AU Post QA
```

For sign-off messages → use `aupost-signoff-message` skill format.

## Error Handling

Common errors:
- `channel_not_found` → confirm channel ID with QA
- `not_in_channel` → bot needs to be added to the channel
- `user_not_found` → try different name spelling or ask QA for Slack ID
- `missing_scope` → check bot OAuth scopes in Slack app settings
