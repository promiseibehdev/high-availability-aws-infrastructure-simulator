resource "aws_iam_role" "app" {
  name = "${var.environment}-application-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "read_artifacts" {
  name = "read-application-artifacts"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "${aws_s3_bucket.artifacts.arn}/application/*"
    }]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "${var.environment}-application-profile"
  role = aws_iam_role.app.name
}
