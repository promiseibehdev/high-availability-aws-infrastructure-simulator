# Display-only educational test definition. The application never executes it.
mock_provider "aws" {}

variables {
  environment          = "demo"
  ami_id               = "ami-0123456789abcdef0"
  artifact_bucket_name = "ha-simulator-test-example"
}

run "reference_design" {
  command = plan

  assert {
    condition     = aws_vpc.main.enable_dns_support
    error_message = "The VPC must keep DNS support enabled."
  }

  assert {
    condition     = aws_autoscaling_group.app.min_size >= 2
    error_message = "The example must retain at least two instances."
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.artifacts.restrict_public_buckets
    error_message = "The artifacts bucket must block public access."
  }
}
