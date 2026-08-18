# Kubernetes Manifests

This directory contains Kubernetes manifests for deploying cpip on Kubernetes clusters.

## Structure

```
k8s/
├── namespace.yaml          # Kubernetes namespace
├── configmap.yaml          # Application configuration
├── secrets.yaml            # Sensitive configuration (base64 encoded)
├── deployment.yaml         # cpip service deployment
├── service.yaml            # Service exposure
├── ingress.yaml            # Ingress for external access
├── hpa.yaml                # Horizontal Pod Autoscaler
├── pdb.yaml                # Pod Disruption Budget
└── rbac/
    ├── serviceaccount.yaml # Service account
    ├── role.yaml           # RBAC role
    └── rolebinding.yaml    # Role binding
```

## Quick Deploy

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Configure secrets (edit before applying)
kubectl apply -f k8s/secrets.yaml -n cpip

# Deploy all resources
kubectl apply -f k8s/ -n cpip

# Verify deployment
kubectl get all -n cpip
kubectl logs -n cpip -l app=cpip
```

## Production Considerations

1. **Secrets Management**: Use tools like Sealed Secrets or External Secrets Operator
2. **TLS/mTLS**: Configure cert-manager for automatic certificate management
3. **Monitoring**: Integrate with Prometheus + Grafana
4. **Logging**: Use ELK stack or cloud-native solutions
5. **Network Policy**: Restrict pod-to-pod communication
6. **Resource Quotas**: Set namespace-level quotas
