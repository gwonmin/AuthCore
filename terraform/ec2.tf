# EC2 인스턴스용 IAM 역할
resource "aws_iam_role" "ec2_role" {
  name = "authcore-ec2-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "AuthCore EC2 Role"
  }
}
# EC2 인스턴스 프로파일
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "authcore-ec2-profile-${var.environment}"
  role = aws_iam_role.ec2_role.name
}

# DynamoDB 접근 정책
resource "aws_iam_role_policy" "ec2_dynamodb_access" {
  name = "authcore-ec2-dynamodb-access-${var.environment}"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          aws_dynamodb_table.refresh_tokens.arn,
          "${aws_dynamodb_table.users.arn}/index/*",
          "${aws_dynamodb_table.refresh_tokens.arn}/index/*"
        ]
      }
    ]
  })
}

# ECR 접근 정책 (Docker 이미지 pull용)
resource "aws_iam_role_policy" "ec2_ecr_access" {
  name = "authcore-ec2-ecr-access-${var.environment}"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# Ubuntu 22.04 LTS AMI 조회
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# k3s 설치 및 Kubernetes 클러스터 초기화 스크립트
# User Data는 EC2 인스턴스 시작 시 실행되는 스크립트
locals {
  user_data = <<-EOF
#!/bin/bash
# set -e 제거 (cloud-init 타임아웃 방지)

# 로그 파일 설정
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== User data script started at $(date) ==="

# 시스템 업데이트
export DEBIAN_FRONTEND=noninteractive
apt-get update || true
apt-get install -y curl || true

# Public IP 가져오기
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

echo "=== Installing k3s at $(date) ==="

# k3s 설치 (단일 명령어)
# --tls-san: Public IP를 인증서에 추가하여 외부 접근 가능하게 함
# --node-ip: Private IP 사용
# --bind-address: Private IP에 바인딩
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--tls-san $PUBLIC_IP --node-ip $PRIVATE_IP --bind-address $PRIVATE_IP" sh -

# k3s 서비스 상태 확인
systemctl status k3s --no-pager | head -10 || true

# kubeconfig 설정
echo "=== Configuring kubeconfig at $(date) ==="
mkdir -p /home/ubuntu/.kube
sudo cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config || exit 1
sudo chown ubuntu:ubuntu /home/ubuntu/.kube/config

# Public IP로 server 주소 변경 (로컬 접근용)
if [ -n "$PUBLIC_IP" ]; then
  # 기본 kubeconfig는 127.0.0.1을 사용하므로 Public IP로 변경
  sed -i "s|127.0.0.1|$PUBLIC_IP|g" /home/ubuntu/.kube/config
  echo "kubeconfig configured with Public IP: $PUBLIC_IP"
fi

# kubectl이 사용 가능할 때까지 대기
echo "=== Waiting for k3s to be ready at $(date) ==="
export KUBECONFIG=/home/ubuntu/.kube/config
export PATH=$PATH:/usr/local/bin

# kubectl 설치 (k3s에 포함되어 있지만 경로 확인)
until kubectl get nodes 2>/dev/null; do
  echo "Waiting for k3s API server..."
  sleep 5
done

echo "=== k3s is ready at $(date) ==="
kubectl get nodes

# k3s는 기본적으로 단일 노드 클러스터로 설정되며 taint가 자동으로 제거됨
# Flannel CNI도 자동으로 설치됨

echo "=== k3s setup completed at $(date) ===" >> /var/log/user-data.log
EOF
}

# EC2 인스턴스
resource "aws_instance" "k8s_node" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.ec2_instance_type
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.k8s.id]
  subnet_id              = aws_subnet.public[0].id
  user_data              = local.user_data
  key_name               = var.key_pair_name != "" ? var.key_pair_name : null

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = {
    Name        = "authcore-k8s-node-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  # import한 기존 EC2가 다른 subnet/SG에 있으면 replace 방지 (기존 인스턴스 유지)
  lifecycle {
    ignore_changes = [
      subnet_id,
      vpc_security_group_ids,
    ]
  }
}

# Elastic IP (선택사항 - 고정 IP)
resource "aws_eip" "k8s_node" {
  instance = aws_instance.k8s_node.id
  domain   = "vpc"

  tags = {
    Name = "authcore-k8s-eip-${var.environment}"
  }
}

