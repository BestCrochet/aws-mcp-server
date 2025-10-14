"""Main server implementation for AWS MCP Server.

This module defines the MCP server instance and tool functions for AWS CLI interaction,
providing a standardized interface for AWS CLI command execution and documentation.
It also provides MCP Resources for AWS profiles, regions, and configuration.
"""

import asyncio
import logging
import sys
import time

from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from aws_mcp_server import __version__
from aws_mcp_server.cli_executor import (
    CommandExecutionError,
    CommandHelpResult,
    CommandResult,
    CommandValidationError,
    check_aws_cli_installed,
    execute_aws_command,
    get_command_help,
)
from aws_mcp_server.config import INSTRUCTIONS
from aws_mcp_server.prompts import register_prompts
from aws_mcp_server.resources import register_resources
from aws_mcp_server.tools import make_request
from aws_mcp_server.request_logger import get_request_logger

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stderr)])
logger = logging.getLogger("aws-mcp-server")

# Initialize request logger
request_logger = get_request_logger()
logger.info(f"Request logging initialized. Logs will be written to: requests.log")


# Run startup checks in synchronous context
def run_startup_checks():
    """Run startup checks to ensure AWS CLI is installed."""
    logger.info("Running startup checks...")
    if not asyncio.run(check_aws_cli_installed()):
        logger.error("AWS CLI is not installed or not in PATH. Please install AWS CLI.")
        sys.exit(1)
    logger.info("AWS CLI is installed and available")


# Call the checks
run_startup_checks()

# Create the FastMCP server following FastMCP best practices
mcp = FastMCP(
    "AWS MCP Server",
    instructions=INSTRUCTIONS,
    host="0.0.0.0",
    # version=__version__,
    # capabilities={"resources": {}},  # Enable resources capability
)

# Register prompt templates
register_prompts(mcp)

# Register AWS resources
register_resources(mcp)


@mcp.tool()
async def aws_cli_help(
    service: str = Field(description="AWS service (e.g., s3, ec2)"),
    command: str | None = Field(description="Command within the service", default=None),
    ctx: Context | None = None,
) -> CommandHelpResult:
    """Get AWS CLI command documentation.

    Retrieves the help documentation for a specified AWS service or command
    by executing the 'aws <service> [command] help' command.

    Returns:
        CommandHelpResult containing the help text
    """
    start_time = time.time()
    input_params = {"service": service, "command": command}
    error_msg = None
    status = "success"
    result = CommandHelpResult(help_text="")  # Initialize with default
    
    logger.info(f"Getting documentation for service: {service}, command: {command or 'None'}")

    try:
        if ctx:
            await ctx.info(f"Fetching help for AWS {service} {command or ''}")

        # Reuse the get_command_help function from cli_executor
        result = await get_command_help(service, command)
    except Exception as e:
        logger.error(f"Error in aws_cli_help: {e}")
        error_msg = str(e)
        status = "error"
        result = CommandHelpResult(help_text=f"Error retrieving help: {str(e)}")
    finally:
        duration_ms = (time.time() - start_time) * 1000
        request_logger.log_request(
            tool_name="aws_cli_help",
            input_params=input_params,
            output=result,
            status=status,
            duration_ms=duration_ms,
            error=error_msg,
            metadata={"server": "aws-mcp-server"},
        )
    
    return result


@mcp.tool()
async def aws_cli_pipeline(
    command: str = Field(description="Complete AWS CLI command to execute (can include pipes with Unix commands)"),
    timeout: int | None = Field(description="Timeout in seconds (defaults to AWS_MCP_TIMEOUT)", default=None),
    ctx: Context | None = None,
) -> CommandResult:
    """Execute an AWS CLI command, optionally with Unix command pipes.

    Validates, executes, and processes the results of an AWS CLI command,
    handling errors and formatting the output for better readability.

    The command can include Unix pipes (|) to filter or transform the output,
    similar to a regular shell. The first command must be an AWS CLI command,
    and subsequent piped commands must be basic Unix utilities.

    Supported Unix commands in pipes:
    - File operations: ls, cat, cd, pwd, cp, mv, rm, mkdir, touch, chmod, chown
    - Text processing: grep, sed, awk, cut, sort, uniq, wc, head, tail, tr, find
    - System tools: ps, top, df, du, uname, whoami, date, which, echo
    - Network tools: ping, ifconfig, netstat, curl, wget, dig, nslookup, ssh, scp
    - Other utilities: man, less, tar, gzip, zip, xargs, jq, tee

    Examples:
    - aws s3api list-buckets --query 'Buckets[*].Name' --output text
    - aws s3api list-buckets --query 'Buckets[*].Name' --output text | sort
    - aws ec2 describe-instances | grep InstanceId | wc -l

    Returns:
        CommandResult containing output and status
    """
    start_time = time.time()
    input_params = {"command": command, "timeout": timeout}
    error_msg = None
    status = "success"
    result = CommandResult(status="error", output="")  # Initialize with default
    
    logger.info(f"Executing command: {command}" + (f" with timeout: {timeout}" if timeout else ""))

    try:
        if ctx:
            is_pipe = "|" in command
            message = "Executing" + (" piped" if is_pipe else "") + " AWS CLI command"
            await ctx.info(message + (f" with timeout: {timeout}s" if timeout else ""))

        cmd_result = await execute_aws_command(command, timeout)

        # Format the output for better readability
        if cmd_result["status"] == "success":
            if ctx:
                await ctx.info("Command executed successfully")
            status = "success"
        else:
            if ctx:
                await ctx.warning("Command failed")
            status = "error"

        result = CommandResult(status=cmd_result["status"], output=cmd_result["output"])
    except CommandValidationError as e:
        logger.warning(f"Command validation error: {e}")
        error_msg = f"Command validation error: {str(e)}"
        status = "error"
        result = CommandResult(status="error", output=error_msg)
    except CommandExecutionError as e:
        logger.warning(f"Command execution error: {e}")
        error_msg = f"Command execution error: {str(e)}"
        status = "error"
        result = CommandResult(status="error", output=error_msg)
    except Exception as e:
        logger.error(f"Error in aws_cli_pipeline: {e}")
        error_msg = f"Unexpected error: {str(e)}"
        status = "error"
        result = CommandResult(status="error", output=error_msg)
    finally:
        duration_ms = (time.time() - start_time) * 1000
        request_logger.log_request(
            tool_name="aws_cli_pipeline",
            input_params=input_params,
            output=result,
            status=status,
            duration_ms=duration_ms,
            error=error_msg,
            metadata={"server": "aws-mcp-server", "has_pipe": "|" in command},
        )
    
    return result


@mcp.tool()
async def fetch_webpage(url: str) -> str:
    """
    Tool to fetch data from a webpage or internet. Use this when the user 
    is asking to (1) retrieve information from a specific URL, (2) you need
    more information from the internet to answer the user's query. 

    Args:
        url (str): The URL to fetch data from.

    Returns:
        str: The HTML content of the fetched webpage or an error message.
    """
    return await make_request(url)

