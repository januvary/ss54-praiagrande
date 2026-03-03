# Quick Start: Cloudflare Tunnel Deployment

## What Changed?

✅ **REMOVED:** Windows Firewall configuration (no admin needed!)
✅ **ADDED:** Cloudflare Tunnel for secure external access
✅ **CHANGED:** App binds to localhost only (127.0.0.1:8000) - more secure

## How to Deploy (3 Steps)

### 1. Run Deployment Script

```powershell
cd ss54-backend
.\scripts\deploy.ps1
```

### 2. Configure Tunnel (when prompted at Phase 8)

```
Configurar Cloudflare Tunnel? (s/n) → s
Subdominio (deixe vazio para dominio raiz) → [Enter]
Iniciar tunnel agora? (s/n) → s
```

### 3. Access Your App

```
https://ss54pg.com.br
```

That's it! No admin required, no firewall configuration, automatic HTTPS.

## Management Commands

### Check Status
```powershell
.\scripts\cloudflare\status.ps1
```

### Start Tunnel
```powershell
.\scripts\cloudflare\start-tunnel.ps1
```

### Stop Tunnel
```powershell
.\scripts\cloudflare\stop-tunnel.ps1
```

### Reconfigure Tunnel
```powershell
.\scripts\cloudflare\setup.ps1
```

## Prerequisites (One-Time Setup)

Before first deployment:

1. **Create Cloudflare Account** (Free)
   - Visit: https://dash.cloudflare.com/sign-up

2. **Add Your Domain to Cloudflare**
   - Visit: https://dash.cloudflare.com
   - Click "Add a site"
   - Enter: `ss54pg.com.br`
   - Update nameservers at your registrar
   - Wait for propagation (usually < 1 hour)

## What Happens During Setup

1. ✓ Downloads cloudflared (no admin)
2. ✓ Opens browser for authentication
3. ✓ Creates tunnel automatically
4. ✓ Configures DNS (ss54pg.com.br → tunnel)
5. ✓ Starts tunnel
6. ✓ Your app is live on HTTPS!

## Architecture

```
User → https://ss54pg.com.br
         ↓
    Cloudflare Edge
         ↓
    Tunnel (outbound)
         ↓
    Your App (127.0.0.1:8000)
```

## Benefits

✅ **No admin rights** - Everything runs in user space
✅ **No firewall config** - No inbound ports needed
✅ **Free HTTPS** - Automatic SSL certificate
✅ **More secure** - App only accessible via tunnel
✅ **Works everywhere** - Behind NAT, firewalls, etc.
✅ **DDoS protection** - Cloudflare's network

## Troubleshooting

### "cloudflared not found"
→ Run `.\scripts\cloudflare\setup.ps1` - it will download automatically

### "Authentication failed"
→ Make sure you have a Cloudflare account and domain added

### "Cannot access https://ss54pg.com.br"
→ Check tunnel status: `.\scripts\cloudflare\status.ps1`
→ Make sure app is running: `nssm status SS54Backend`
→ Check logs: `%USERPROFILE%\.cloudflared\logs\`

## For Detailed Information

See: `ss54-backend\scripts\cloudflare\README.md`

## Quick Reference

| Task | Command |
|------|---------|
| Full deployment | `.\scripts\deploy.ps1` |
| Check tunnel status | `.\scripts\cloudflare\status.ps1` |
| Start tunnel | `.\scripts\cloudflare\start-tunnel.ps1` |
| Stop tunnel | `.\scripts\cloudflare\stop-tunnel.ps1` |
| Reconfigure tunnel | `.\scripts\cloudflare\setup.ps1` |
| View documentation | `.\scripts\cloudflare\README.md` |
| Manage Windows service | `nssm start/stop/restart SS54Backend` |

## Need Help?

1. Check tunnel status: `.\scripts\cloudflare\status.ps1`
2. Read the docs: `ss54-backend\scripts\cloudflare\README.md`
3. Check logs:
   - Tunnel: `%USERPROFILE%\.cloudflared\logs\`
   - App: `C:\ss54-praiagrande\logs\`

---

**That's it!** Run `.\scripts\deploy.ps1` and choose to configure Cloudflare Tunnel when prompted. Your app will be live on HTTPS with zero admin required.
