module "mcp_tool_iac_template" {
  source = "github.com/CostNorm/mcp_tool_iac_template"
  function_name = "lambda_architecture_change_tool"
  lambda_handler = "lambda_function.lambda_handler"
  lambda_runtime = "python3.13"
  lambda_architecture = "arm64"
  lambda_timeout = 300
  lambda_memory = 1024
  attach_lambda_arch_change_policy = true
  region = "ap-northeast-2"
  profile = "costnorm"
}