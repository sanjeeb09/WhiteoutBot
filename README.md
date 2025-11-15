# \[WOS\] Whitey Bot ❄️

> **Status:** 🟢 `ONLINE` (Hosted on Render)

A 24/7 Alliance Management Bot built with Python for our Whiteout Survival Discord. Whitey Bot is designed to keep our city running smoothly by managing all survivor reports, validating data, and ensuring our leadership is alerted.

It runs 24/7 on a secure cloud server, always watching the furnace.

## 🔥 Core Capabilities (v1.0)

Whitey Bot isn't just a simple ticket bot; it's a fully integrated Alliance assistant.

* **🛡️ Trinity Ticket System:** A persistent, 3-button (Bug, Suggestion, Complaint) UI in `#help-center` that survives bot restarts.

* **🤖 The Interviewer:** A conversational Q&A flow for each ticket, asking specific, themed questions and validating data (like checking for `Player ID` numbers).

* **🗃️ Smart Routing:** Automatically sends completed reports to the correct private log channels (`#bugs`, `#complaints`, etc.).

* **📸 Image Reconstruction:** Securely re-uploads evidence attachments (so they never expire) and posts them directly in the log.

* **🚨 Smart Pings:** Pings specific roles based on the report type (e.g., `@Tech Support` for bugs, `@R4s` for complaints).

* **⏲️ Tiered Cooldowns:** Dynamic wait times to prevent spam:
    * `1 Min` for Server Owner
    * `2 Min` for Admins
    * `5 Min` for Verified
    * `10 Min` for Unverified

* **🧊 Themed UI:** Custom, immersive messages (like "Engineering Bay Opened!") for every step of the process.

* **🔐 Secure & Persistent:** Runs 24/7 on Render, uses Environment Variables (no hardcoded tokens), and is kept awake by an external cron-job.

## 🛠️ Engineering Bay (Tech Stack)

* **Python 3**

* **discord.py:** The core library for bot interaction.

* **Flask:** A micro web server used for the `keep_alive` trick needed by Render.

* **python-dotenv:** For securely managing the `DISCORD_TOKEN` in a local `.env` file.

* **Render.com:** Cloud Hosting (Free Web Service Tier).

* **Cron-job.org:** Uptime pinger to prevent the server from sleeping.

## 🚀 Ignition Sequence (How to Deploy)

This bot is configured for deployment on **Render**.

1.  **Repo:** Upload the code to a public GitHub repository. Ensure your `.env` file is listed in `.gitignore`.

2.  **Render Setup:** Create a new **Web Service** on Render and connect your GitHub repo.

3.  **Render Settings:**
    * **Build Command:** `pip install -r requirements.txt`
    * **Start Command:** `python bot.py`

4.  **Render Environment:** Go to the "Environment" tab and add a secret variable:
    * **Key:** `DISCORD_TOKEN`
    * **Value:** `YourActualBotTokenHere`

5.  **Uptime:** Take your Render URL (e.g., `https://whitey-bot.onrender.com`) and plug it into a free pinger like `cron-job.org` to run every 5 minutes. This keeps the Flask server active and the bot online.

## 🔒 Securing the Vault (.env)

For local testing, a `.env` file is required in the root directory:
