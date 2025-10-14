# Example: Request Logging Output

This document shows example log entries from the AWS MCP Server.

## Successful AWS CLI Command

**Tool Call**: `aws_cli_pipeline`  
**Command**: `aws s3 ls`  
**Status**: Success

```json
{
  "timestamp": "2025-10-14T15:30:45.123Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws s3 ls",
    "timeout": null
  },
  "output": {
    "status": "success",
    "output": "2025-10-14 12:00:00 my-bucket-1\n2025-10-14 13:00:00 my-bucket-2\n2025-10-14 14:00:00 test-bucket"
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

## Command with Unix Pipe

**Tool Call**: `aws_cli_pipeline`  
**Command**: `aws s3 ls | grep test`  
**Status**: Success

```json
{
  "timestamp": "2025-10-14T15:31:20.456Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws s3 ls | grep test",
    "timeout": null
  },
  "output": {
    "status": "success",
    "output": "2025-10-14 14:00:00 test-bucket"
  },
  "status": "success",
  "duration_ms": 923.45,
  "error": null,
  "metadata": {
    "server": "aws-mcp-server",
    "has_pipe": true
  }
}
```

## Failed Command (Validation Error)

**Tool Call**: `aws_cli_pipeline`  
**Command**: `aws s3api get-bucket-location --bucket nonexistent-bucket-12345`  
**Status**: Error

```json
{
  "timestamp": "2025-10-14T15:32:10.789Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws s3api get-bucket-location --bucket nonexistent-bucket-12345",
    "timeout": null
  },
  "output": {
    "status": "error",
    "output": "Command execution error: An error occurred (NoSuchBucket) when calling the GetBucketLocation operation: The specified bucket does not exist"
  },
  "status": "error",
  "duration_ms": 423.12,
  "error": "Command execution error: An error occurred (NoSuchBucket) when calling the GetBucketLocation operation: The specified bucket does not exist",
  "metadata": {
    "server": "aws-mcp-server",
    "has_pipe": false
  }
}
```

## Help Command

**Tool Call**: `aws_cli_help`  
**Service**: `s3`  
**Command**: `ls`  
**Status**: Success

```json
{
  "timestamp": "2025-10-14T15:33:00.234Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_help",
  "input": {
    "service": "s3",
    "command": "ls"
  },
  "output": {
    "help_text": "NAME\n       ls -\n\nDESCRIPTION\n       List S3 objects and common prefixes under a prefix or all S3 buck-\n       ets. Note that the --output and --no-paginate arguments are ignored\n       for this command.\n\nSYNOPSIS\n            ls\n          <S3Uri> or NONE\n          [--recursive]\n          [--page-size <value>]\n          [--human-readable]\n          [--summarize]\n          [--request-payer <value>]"
  },
  "status": "success",
  "duration_ms": 234.56,
  "error": null,
  "metadata": {
    "server": "aws-mcp-server"
  }
}
```

## Command with Custom Timeout

**Tool Call**: `aws_cli_pipeline`  
**Command**: `aws ec2 describe-instances`  
**Timeout**: 60 seconds  
**Status**: Success

```json
{
  "timestamp": "2025-10-14T15:34:15.678Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws ec2 describe-instances",
    "timeout": 60
  },
  "output": {
    "status": "success",
    "output": "{\n    \"Reservations\": [\n        {\n            \"Groups\": [],\n            \"Instances\": [\n                {\n                    \"InstanceId\": \"i-0123456789abcdef0\",\n                    \"InstanceType\": \"t2.micro\",\n                    \"State\": {\n                        \"Name\": \"running\"\n                    }\n                }\n            ]\n        }\n    ]\n}"
  },
  "status": "success",
  "duration_ms": 1523.89,
  "error": null,
  "metadata": {
    "server": "aws-mcp-server",
    "has_pipe": false
  }
}
```

## Complex Piped Command

**Tool Call**: `aws_cli_pipeline`  
**Command**: `aws ec2 describe-instances | jq '.Reservations[].Instances[] | {id: .InstanceId, state: .State.Name}' | grep running`  
**Status**: Success

```json
{
  "timestamp": "2025-10-14T15:35:30.901Z",
  "event_type": "mcp_tool_call",
  "tool_name": "aws_cli_pipeline",
  "input": {
    "command": "aws ec2 describe-instances | jq '.Reservations[].Instances[] | {id: .InstanceId, state: .State.Name}' | grep running",
    "timeout": null
  },
  "output": {
    "status": "success",
    "output": "{\n  \"id\": \"i-0123456789abcdef0\",\n  \"state\": \"running\"\n}\n{\n  \"id\": \"i-abcdef0123456789\",\n  \"state\": \"running\"\n}"
  },
  "status": "success",
  "duration_ms": 2134.67,
  "error": null,
  "metadata": {
    "server": "aws-mcp-server",
    "has_pipe": true
  }
}
```

## Tips for Reading Logs

1. **Filter by status**: Use `jq` or `grep` to find errors:
   ```bash
   grep '"status": "error"' requests.log
   cat requests.log | jq 'select(.status == "error")'
   ```

2. **Calculate average duration**:
   ```bash
   cat requests.log | jq '.duration_ms' | awk '{sum+=$1; count++} END {print "Average:", sum/count, "ms"}'
   ```

3. **Count requests by tool**:
   ```bash
   cat requests.log | jq -r '.tool_name' | sort | uniq -c
   ```

4. **Find slow requests** (>1000ms):
   ```bash
   cat requests.log | jq 'select(.duration_ms > 1000)'
   ```

5. **View formatted JSON**:
   ```bash
   tail -1 requests.log | jq '.'
   ```
