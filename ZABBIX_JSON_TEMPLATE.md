# Enriched Zabbix JSON Template for SEED Agent v5

Use this enriched JSON template in your Zabbix Media Type → Script (or Webhook) Message field to provide maximum context to the LLM:

## For Zabbix 5.4.9+

```json
{
  "event": {
    "id": "{EVENT.ID}",
    "value": "{EVENT.VALUE}",
    "date": "{EVENT.DATE}",
    "time": "{EVENT.TIME}",
    "r_date": "{EVENT.RECOVERY.DATE}",
    "r_time": "{EVENT.RECOVERY.TIME}"
  },
  "trigger": {
    "name": "{TRIGGER.NAME}",
    "description": "{TRIGGER.DESCRIPTION}",
    "severity_text": "{EVENT.SEVERITY}",
    "tags": "{TRIGGER.TAGS}"
  },
  "host": {
    "name": "{HOST.NAME}",
    "ip": "{HOST.IP}",
    "groups": "{HOST.GROUP.NAME}"
  },
  "item": {
    "name": "{ITEM.NAME1}",
    "key": "{ITEM.KEY1}",
    "lastvalue": "{ITEM.LASTVALUE1}",
    "id": "{ITEM.ID}",
    "port": "0"
  }
}
```

## Benefits of Enriched Template

This enriched template provides the LLM with:

1. **Event Context**: Event ID, timing, recovery information
2. **Trigger Details**: Full description and tags for better context
3. **Host Information**: IP address and host groups for infrastructure understanding
4. **Item Context**: Item key and last value for precise diagnostics

## Webhook Script Requirements

The webhook script should:
1. Accept this JSON as `argv[3]` (Zabbix 5.4+ supports this)
2. Proxy the JSON directly to SEED Agent `/zabbix` endpoint without modification
3. Let SEED Agent process and enrich the data internally

This approach gives the LLM much more context than basic alertname/severity, enabling:
- Precise command suggestions based on `item.key`
- Host-specific troubleshooting using `host.ip` and `host.groups`
- Tag-based intelligent routing and context
- Recovery time tracking and escalation logic