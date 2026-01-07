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

# kubeadm 설치 및 Kubernetes 클러스터 초기화 스크립트
# User Data는 EC2 인스턴스 시작 시 실행되는 스크립트
locals {
  user_data = <<-EOF
#!/bin/bash
set -e

# 시스템 업데이트
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# containerd 설치
apt-get install -y containerd
mkdir -p /etc/containerd
containerd config default | tee /etc/containerd/config.toml
systemctl restart containerd
systemctl enable containerd

# swap 비활성화 (Kubernetes 요구사항)
swapoff -a
sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# 커널 모듈 로드
cat <<MODULES | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
MODULES

modprobe overlay
modprobe br_netfilter

# sysctl 설정
cat <<SYSCTL | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
SYSCTL

sysctl --system

# Kubernetes 패키지 설치
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

# kubelet 자동 시작
systemctl enable kubelet

# Kubernetes 클러스터 초기화
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4) \
  --apiserver-cert-extra-sans=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4) \
  --ignore-preflight-errors=Swap

# kubectl 설정 (kubeadm init 완료 후)
mkdir -p /home/ubuntu/.kube
cp -i /etc/kubernetes/admin.conf /home/ubuntu/.kube/config
chown -R ubuntu:ubuntu /home/ubuntu/.kube

# 환경 변수 설정 (kubectl 사용을 위해)
export KUBECONFIG=/home/ubuntu/.kube/config

# Master 노드에서도 Pod 스케줄링 허용 (단일 노드 클러스터)
# kubeadm init이 완료된 후 실행되므로 잠시 대기
sleep 10
# kubectl이 사용 가능할 때까지 대기
until kubectl get nodes --kubeconfig=/home/ubuntu/.kube/config 2>/dev/null; do
  echo "Waiting for Kubernetes API server..."
  sleep 5
done
kubectl taint nodes --all node-role.kubernetes.io/control-plane- --kubeconfig=/home/ubuntu/.kube/config || true

# Flannel 네트워크 플러그인 설치
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml --kubeconfig=/home/ubuntu/.kube/config || {
  echo "Failed to install Flannel, retrying..."
  sleep 10
  kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml --kubeconfig=/home/ubuntu/.kube/config
}

# 로그 저장
echo "User data script completed at $(date)" >> /var/log/user-data.log
EOF
}

# EC2 인스턴스
resource "aws_instance" "k8s_node" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.small"
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.k8s.id]
  subnet_id              = aws_subnet.public[0].id
  user_data              = local.user_data

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
}

# Elastic IP (선택사항 - 고정 IP)
resource "aws_eip" "k8s_node" {
  instance = aws_instance.k8s_node.id
  domain   = "vpc"

  tags = {
    Name = "authcore-k8s-eip-${var.environment}"
  }
}

