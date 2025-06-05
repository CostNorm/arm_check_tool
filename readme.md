# ARM Compatibility Analyzer - Deployment Guide

This guide explains how to deploy the ARM Compatibility Analyzer as an AWS Lambda function using Terraform. The deployed Lambda function can be invoked directly or through the included `analyzer.py` client module, and is also integrated with the CostNorm MCP server for automated ARM64 migration workflows.

## Architecture Overview

The ARM Compatibility Analyzer consists of:

1. **Lambda Function** (`src/`): Core analysis logic deployed to AWS Lambda
2. **Client Module** (`analyzer.py`): Python client for invoking the Lambda function
3. **Supporting Tools**: Lambda search and architecture change tools
4. **MCP Integration**: Used by CostNorm MCP server for automated workflows

## Prerequisites

1. **AWS Account & Credentials**: You need AWS credentials with permissions to create Lambda functions, IAM roles, and CloudWatch Log Groups.
    * Configure your AWS CLI: `aws configure --profile costnorm`
    * Or set AWS environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

2. **Terraform**: Download and install Terraform (version >= 1.0.0)
    * Download from: <https://www.terraform.io/downloads>
    * Verify installation: `terraform -v`

3. **Docker**: Docker must be installed and running on the machine where you execute `terraform apply`. This is required for building the Python dependency layer.
    * Download from: <https://www.docker.com/get-started>
    * Verify installation: `docker --version`

4. **Python & Dependencies (for Local Development)**: Python 3.8+ and pip installed.
    * Install dependencies listed in `requirements.txt` if you plan to run or test locally: `pip install -r requirements.txt`

## Local Development

For local development and testing, you can use a `.env` file to configure environment variables:

1. Create a `.env` file in the `src/` directory with the necessary variables (see `src/.env.sample` for a template):

    ```dotenv
    # GitHub API Access
    GITHUB_TOKEN=your_github_token_here

    # DockerHub Access (for Docker image inspection)
    DOCKERHUB_USERNAME=your_dockerhub_username
    DOCKERHUB_PASSWORD=your_dockerhub_password_or_token

    # Analyzer Configuration (set to True/False)
    ENABLE_TERRAFORM_ANALYZER=True
    ENABLE_DOCKER_ANALYZER=True
    ENABLE_DEPENDENCY_ANALYZER=True
    ```

2. Run the analyzer locally (from the `src/` directory):

    ```bash
    cd src
    # Make sure dependencies are installed locally if needed for testing
    pip install -r ../requirements.txt
    python lambda_function.py
    ```

The code in `src/config.py` automatically detects whether it's running in Lambda or locally and will load the `.env` file if it's not in a Lambda environment.

## Deployment Steps

### 1. Configure Terraform Variables

1. Navigate to the Terraform directory:

    ```bash
    cd terraform
    ```

2. Create your variable definitions file by copying the example:

    ```bash
    cp terraform.auto.tfvars.example terraform.auto.tfvars
    ```

3. Edit `terraform.auto.tfvars` and fill in your values:

    ```hcl
    # --- Required Credentials ---
    dockerhub_username = "YOUR_DOCKERHUB_USERNAME"
    dockerhub_password = "YOUR_DOCKERHUB_PASSWORD_OR_PAT"
    github_token       = "YOUR_GITHUB_TOKEN"

    # --- Analyzer Configuration ---
    enable_terraform_analyzer  = "True"
    enable_docker_analyzer     = "True" 
    enable_dependency_analyzer = "True"

    # --- Optional Overrides ---
    aws_region = "ap-northeast-2"  # Default region
    log_level  = "INFO"            # Or "DEBUG"
    
    # Customize function names if needed
    # lambda_function_name = "custom-arm-analyzer"
    # lambda_timeout = 300
    # lambda_memory_size = 1024
    ```

    **Important**: Do not commit this file with sensitive credentials to version control.

### 2. Deploy with Terraform

From within the `terraform/` directory, run the following commands:

```bash
# Initialize Terraform (downloads providers like aws and archive)
terraform init

# Preview the changes Terraform will make
terraform plan

# Apply the changes to deploy to AWS
terraform apply
```

Confirm the apply operation when prompted.

**What `terraform apply` does:**

* Creates a zip file from the `src/` directory, excluding development files like `.env`, `__pycache__/`, etc.
* Uses Docker to build Python dependencies into a Lambda layer for ARM64 architecture
* Creates/updates the IAM role, Lambda layer, Lambda function, and CloudWatch Log Group in your AWS account
* Injects variables from `terraform.auto.tfvars` into the Lambda function's environment

Terraform will output information about the created resources upon successful completion.

### 3. Update Client Configuration (if using analyzer.py)

If you plan to use the `analyzer.py` client module, update the Lambda function name:

1. Open `analyzer.py`
2. Update the `ARM_ANALYSIS_LAMBDA_FUNCTION_NAME` variable with the Lambda function name from Terraform output:

   ```python
   ARM_ANALYSIS_LAMBDA_FUNCTION_NAME = "arm-compatibility-analyzer"  # Update if you customized the name
   ```

3. Ensure you have the correct AWS profile configured:

   ```python
   boto3_session = boto3.Session(profile_name='costnorm', region_name='ap-northeast-2')
   ```

## Usage

### Direct Lambda Invocation

The Lambda function expects a JSON payload with a `github_url` parameter:

```bash
# Using AWS CLI
aws lambda invoke \
  --function-name arm-compatibility-analyzer \
  --payload '{"github_url":"https://github.com/username/repo-to-analyze"}' \
  response.json

# View the result
cat response.json
```

### Using the Client Module

```python
from analyzer import _invoke_arm_analysis_lambda

# Analyze a repository
result = await _invoke_arm_analysis_lambda("https://github.com/username/repo")
print(result)
```

### MCP Server Integration

The Lambda function is automatically integrated with the CostNorm MCP server through the `analyze_repo_arm_compatibility` tool. The MCP server can:

1. Analyze repository ARM compatibility
2. Search for existing Lambda functions
3. Automatically migrate compatible functions to ARM64

## Supporting Tools

The deployment also includes additional Lambda functions for ARM migration workflows:

### Lambda Search Tool

```bash
# Search for Lambda functions by name
aws lambda invoke \
  --function-name lambda_search_tool \
  --payload '{"query":"my-function","only_x86":true}' \
  search_result.json
```

### Lambda Architecture Change Tool

```bash
# Change function architecture to ARM64
aws lambda invoke \
  --function-name lambda_architecture_change_tool \
  --payload '{"function_name":"my-function","target_arch":"arm64"}' \
  change_result.json
```

## Response Format

The ARM compatibility analyzer returns a structured JSON response:

```json
{
  "repository": "owner/repo",
  "github_url": "https://github.com/owner/repo",
  "default_branch": "main",
  "analysis_details": {
    "dependencies": {
      "results": [...],
      "recommendations": [...],
      "reasoning": [...]
    },
    "docker_analysis": {
      "results": [...], 
      "recommendations": [...],
      "reasoning": [...]
    },
    "instance_types": {
      "results": [...],
      "recommendations": [...], 
      "reasoning": [...]
    }
  },
  "overall_compatibility": "compatible|incompatible|unknown",
  "recommendations": [...],
  "context": {
    "analysis_summary": {...},
    "reasoning": [...],
    "enabled_analyzers": [...],
    "statistics": {...}
  }
}
```

## Cleanup

To remove all resources created by Terraform:

```bash
# From within the terraform/ directory
terraform destroy
```

Confirm the destroy operation when prompted.

## Troubleshooting

* **Terraform Errors**: Read the output carefully. Common issues include missing credentials, Docker not running, or AWS permissions errors. Run `terraform init` if you add new providers.

* **Lambda Execution Errors**: Check AWS CloudWatch logs for the function (e.g., `/aws/lambda/arm-compatibility-analyzer`). Log group name is available in Terraform outputs.

* **Configuration**: Verify environment variables in the Lambda function settings via the AWS Console (Terraform should set these from `terraform.auto.tfvars`).

* **Dependencies**: Ensure `requirements.txt` is correct. Check the logs from the `local-exec` layer build step during `terraform apply` for Docker errors.

* **Permissions**: Verify the IAM role has the necessary permissions (`AWSLambdaBasicExecutionRole` is attached by default).

* **Client Connection**: If using `analyzer.py`, ensure your AWS profile (`costnorm`) is configured correctly and has permissions to invoke the Lambda function.

## Security Considerations

* Store sensitive credentials (GitHub token, Docker Hub credentials) securely
* Consider using AWS Secrets Manager for production deployments instead of environment variables
* The Lambda function runs with minimal IAM permissions for security
* All network communication uses HTTPS

## Contributing

When adding new analyzers or modifying existing ones:

1. Follow the `BaseAnalyzer` interface in `src/analyzers/base_analyzer.py`
2. Add new analyzer configurations to `src/config.py`
3. Update `requirements.txt` if new dependencies are needed
4. Test locally before deploying
5. Update this README with any new configuration options
