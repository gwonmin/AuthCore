#!/bin/bash
set -e

echo "🚀 Starting Kubernetes cluster setup with kubeadm..."

# 시스템 업데이트
echo "📦 Updating system packages..."
apt-get update
apt-get install -y apt-transport-https ca-certificates curl

# containerd 설치
echo "🐳 Installing containerd..."
apt-get install -y containerd
mkdir -p /etc/containerd
containerd config default | tee /etc/containerd/config.toml
systemctl restart containerd
systemctl enable containerd

# swap 비활성화 (Kubernetes 요구사항)
echo "🔄 Disabling swap..."
swapoff -a
sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# 커널 모듈 로드
echo "📦 Loading kernel modules..."
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

# sysctl 설정
echo "⚙️  Configuring sysctl..."
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sysctl --system

# Kubernetes 패키지 설치
echo "📦 Installing Kubernetes packages..."
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

# kubelet 자동 시작
systemctl enable kubelet

# Kubernetes 클러스터 초기화
echo "🎯 Initializing Kubernetes cluster..."
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4) \
  --apiserver-cert-extra-sans=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4) \
  --ignore-preflight-errors=Swap

# kubectl 설정
echo "⚙️  Configuring kubectl..."
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# Master 노드에서도 Pod 스케줄링 허용 (단일 노드 클러스터)
echo "🔓 Removing taint from master node..."
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

# Flannel 네트워크 플러그인 설치
echo "🌐 Installing Flannel CNI..."
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# 클러스터 준비 대기
echo "⏳ Waiting for cluster to be ready..."
sleep 30
kubectl get nodes

echo "✅ Kubernetes cluster setup completed!"
echo ""
echo "📝 Next steps:"
echo "  1. Copy kubeconfig: scp ubuntu@<EC2_IP>:/home/ubuntu/.kube/config ~/.kube/config"
echo "  2. Verify cluster: kubectl get nodes"
echo "  3. Install local-path-provisioner for storage (optional)"

