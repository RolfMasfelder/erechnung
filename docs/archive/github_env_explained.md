# GitHub Environments Explained

This document explains how GitHub Environments work in the eRechnung Django App CI/CD pipeline and what infrastructure you need to provide.

## 🌍 **What are GitHub Environments?**

GitHub Environments provide **deployment protection and configuration management** for your CI/CD pipelines. They act as deployment targets with their own:

- **Secrets and variables** (environment-specific configuration)
- **Protection rules** (approval gates, reviewers, deployment restrictions)
- **Deployment history** (logs and tracking)
- **Branch restrictions** (which branches can deploy to which environments)

## 🎯 **Environment Types in eRechnung**

### **1. Staging Environment**
- **Purpose**: Pre-production testing environment
- **Trigger**: Automatically on every push to `main` branch
- **Usage**: Validate changes before production
- **Protection**: Optional reviewers, immediate deployment
- **Infrastructure**: Separate server/VM for testing

### **2. Production Environment**
- **Purpose**: Live production deployment serving real users
- **Trigger**: Only on tagged releases (e.g., `v1.0.0`, `v1.2.1`)
- **Usage**: Stable, production-ready releases
- **Protection**: **Required reviewers**, manual approval gates
- **Infrastructure**: Production-grade server/VM with high availability

## 🔧 **Setting Up GitHub Environments**

### **Step 1: Create Environments in GitHub**

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Environments**
3. Click **New environment**
4. Create two environments:
   - `staging`
   - `production`

### **Step 2: Configure Environment Protection Rules**

#### **Staging Environment Settings:**
- ✅ **Environment secrets**: STAGING_HOST, STAGING_USER, STAGING_SSH_KEY
- ⚠️ **Required reviewers**: None (auto-deploy)
- ⚠️ **Wait timer**: None
- ✅ **Deployment branches**: `main` branch only

#### **Production Environment Settings:**
- ✅ **Environment secrets**: PRODUCTION_HOST, PRODUCTION_USER, PRODUCTION_SSH_KEY, KUBECONFIG
- ✅ **Required reviewers**: Add yourself and/or team members
- ✅ **Wait timer**: Optional (e.g., 5 minutes for emergency stops)
- ✅ **Deployment branches**: `main` and tags only

### **Step 3: Add Environment Secrets**

#### **Staging Environment Secrets:**
```
STAGING_HOST=staging.yourdomain.com
STAGING_USER=deploy
STAGING_SSH_KEY=--*--BEGIN OPENSSH not a PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
(your private SSH key content)
-----END OPENSSH PRIVATE KEY-----
```

#### **Production Environment Secrets:**
```
PRODUCTION_HOST=production.yourdomain.com
PRODUCTION_USER=deploy
PRODUCTION_SSH_KEY=--*--BEGIN OPENSSH not a PRIVATE KEY-----
(different private SSH key for production)
-----END OPENSSH PRIVATE KEY-----

KUBECONFIG=apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0t...
(your Kubernetes config file content)
```

## 🔑 **SSH Keys Usage**

### **Purpose**
SSH keys enable GitHub Actions to securely connect to your servers and execute deployment commands without passwords.

### **How It Works**
```yaml
- name: Deploy to staging server
  uses: appleboy/ssh-action@v1.0.0
  with:
    host: ${{ secrets.STAGING_HOST }}        # Server IP or domain
    username: ${{ secrets.STAGING_USER }}    # SSH username
    key: ${{ secrets.STAGING_SSH_KEY }}      # Private SSH key
    script: |
      cd /opt/erechnung
      git pull origin main
      docker-compose -f docker-compose.production.yml down
      docker-compose -f docker-compose.production.yml up -d
```

### **SSH Key Generation Process**
```bash
# Generate SSH key pairs (run on your local machine)
ssh-keygen -t rsa -b 4096 -C "github-actions-staging" -f ~/.ssh/erechnung_staging
ssh-keygen -t rsa -b 4096 -C "github-actions-production" -f ~/.ssh/erechnung_production

# Copy public keys to servers
ssh-copy-id -i ~/.ssh/erechnung_staging.pub deploy@staging.yourdomain.com
ssh-copy-id -i ~/.ssh/erechnung_production.pub deploy@production.yourdomain.com

# Get private key content for GitHub secrets
cat ~/.ssh/erechnung_staging      # Copy this to STAGING_SSH_KEY
cat ~/.ssh/erechnung_production   # Copy this to PRODUCTION_SSH_KEY
```

## 🏗️ **Infrastructure Requirements**

You need to provide **2-3 machines/VMs** depending on your deployment strategy:

### **Option 1: Traditional VM Deployment (Recommended for Start)**

#### **Staging Server Requirements:**
- **OS**: Ubuntu 22.04 LTS (or similar)
- **CPU**: 2 cores minimum
- **RAM**: 4GB minimum
- **Storage**: 20GB minimum
- **Network**: Public IP with SSH access (port 22)
- **Firewall**: Allow ports 22 (SSH), 8080 (API Gateway)

#### **Production Server Requirements:**
- **OS**: Ubuntu 22.04 LTS (or similar)
- **CPU**: 4+ cores (depends on load)
- **RAM**: 8GB+ (depends on load)
- **Storage**: 50GB+ (with backup strategy)
- **Network**: Public IP with domain name
- **Firewall**: Allow ports 22 (SSH), 8080 (API Gateway), 443 (HTTPS)
- **SSL Certificate**: For HTTPS termination

### **Option 2: Kubernetes Deployment (Advanced)**

#### **Kubernetes Cluster Requirements:**
- **Managed K8s**: AWS EKS, Google GKE, Azure AKS, or DigitalOcean DOKS
- **Self-hosted**: Minimum 3 nodes (1 master + 2 workers)
- **Resources**: Total 8+ CPU cores, 16GB+ RAM
- **Storage**: Persistent volumes for database
- **Networking**: Load balancer support
- **KUBECONFIG**: Admin access to the cluster

## 🖥️ **Infrastructure Providers**

### **Cloud Providers (Recommended):**

#### **DigitalOcean (Cost-effective)**
```
Staging: $24/month (4GB RAM, 2 vCPU, 80GB SSD)
Production: $48/month (8GB RAM, 4 vCPU, 160GB SSD)
Total: ~$72/month
```

#### **AWS EC2**
```
Staging: t3.medium ($30/month)
Production: t3.large ($60/month)
Total: ~$90/month
```

#### **Google Cloud Platform**
```
Staging: e2-medium ($25/month)
Production: e2-standard-4 ($120/month)
Total: ~$145/month
```

#### **Hetzner (European, Budget-friendly)**
```
Staging: CX21 (€5.39/month)
Production: CX41 (€16.59/month)
Total: ~€22/month (~$24/month)
```

### **Self-hosted Options:**
- **Raspberry Pi cluster** (for learning/development)
- **Home lab servers** (if you have static IP)
- **VPS providers** (Contabo, OVH, Vultr)

## 🚀 **Deployment Flow**

### **Staging Deployment (Automatic)**
```
git push origin main
    ↓
GitHub Actions triggered
    ↓
SSH into staging server
    ↓
git pull + docker-compose up
    ↓
Health check (curl localhost:8080/health)
    ↓
✅ Staging updated
```

### **Production Deployment (Manual Approval)**
```
git tag v1.0.0 && git push origin v1.0.0
    ↓
GitHub Actions triggered
    ↓
⏳ Wait for manual approval
    ↓
Reviewer approves deployment
    ↓
SSH into production server
    ↓
git checkout v1.0.0 + docker-compose up
    ↓
Health check
    ↓
✅ Production updated
```

## 🔒 **Security Considerations**

### **Environment Separation**
- **Different SSH keys** for staging vs production
- **Different servers** (never use same machine)
- **Different domain names** and SSL certificates
- **Different database credentials**

### **Access Control**
- **Limited deploy user permissions** (no root access)
- **SSH key rotation** every 90 days
- **Firewall rules** restricting access
- **VPN access** for production servers (optional but recommended)

### **Monitoring Requirements**
- **Server monitoring** (CPU, RAM, disk usage)
- **Application monitoring** (uptime, response times)
- **Log aggregation** (centralized logging)
- **Backup strategy** (database and file backups)

## 📋 **Next Steps for You**

### **Immediate Actions:**
1. **Choose infrastructure provider** (DigitalOcean recommended for start)
2. **Provision staging server** (start small, can upgrade later)
3. **Set up DNS records** (staging.yourdomain.com)
4. **Generate SSH keys** (separate for staging/production)
5. **Configure GitHub environments** and add secrets

### **Server Setup Checklist:**
- [ ] Ubuntu 22.04 LTS installed
- [ ] Docker and Docker Compose installed
- [ ] Deploy user created with sudo privileges
- [ ] SSH keys configured
- [ ] Firewall rules configured
- [ ] Domain name pointed to server
- [ ] Repository cloned to /opt/erechnung
- [ ] Environment variables configured
- [ ] Initial deployment tested

### **Production Readiness:**
- [ ] Production server provisioned with higher specs
- [ ] SSL certificates configured
- [ ] Database backups automated
- [ ] Monitoring and alerting set up
- [ ] Manual approval process configured in GitHub
- [ ] Load testing performed
- [ ] Disaster recovery plan documented

## 💡 **Recommendations**

### **Start Simple:**
1. **Begin with staging only** on a small DigitalOcean droplet
2. **Test the deployment pipeline** thoroughly
3. **Add production environment** once staging is stable
4. **Consider Kubernetes later** when you need scaling

### **Cost Optimization:**
- **Start with smaller VMs** and scale up based on usage
- **Use managed databases** (less maintenance overhead)
- **Implement auto-scaling** only when needed
- **Monitor costs** and optimize resource usage

### **Alternative: Docker-based Development**
If you don't want to provision servers immediately, you can:
- **Disable the deploy jobs** in the workflow
- **Focus on CI pipeline first** (testing, building, security scanning)
- **Add deployment later** when you're ready with infrastructure

This approach allows you to benefit from automated testing and Docker image building without needing servers right away.
