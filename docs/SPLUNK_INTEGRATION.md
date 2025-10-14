# Splunk Integration Guide for AWS MCP Server Logs

This guide provides step-by-step instructions for integrating AWS MCP Server request logs with Splunk.

## Prerequisites

- Splunk Enterprise or Splunk Cloud instance
- Access to configure data inputs
- AWS MCP Server running and generating logs

## Method 1: File Monitor (Recommended for Local Splunk)

### Step 1: Configure Splunk to Monitor the Log File

1. **Log into Splunk Web** at http://your-splunk-server:8000

2. **Navigate to Settings → Data Inputs → Files & Directories**

3. **Click "New Local File & Directory"**

4. **Configure the monitor**:
   - **File or Directory**: Enter the full path to `requests.log`
     - Example: `/path/to/aws-mcp-server/requests.log`
     - Windows: `C:\path\to\aws-mcp-server\requests.log`
   - **Continuously monitor**: Yes (checked)

5. **Set Source Type**:
   - **Source type**: `_json` (for automatic JSON parsing)
   - Or create custom source type: `aws_mcp_logs`

6. **Input Settings**:
   - **Host**: Use the hostname where MCP server runs
   - **Index**: Create or select an index (e.g., `aws_mcp`)

7. **Review and Submit**

### Step 2: Configure inputs.conf (Alternative)

Edit `$SPLUNK_HOME/etc/system/local/inputs.conf`:

```ini
[monitor:///path/to/aws-mcp-server/requests.log]
disabled = false
index = aws_mcp
sourcetype = _json
host = mcp-server-host
```

Restart Splunk:
```bash
$SPLUNK_HOME/bin/splunk restart
```

## Method 2: HTTP Event Collector (HEC)

### Step 1: Enable and Configure HEC in Splunk

1. **Navigate to Settings → Data Inputs → HTTP Event Collector**

2. **Click "Global Settings"**:
   - Enable "All tokens"
   - Set HTTP Port (default: 8088)
   - Enable SSL (recommended)

3. **Create a new token**:
   - Click "New Token"
   - Name: `aws-mcp-server`
   - Source type: `_json`
   - Index: `aws_mcp`
   - Copy the token value

### Step 2: Modify request_logger.py for HEC

Add this method to the `RequestLogger` class:

```python
import requests

def log_request_to_splunk_hec(self, log_entry: Dict[str, Any]):
    """Send log entry to Splunk HEC."""
    hec_url = "https://your-splunk-server:8088/services/collector"
    hec_token = "your-hec-token-here"
    
    headers = {
        "Authorization": f"Bearer {hec_token}",
        "Content-Type": "application/json"
    }
    
    # Format for HEC
    hec_event = {
        "event": log_entry,
        "sourcetype": "_json",
        "index": "aws_mcp"
    }
    
    try:
        response = requests.post(
            hec_url,
            json=hec_event,
            headers=headers,
            verify=True  # Set to False for self-signed certs (not recommended)
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send to Splunk HEC: {e}")
```

## Method 3: Splunk Universal Forwarder

### Step 1: Install Universal Forwarder

Download from: https://www.splunk.com/en_us/download/universal-forwarder.html

**Linux/macOS**:
```bash
wget -O splunkforwarder.tgz 'https://download.splunk.com/...'
tar xvzf splunkforwarder.tgz -C /opt
/opt/splunkforwarder/bin/splunk start --accept-license
```

**Windows**:
- Run the installer
- Follow the installation wizard
- Start the forwarder service

### Step 2: Configure Forwarder

Edit `$SPLUNK_FORWARDER_HOME/etc/system/local/inputs.conf`:

```ini
[monitor:///path/to/requests.log]
disabled = false
index = aws_mcp
sourcetype = _json
```

Configure forwarding to your Splunk indexer:

```bash
$SPLUNK_FORWARDER_HOME/bin/splunk add forward-server your-splunk-server:9997
$SPLUNK_FORWARDER_HOME/bin/splunk restart
```

## Field Extraction (If Not Using _json Sourcetype)

If you're not using `_json` sourcetype, configure field extraction:

### props.conf
```ini
[aws_mcp_logs]
KV_MODE = json
TIME_PREFIX = "timestamp":"
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3NZ
SHOULD_LINEMERGE = false
LINE_BREAKER = ([\r\n]+)
```

## Useful Splunk Queries

### Dashboard Searches

#### 1. Request Rate Over Time
```spl
index=aws_mcp
| timechart span=1h count by tool_name
```

#### 2. Error Rate
```spl
index=aws_mcp
| timechart span=1h count by status
```

#### 3. Average Duration by Tool
```spl
index=aws_mcp
| stats avg(duration_ms) as avg_duration by tool_name
| sort -avg_duration
```

#### 4. Top 10 Slowest Requests
```spl
index=aws_mcp
| sort -duration_ms
| head 10
| table timestamp tool_name input.command duration_ms status
```

#### 5. Failed Requests
```spl
index=aws_mcp status=error
| table timestamp tool_name input.command error
| sort -timestamp
```

#### 6. Piped Commands Performance
```spl
index=aws_mcp tool_name=aws_cli_pipeline metadata.has_pipe=true
| stats avg(duration_ms) as avg_duration count by metadata.has_pipe
```

#### 7. Request Distribution
```spl
index=aws_mcp
| stats count by tool_name
| eval percent=round((count/sum(count)*100),2)
| fields tool_name count percent
```

## Creating a Dashboard

### Step 1: Create Search
Run any of the searches above in Splunk Web.

### Step 2: Save as Dashboard Panel
Click **Save As → Dashboard Panel**

### Example Dashboard XML

```xml
<dashboard>
  <label>AWS MCP Server Monitoring</label>
  <row>
    <panel>
      <title>Request Rate</title>
      <chart>
        <search>
          <query>index=aws_mcp | timechart span=1h count by tool_name</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">column</option>
      </chart>
    </panel>
  </row>
  <row>
    <panel>
      <title>Error Rate</title>
      <chart>
        <search>
          <query>index=aws_mcp | timechart span=1h count by status</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">area</option>
      </chart>
    </panel>
  </row>
  <row>
    <panel>
      <title>Average Duration</title>
      <table>
        <search>
          <query>index=aws_mcp | stats avg(duration_ms) as avg_duration by tool_name | sort -avg_duration</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
      </table>
    </panel>
  </row>
  <row>
    <panel>
      <title>Recent Errors</title>
      <table>
        <search>
          <query>index=aws_mcp status=error | table timestamp tool_name error | head 10</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
      </table>
    </panel>
  </row>
</dashboard>
```

## Alerting

### Create Alert for High Error Rate

1. **Navigate to Settings → Searches, Reports, and Alerts**

2. **Create New Alert**:
   - **Title**: AWS MCP High Error Rate
   - **Search**:
     ```spl
     index=aws_mcp
     | bucket _time span=5m
     | stats count(eval(status="error")) as errors, count as total by _time
     | eval error_rate=round((errors/total)*100,2)
     | where error_rate > 10
     ```
   - **Time Range**: Last 15 minutes
   - **Schedule**: Every 5 minutes
   - **Trigger**: Number of results is greater than 0
   - **Actions**: Email, Slack, PagerDuty, etc.

### Alert for Slow Requests

```spl
index=aws_mcp duration_ms > 5000
| table timestamp tool_name input.command duration_ms
```

## Log Retention and Management

### Configure Index Retention

Edit `$SPLUNK_HOME/etc/system/local/indexes.conf`:

```ini
[aws_mcp]
homePath = $SPLUNK_DB/aws_mcp/db
coldPath = $SPLUNK_DB/aws_mcp/colddb
thawedPath = $SPLUNK_DB/aws_mcp/thaweddb
maxTotalDataSizeMB = 512000
frozenTimePeriodInSecs = 2592000  # 30 days
```

## Troubleshooting

### Logs Not Appearing in Splunk

1. **Check file permissions**:
   ```bash
   ls -la requests.log
   ```
   Ensure Splunk user can read the file.

2. **Verify input is active**:
   ```bash
   $SPLUNK_HOME/bin/splunk list input
   ```

3. **Check Splunk logs**:
   ```bash
   tail -f $SPLUNK_HOME/var/log/splunk/splunkd.log
   ```

### Field Extraction Issues

Test JSON parsing in Splunk:
```spl
index=aws_mcp
| head 1
| spath
```

### High Data Volume

If logs are too verbose:
1. Implement sampling in `request_logger.py`
2. Filter in Splunk with transforms.conf
3. Increase log rotation frequency

## Best Practices

1. **Use dedicated index**: Keep MCP logs separate
2. **Enable compression**: Configure in indexes.conf
3. **Set appropriate retention**: Based on compliance needs
4. **Create data models**: For accelerated searches
5. **Use summary indexing**: For long-term trends
6. **Implement role-based access**: Restrict sensitive data
7. **Regular monitoring**: Set up alerts for anomalies
8. **Backup configurations**: Version control your configs

## Resources

- [Splunk Documentation](https://docs.splunk.com/)
- [HTTP Event Collector](https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector)
- [Universal Forwarder](https://docs.splunk.com/Documentation/Forwarder/latest/Forwarder/Abouttheuniversalforwarder)
- [Search Reference](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference)
