# Zabbix Webhook Troubleshooting Guide

## Error: Invalid JSON (12 characters)

This error indicates that the JSON data being passed to the webhook is either truncated, malformed, or not being passed correctly from Zabbix.

### Immediate Diagnostic Steps

1. **Test the webhook script locally first:**
   ```bash
   cd v5/
   python3 ../test-zabbix-webhook.py http://p-dba-seed-adv-msk01:8080
   ```

2. **Check what Zabbix is actually sending:**
   The 12-character length suggests the data is severely truncated. Add logging to see the raw data:
   ```bash
   # Run with improved debugging
   python3 zabbix-webhook-enriched.py "http://p-dba-seed-adv-msk01:8080/zabbix" '{"test": "data"}'
   ```

### Common Causes and Solutions

#### 1. **Zabbix Configuration Issues**

**Problem**: Zabbix Media Type not configured correctly
- Check that the Message template in Zabbix Media Type contains the full enriched JSON
- Verify that the Script parameters include the complete JSON

**Solution**: Update Zabbix Media Type → Script → Message field with:
```json
{
  "event": {
    "id": "{EVENT.ID}",
    "value": "{EVENT.VALUE}",
    "date": "{EVENT.DATE}",
    "time": "{EVENT.TIME}"
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
    "id": "{ITEM.ID}"
  }
}
```

#### 2. **Script Parameter Issues**

**Problem**: Script parameters in wrong order
- Zabbix passes parameters as `{ALERT.SENDTO}`, `{ALERT.SUBJECT}`, `{ALERT.MESSAGE}`
- For Script media type, the JSON should be in `{ALERT.MESSAGE}`

**Solution**: Configure Zabbix Script parameters as:
1. Parameter 1: `http://p-dba-seed-adv-msk01:8080/zabbix`
2. Parameter 2: `{ALERT.MESSAGE}` (contains the JSON template)

#### 3. **Character Encoding/Escaping**

**Problem**: Special characters in JSON are breaking the parsing
- Cyrillic characters in trigger names/descriptions
- Quotes not properly escaped

**Solution**: Test with a simple English-only JSON first:
```bash
python3 zabbix-webhook-enriched.py '{"event":{"value":"1"},"trigger":{"name":"Test Alert"},"host":{"name":"testhost"}}'
```

#### 4. **Argument Parsing Issues**

**Problem**: Shell argument parsing is truncating the JSON
- JSON contains characters that shell interprets specially
- Missing proper quoting

**Solution**: Ensure proper quoting when calling the script:
```bash
# Correct - single quotes around entire JSON
python3 zabbix-webhook-enriched.py 'http://host:8080/zabbix' '{"event":{"value":"1"}}'

# Incorrect - shell will break on spaces/special chars
python3 zabbix-webhook-enriched.py http://host:8080/zabbix {"event":{"value":"1"}}
```

### Debugging Steps

1. **Enable verbose logging in Zabbix:**
   ```bash
   # Check Zabbix server logs
   tail -f /var/log/zabbix/zabbix_server.log | grep -i script
   ```

2. **Test webhook manually with curl:**
   ```bash
   curl -X POST http://p-dba-seed-adv-msk01:8080/zabbix \
     -H 'Content-Type: application/json' \
     -d '{"event":{"value":"1"},"trigger":{"name":"Manual Test"},"host":{"name":"testhost"}}'
   ```

3. **Check SEED Agent logs:**
   ```bash
   tail -f seed-agent.log | grep zabbix
   ```

4. **Run the test script:**
   ```bash
   python3 test-zabbix-webhook.py http://p-dba-seed-adv-msk01:8080
   ```

### Quick Fixes

#### Minimal Working Example
Create a minimal Zabbix Media Type for testing:

**Script name**: `zabbix-webhook-enriched.py`
**Script parameters**:
1. `http://p-dba-seed-adv-msk01:8080/zabbix`
2. `{"event":{"id":"{EVENT.ID}","value":"{EVENT.VALUE}"},"trigger":{"name":"{TRIGGER.NAME}","severity_text":"{EVENT.SEVERITY}"},"host":{"name":"{HOST.NAME}","ip":"{HOST.IP}"}}`

#### Test with Static JSON
If dynamic macros are causing issues, test with static JSON first:
```bash
python3 zabbix-webhook-enriched.py "http://p-dba-seed-adv-msk01:8080/zabbix" '{"event":{"id":"123","value":"1"},"trigger":{"name":"Static Test Alert","severity_text":"High"},"host":{"name":"test-server","ip":"192.168.1.1"}}'
```

### Expected Output
When working correctly, you should see:
```
[INFO] SEED URL: http://p-dba-seed-adv-msk01:8080/zabbix
[INFO] JSON data length: 150+ characters
[DEBUG] Raw JSON data: '{"event":{"id":"123",...
[INFO] Parsed JSON payload with 4 top-level keys
[DEBUG] Enriched payload preview:
  Event: 123
  Trigger: Test Alert
  Host: test-server
  Item key: N/A
[SUCCESS] Alert sent to SEED Agent: 200
```

### If All Else Fails
Fall back to the basic webhook script:
```bash
python3 zabbix-webhook-5.4.py "http://p-dba-seed-adv-msk01:8080/zabbix" '{"event":{"value":"1"},"trigger":{"name":"Test"},"host":{"name":"test"}}'
```