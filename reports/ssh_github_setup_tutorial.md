# Setting Up SSH for GitHub on Windows

A step-by-step tutorial covering how to connect a local Git repository to GitHub using SSH authentication on Windows (PowerShell).

---

## Why SSH?

When you push code to GitHub, GitHub needs to verify that you're allowed to write to the repository. SSH does this with a **key pair**:

- A **private key** stays on your machine and is never shared.
- A **public key** is uploaded to GitHub.

When you push, your machine proves it owns the matching private key, and GitHub lets you in — no password typing required.

---

## Step 1 — Create the Remote Repository on GitHub

1. Go to GitHub and click **New repository**.
2. Give it a name (e.g. `rossmann-forecast`).
3. **Do not** check "Initialize with README/license/.gitignore" — you already have local commits, and pre-populating the remote will cause a conflict on first push.
4. On the new repo page, switch the clone box from HTTPS to **SSH** and copy the URL. It looks like:

   ```
   git@github.com:yourusername/rossmann-forecast.git
   ```

---

## Step 2 — Link the Local Repo to the Remote

In your project folder:

```powershell
git remote add origin git@github.com:yourusername/rossmann-forecast.git
git branch -M main
git push -u origin main
```

What each line does:

- `remote add origin …` — registers the URL under the conventional name `origin`.
- `branch -M main` — renames `master` to `main` (GitHub's default). Skip if you want to keep `master`.
- `-u origin main` — sets the upstream so future `git push` / `git pull` work without arguments.

The first push will likely fail at this point because SSH isn't set up yet. That's expected — continue to Step 3.

---

## Step 3 — Trust github.com (Host Key Verification)

The first time you connect, SSH asks whether you trust GitHub's server. You'll see:

```
The authenticity of host 'github.com (140.82.121.3)' can't be established.
ED25519 key fingerprint is SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Type `yes` and press Enter. This adds GitHub to your `known_hosts` file so the prompt doesn't appear again.

If you see this prompt during `git push`, the push fails with `Host key verification failed` — that's fine, you only need to confirm it once. Run `ssh -T git@github.com` to trigger the prompt cleanly.

---

## Step 4 — Check for an Existing SSH Key

Before generating a new key, check whether you already have one:

```powershell
ls $env:USERPROFILE\.ssh\
```

Look for files like:

- `id_ed25519` and `id_ed25519.pub` (modern, recommended)
- `id_rsa` and `id_rsa.pub` (older but still valid)

If a key pair exists, skip to Step 6.

---

## Step 5 — Generate a New SSH Key (only if needed)

```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"
```

- Press Enter to accept the default location (`C:\Users\<you>\.ssh\id_ed25519`).
- Optionally set a passphrase, or leave it blank.

The `-C` flag is just a comment label — it has no effect on how the key works.

---

## Step 6 — Print the Public Key

```powershell
cat $env:USERPROFILE\.ssh\id_ed25519.pub
```

You'll get a single line like:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMm6Qx/vduUrEp7ENpynz+2GE+PQgLO2O5Mrun09yW8v your-comment
```

Select and copy the **entire line**, including the algorithm at the start (`ssh-ed25519`) and the comment at the end.

> **Critical:** Always copy from the `.pub` file. The file without `.pub` is your **private** key and must never be shared.

---

## Step 7 — Add the Public Key to GitHub

1. On GitHub, click your avatar (top-right) → **Settings**.
2. Left sidebar → **SSH and GPG keys**.
3. Click **New SSH key**.
4. **Title:** something descriptive (e.g. "Windows desktop").
5. **Key type:** Authentication Key.
6. **Key:** paste the full line you copied.
7. Click **Add SSH key**.

---

## Step 8 — Verify the Connection

```powershell
ssh -T git@github.com
```

A successful response looks like:

```
Hi yourusername! You've successfully authenticated, but GitHub does not provide shell access.
```

If you get `Permission denied (publickey)`, GitHub doesn't recognize your key. Common causes:

- The public key wasn't actually added to GitHub (re-check Step 7).
- You pasted the private key by mistake.
- The ssh-agent doesn't have your key loaded — see the troubleshooting section below.

---

## Step 9 — Push

```powershell
git push -u origin main
```

You should see Git upload your commits to GitHub.

---

## Troubleshooting: ssh-agent Not Running

If SSH can't find your private key automatically, you may need to start the agent and load the key. Open PowerShell **as Administrator** once:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
```

Then in a normal PowerShell:

```powershell
ssh-add $env:USERPROFILE\.ssh\id_ed25519
```

---

## Quick Reference

| Task | Command |
|------|---------|
| List existing keys | `ls $env:USERPROFILE\.ssh\` |
| Generate new key | `ssh-keygen -t ed25519 -C "email@example.com"` |
| Print public key | `cat $env:USERPROFILE\.ssh\id_ed25519.pub` |
| Test GitHub connection | `ssh -T git@github.com` |
| Add remote | `git remote add origin git@github.com:user/repo.git` |
| First push | `git push -u origin main` |
| Subsequent pushes | `git push` |

---

## Security Reminders

- The **private key** (`id_ed25519`) stays on your machine. Never paste it anywhere, never commit it to a repository, never email it.
- The **public key** (`id_ed25519.pub`) is safe to share — that's the whole point.
- If you ever suspect the private key has been exposed, delete it from GitHub's SSH settings, generate a new pair, and add the new public key.
