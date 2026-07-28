# Educational configuration only. The simulator never initializes this provider.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "high-availability-aws-infrastructure-simulator"
      ManagedBy = "terraform-educational-example"
    }
  }
}
