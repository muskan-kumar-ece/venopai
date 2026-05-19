# Security Operations Guide

## Secret rotation guidance
Rotate on schedule (quarterly) and immediately on compromise.

Targets:
- `SECRET_KEY`
- JWT signing key or refresh token secret
- Database credentials
- Redis credentials
- Razorpay API keys and webhook secret

Rotation steps:
1. Create new secrets in the secret manager.
2. Deploy with both old and new JWT signing keys if supported.
3. Restart services to pick up new secrets.
4. Revoke old secrets after confirmation.

## Admin access review checklist
- List all admin accounts and validate need.
- Remove inactive or unused admins.
- Verify 2FA and strong password policy.
- Review admin actions log for anomalies.
- Confirm least privilege roles.

## Compromised token response procedure
1. Identify affected users and scope.
2. Rotate JWT signing keys and refresh token secret.
3. Invalidate active sessions and force re-login.
4. Review logs for suspicious activity.
5. Notify users if required.

## Webhook secret rotation guidance
1. Schedule a short maintenance window.
2. Disable webhook deliveries at provider.
3. Generate new webhook secret and update env.
4. Deploy backend with new secret.
5. Re-enable webhook deliveries.
6. Run reconciliation for missed events.
