output "api_endpoint" {
  description = "API Gateway endpoint"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.incidents.name
}

output "failure_queue_url" {
  description = "SQS failure queue URL"
  value       = aws_sqs_queue.failure_queue.url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.incident_api.function_name
}

output "sns_topic_arn" {
  description = "SNS topic ARN"
  value       = aws_sns_topic.alarm_topic.arn
}

output "github_actions_role_arn" {
  description = "IAM Role ARN for GitHub Actions OIDC deployment"
  value       = aws_iam_role.github_actions_deploy_role.arn
}