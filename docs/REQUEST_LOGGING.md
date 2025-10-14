# Request Logging for AWS MCP Server

## Overview

The AWS MCP Server now includes comprehensive request logging that captures all tool invocations, inputs, and outputs in a structured JSON format suitable for ingestion into Splunk and other log analysis tools.

## Log File Location

All requests are logged to `requests.log` in the working directory where the server is started.

## Log Format

Each log entry is a single line of JSON (JSONL format) with the following structure:

```json
{
  "timestamp": "2025-10-14T12:34:56.789Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws s3api list-buckets",
    "timeout": null
  },
  "output": {
    "status": "success",
    "output": "{\n  \"Buckets\": [\n    ...\n  ]\n}"
  },
  "status": "success",
  "duration_ms": 1234.56,
  "error": null,
  "metadata": {
    "server": "aws-mcp-server",
    "has_pipe": false
  }
}
```

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp in UTC (ends with 'Z') |
| `event_type` | string | Always "mcp_tool_call" for tool invocations |
| `tool_name` | string | Name of the MCP tool that was called |
| `input` | object | Input parameters passed to the tool |
| `output` | object | Output returned from the tool |
| `status` | string | Operation status: "success", "error", or "warning" |
| `duration_ms` | number | Duration of the operation in milliseconds |
| `error` | string/null | Error message if the operation failed |
| `metadata` | object | Additional context about the request |

## Splunk Integration

### Ingestion Setup

1. **File Monitor Input**: Configure Splunk to monitor the `requests.log` file:

```ini
[monitor://path/to/requests.log]
sourcetype = _json
index = aws_mcp
```

2. **HTTP Event Collector (HEC)**: Alternatively, you can send logs to Splunk via HEC by modifying the `request_logger.py` to use the Splunk SDK.

### Sample Splunk Queries

#### Find all failed requests
```spl
index=aws_mcp status=error
| table timestamp tool_name input.command error
```

#### Average duration by tool
```spl
index=aws_mcp
| stats avg(duration_ms) as avg_duration by tool_name
| sort -avg_duration
```

#### Request rate over time
```spl
index=aws_mcp
| timechart count by tool_name
```

#### Commands with pipes
```spl
index=aws_mcp tool_name=aws_cli_pipeline metadata.has_pipe=true
| table timestamp input.command duration_ms status
```

#### Top slowest commands
```spl
index=aws_mcp
| sort -duration_ms
| head 20
| table timestamp tool_name input.command duration_ms status
```

## Log Rotation

To prevent the log file from growing indefinitely, consider implementing log rotation using:

### Linux/macOS - logrotate

Create `/etc/logrotate.d/aws-mcp-server`:

```
/path/to/requests.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
}
```

### Windows - PowerShell script

```powershell
$logFile = "requests.log"
$maxSize = 100MB

if ((Get-Item $logFile).Length -gt $maxSize) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Move-Item $logFile "requests-$timestamp.log"
    Compress-Archive "requests-$timestamp.log" "requests-$timestamp.zip"
    Remove-Item "requests-$timestamp.log"
}
```

## Privacy and Security Considerations

The request logs may contain sensitive information such as:
- AWS credentials (if passed as parameters)
- Resource names and IDs
- Command outputs with potentially sensitive data

### Recommendations:

1. **Secure the log file**: Ensure proper file permissions
   ```bash
   chmod 600 requests.log
   ```

2. **Consider log sanitization**: Modify `request_logger.py` to redact sensitive fields

3. **Encrypt logs at rest**: Use disk encryption for the log directory

4. **Secure transmission**: If sending to Splunk, use TLS/SSL

5. **Implement retention policies**: Delete old logs after a specific period

## Customization

You can customize the logging behavior by modifying `src/aws_mcp_server/request_logger.py`:

- Change the log file location
- Add custom metadata fields
- Filter certain types of requests
- Modify the sanitization logic
- Add encryption or compression

## Troubleshooting

### Log file not created
- Ensure write permissions in the working directory
- Check server logs for initialization errors

### Missing entries
- Verify the server is running with the updated code
- Check for exceptions in the server logs

### Large log files
- Implement log rotation (see above)
- Consider reducing log verbosity for high-frequency operations

## Example Log Entries

### Successful command execution
```json
{
  "timestamp": "2025-10-14T12:00:00.000Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws s3 ls",
    "timeout": null
  },
  "output": {
    "status": "success",
    "output": "2025-10-14 12:00:00 my-bucket-1\n2025-10-14 12:00:00 my-bucket-2"
  },
  "status": "success",
  "duration_ms": 856.32,
  "error": null,
  "metadata": {
    "server": "aws-mcp-server",
    "has_pipe": false
  }
}
```

### Failed command with error
```json
{
  "timestamp": "2025-10-14T12:01:00.000Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws s3api get-bucket-location --bucket nonexistent",
    "timeout": null
  },
  "output": {
    "status": "error",
    "output": "Command execution error: NoSuchBucket"
  },
  "status": "error",
  "duration_ms": 423.12,
  "error": "Command execution error: NoSuchBucket",
  "metadata": {
    "server": "aws-mcp-server",
    "has_pipe": false
  }
}
```

### Help command
```json
{
  "timestamp": "2025-10-14T12:02:00.000Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_help",
  "input": {
    "service": "s3",
    "command": "ls"
  },
  "output": {
    "help_text": "NAME\n       ls -\n\nDESCRIPTION\n..."
  },
  "status": "success",
  "duration_ms": 234.56,
  "error": null,
  "metadata": {
    "server": "aws-mcp-server"
  }
}
```
