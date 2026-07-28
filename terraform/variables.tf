variable "aws_region" {
  description = "Example AWS Region for the production-shaped design."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Short environment label used in educational resource names."
  type        = string
  default     = "demo"

  validation {
    condition     = contains(["demo", "production"], var.environment)
    error_message = "Environment must be demo or production."
  }
}

variable "vpc_cidr" {
  description = "Private IPv4 CIDR for the example VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "ami_id" {
  description = "Reviewed Linux AMI identifier supplied by an authorized deployment."
  type        = string

  validation {
    condition     = can(regex("^ami-[0-9a-f]{17}$", var.ami_id))
    error_message = "AMI ID must use the 17-character hexadecimal AWS format."
  }
}

variable "instance_type" {
  description = "Example EC2 instance type for the application launch template."
  type        = string
  default     = "t3.micro"
}

variable "minimum_capacity" {
  description = "Minimum number of application instances."
  type        = number
  default     = 2
}

variable "desired_capacity" {
  description = "Initial number of application instances."
  type        = number
  default     = 2
}

variable "maximum_capacity" {
  description = "Maximum number of application instances."
  type        = number
  default     = 4
}

variable "artifact_bucket_name" {
  description = "Globally unique example bucket name supplied by an authorized deployment."
  type        = string
}
