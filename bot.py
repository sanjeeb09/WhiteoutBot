from keep_alive import keep_alive  # Imports the Flask server to keep the bot running 24/7
import discord
from discord.ext import commands
import asyncio
import datetime
import time
import os
from dotenv import load_dotenv

# Load environment variables from the .env file (used for local testing)
load_dotenv()

# ==========================================
# ⚙️ SECTION 1: CONFIGURATION
# ==========================================
"""
This section holds all the sensitive data and settings.
Edit these numbers to match your specific Discord server.
"""

# Securely get the token. If on Cloud, it gets it from Environment Variables.
TOKEN = os.getenv('DISCORD_TOKEN')

# Safety check: Stops the bot immediately if no token is found.
if TOKEN is None:
    print("❌ Error: DISCORD_TOKEN not found! Check your .env file or Cloud Settings.")
    exit()

# Channel IDs where the final reports will be sent
LOG_CHANNELS = {
    "Bug": 1436611647463489568,        
    "Suggestion": 1436628659413848114, 
    "Complaint": 1436628820303286376   
}

# Role IDs to be pinged (@Mentioned) when a report comes in
ROLE_PINGS = {
    "Bug": 1439114820157706351,             
    "Suggestion": 1436577296835285012,      
    "Complaint": 1436783614384800008        
}

# The Role ID for "Verified" members (Used for cooldown logic)
VERIFIED_ROLE_ID = 1436577314589769782  

# ==========================================
# 📝 SECTION 2: TEXT & DATA
# ==========================================

"""We store long text and questions here to keep the logic code clean."""


# Dictionary to track how long users have to wait (User ID: Time)
user_cooldowns = {}

# The short messages sent when a user clicks a button (Only they can see this)
EPHEMERAL_MESSAGES = {
    "Bug": "🔧 **Engineering Bay Opened!**\nHi {user}, I have established a secure line here: {channel}.\nLet's fix those broken gears!",
    "Suggestion": "🔥 **Ignition Sequence Started!**\nHi {user}, I have opened a drafting table here: {channel}.\nLet's hear your brilliant ideas!",
    "Complaint": "⚖️ **Council Chamber Cleared!**\nHi {user}, I have prepared a private room here: {channel}.\nWe can discuss the incident confidentially."
}

# The big welcome messages inside the new ticket channel
INTRO_EMBEDS = {
    "Bug": {
        "Title": "🔧 ENGINEERING & BUG REPORT",
        "Desc": (
            "Hey there {user}! Thank you for taking the time to report a problem!\n\n"
            "⚠️ **PLEASE READ BEFORE PROCEEDING:**\n"
            "We **cannot** help with the following (Contact In-Game Support):\n"
            "1️⃣ Account issues (lost account/binding).\n"
            "2️⃣ Reports of inappropriate In-Game behavior.\n"
            "3️⃣ Payment/Refund related issues.\n"
            "4️⃣ Lost/Missing rewards or items.\n\n"
            "**🛠️ TROUBLESHOOTING STEPS:**\n"
            "Before reporting, please try:\n"
            "• Restarting the game.\n"
            "• Rebooting your phone.\n\n"
            "**If your issue is listed above or fixed, click 'End Conversation'.**\n"
            "Otherwise, answer the bot below!"
        ),
        "Color": discord.Color.red()
    },
    "Suggestion": {
        "Title": "💡 STRATEGIC PLANNING ROOM",
        "Desc": (
            "Dear Governor {user}! Thank you so much for sharing your suggestion with us!\n\n"
            "Your ideas are the fuel that keeps our furnace burning. "
            "We review every spark of genius to make our alliance stronger.\n\n"
            "**Changed your mind?** You can end this conversation using the button below.\n"
            "Otherwise, please answer the next couple of questions!"
        ),
        "Color": discord.Color.green()
    },
    "Complaint": {
        "Title": "⚖️ DISCIPLINARY COUNCIL",
        "Desc": (
            "Greetings Chief {user}. We take peacekeeping seriously.\n\n"
            "Please provide honest and accurate information regarding the incident. "
            "False reports may lead to consequences.\n\n"
            "**Changed your mind?** You can close this ticket using the button below.\n"
            "If you are ready, please proceed."
        ),
        "Color": discord.Color.blurple()
    }
}

# The specific questions the bot asks for each category
QUESTIONS = {
    "Bug": {
        "In-Game Name": "What is your **In-Game Username**?",
        "Player ID": "What is your **Player ID**? (e.g. 12345678)",
        "Game Version": "What **Game Version** are you on?",
        "Device Model": "Which **Device** are you using?",
        "OS Version": "Which **OS Version**?",
        "Description": "Please describe the **Bug/Glitch**.",
        "Attachment": "Attach a **Screenshot/Video** (or type 'no')."
    },
    "Suggestion": {
        "In-Game Name": "What is your **In-Game Username**?",
        "Player ID": "What is your **Player ID**?",
        "Topic": "What is this suggestion about?",
        "Idea": "Describe your **Spark of Genius** in detail.",
        "Benefit": "How will this help the alliance?",
        "Attachment": "Attach an example image (or type 'no')."
    },
    "Complaint": {
        "In-Game Name": "What is your **In-Game Username**?",
        "Player ID": "What is your **Player ID**?",
        "Offender Name": "Who is this complaint against?",
        "Violation": "What happened?",
        "Time": "When did this happen?",
        "Evidence": "Attach **Proof** (Required). Type 'no' if none."
    }
}

# ==========================================
# 🤖 SECTION 3: MAIN BOT CLASS
# ==========================================

class PersistentBot(commands.Bot):
    """
    Custom Bot Class that allows buttons to survive restarts (Persistence).
    """
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """This function runs once when the bot starts. It re-loads the buttons."""
        self.add_view(TicketLauncher())
        print("✅ Persistent Views Loaded")

    async def on_ready(self):
        """Runs when the bot successfully connects to Discord."""
        print(f'Logged in as {self.user}')
        # Sets the "Watching the Furnace" status
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the Furnace 🔥"))

bot = PersistentBot()

# ==========================================
# 🖥️ SECTION 4: UI VIEWS (BUTTONS)
# ==========================================

class TicketLauncher(discord.ui.View):
    """
    The Main Menu with 3 buttons (Bug, Suggestion, Complaint).
    Attached to the message sent by !setup.
    """
    def __init__(self):
        super().__init__(timeout=None) # timeout=None ensures it never expires

    async def handle_ticket(self, interaction, ticket_type):
        """
        Central logic to check cooldowns and create tickets.
        """
        user = interaction.user
        user_id = user.id
        
        # --- TIERED COOLDOWN LOGIC ---
        if user.id == interaction.guild.owner_id:
            limit = 60  # 1 Minute for Owner
        elif user.guild_permissions.administrator:
            limit = 120 # 2 Minutes for Admins
        elif discord.utils.get(user.roles, id=VERIFIED_ROLE_ID):
            limit = 300 # 5 Minutes for Verified Members
        else:
            limit = 600 # 10 Minutes for everyone else

        # Check if user is on cooldown
        if user_id in user_cooldowns:
            last_time = user_cooldowns[user_id]
            if time.time() - last_time < limit:
                remaining = int(limit - (time.time() - last_time))
                minutes = remaining // 60
                seconds = remaining % 60
                await interaction.response.send_message(f"❄️ **Chill out, Chief!**\nBased on your rank, you must wait **{minutes}m {seconds}s**.", ephemeral=True)
                return

        # Save current time as last used time
        user_cooldowns[user_id] = time.time()
        
        # IMPORTANT: Defer the response. This tells Discord "Wait, I'm working" 
        # to prevent the "Unknown Interaction" error on slow cloud servers.
        await interaction.response.defer(ephemeral=True)
        
        await create_ticket(interaction, ticket_type)

    # Define the 3 Buttons
    @discord.ui.button(label="Report Bug", style=discord.ButtonStyle.red, custom_id="btn_bug", emoji="🐛")
    async def bug_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_ticket(interaction, "Bug")

    @discord.ui.button(label="Suggestion", style=discord.ButtonStyle.green, custom_id="btn_suggest", emoji="🔥")
    async def suggest_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_ticket(interaction, "Suggestion")

    @discord.ui.button(label="Complaint", style=discord.ButtonStyle.blurple, custom_id="btn_complaint", emoji="🛡️")
    async def complaint_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_ticket(interaction, "Complaint")

class TicketControls(discord.ui.View):
    """
    The 'End Conversation' button shown INSIDE the ticket.
    """
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="End Conversation", style=discord.ButtonStyle.grey, emoji="❌")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❄️ Closing ticket as requested...")
        await asyncio.sleep(2)
        await interaction.channel.delete()

class ConfirmView(discord.ui.View):
    """
    The Yes/No buttons shown after the user answers all questions.
    """
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @discord.ui.button(label="Yes, Submit", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True # User clicked Yes
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="No, Revise", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False # User clicked No
        self.stop()
        await interaction.response.defer()

# ==========================================
# 🧠 SECTION 5: TICKET LOGIC
# ==========================================

async def create_ticket(interaction, ticket_type):
    """
    Creates a private channel for the user.
    """
    guild = interaction.guild
    
    # Find or Create the "Tickets" category
    category = discord.utils.get(guild.categories, name="Tickets")
    if not category:
        category = await guild.create_category("Tickets")

    # Set permissions: Only the Bot and the User can see this channel
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    
    # Create the channel
    channel_name = f"{ticket_type.lower()}-{interaction.user.name}"
    ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
    
    # Create the ephemeral "Click here" message
    msg_template = EPHEMERAL_MESSAGES[ticket_type]
    formatted_msg = msg_template.format(user=interaction.user.mention, channel=ticket_channel.mention)
    
    # Use followup.send because we deferred earlier
    await interaction.followup.send(formatted_msg, ephemeral=True)
    
    # Start the Q&A process (Wrap in try/except in case user deletes channel)
    try:
        await run_interview(ticket_channel, interaction.user, ticket_type)
    except:
        pass

async def run_interview(channel, user, ticket_type):
    """
    Runs the entire interview process:
    1. Intro -> 2. Questions -> 3. Validation -> 4. Summary -> 5. Logging
    """
    
    # --- STEP 1: SEND INTRO ---
    data = INTRO_EMBEDS[ticket_type]
    formatted_desc = data["Desc"].format(user=user.mention)
    
    embed = discord.Embed(
        title=data["Title"],
        description=formatted_desc,
        color=data["Color"]
    )
    # Attach the "End Conversation" button
    await channel.send(embed=embed, view=TicketControls())
    
    questions = QUESTIONS[ticket_type]
    answers = {}
    captured_attachment = None 

    def check(m):
        # Ensures the bot only listens to the correct user in the correct channel
        return m.author == user and m.channel == channel

    # --- STEP 2: ASK QUESTIONS LOOP ---
    for field, question in questions.items():
        await channel.send(f"🔹 **{field}:** {question}")
        
        # Validation Loop: Keep asking until valid input is received
        while True:
            try:
                msg = await bot.wait_for('message', check=check, timeout=300)
                
                # Check: Is "Player ID" a number?
                if field == "Player ID" and not msg.content.isdigit():
                    await channel.send("⚠️ **Invalid Player ID.** Numbers only please.")
                    continue
                
                # Check: Did they upload an image?
                if msg.attachments:
                    captured_attachment = msg.attachments[0] 
                    answers[field] = "*(Image Attached)*"
                else:
                    answers[field] = msg.content
                break # Input is valid, move to next question

            except asyncio.TimeoutError:
                await channel.send("❄️ Frozen due to inactivity. Closing.")
                await asyncio.sleep(5)
                await channel.delete()
                return

    # --- STEP 3: SUMMARY & REVISION LOOP ---
    while True:
        summary_text = ""
        for field, ans in answers.items():
            summary_text += f"**{field}:** {ans}\n"

        embed = discord.Embed(title=f"❄️ {ticket_type} Summary", description=summary_text, color=discord.Color.gold())
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Send Summary with Yes/No buttons
        view = ConfirmView()
        await channel.send(embed=embed, view=view)
        await view.wait()

        if view.value is True:
            # --- USER CLICKED YES: SUBMIT TO LOGS ---
            log_channel_id = LOG_CHANNELS[ticket_type]
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                log_embed = discord.Embed(title=f"📄 New {ticket_type} Report", color=discord.Color.green(), timestamp=datetime.datetime.now())
                log_embed.set_author(name=f"{user.name} (ID: {user.id})", icon_url=user.display_avatar.url)
                log_embed.set_thumbnail(url=user.display_avatar.url)
                
                for field, ans in answers.items():
                    log_embed.add_field(name=field, value=ans, inline=False)
                
                # Image Re-upload Logic
                file_to_send = None
                if captured_attachment:
                    try:
                        # Converts the attachment to a file the bot can upload
                        file_to_send = await captured_attachment.to_file()
                        log_embed.set_image(url=f"attachment://{file_to_send.filename}")
                    except:
                        pass

                # Ping the relevant Role
                role_id = ROLE_PINGS.get(ticket_type)
                if role_id:
                    await log_channel.send(f"<@&{role_id}>")

                # Send the Log
                if file_to_send:
                    await log_channel.send(embed=log_embed, file=file_to_send)
                else:
                    await log_channel.send(embed=log_embed)

                await channel.send("✅ Submitted! Closing channel...")
                await asyncio.sleep(5)
                await channel.delete()
                break
            else:
                await channel.send("❌ Log channel not found.")
                break

        else:
            # --- USER CLICKED NO: REVISE ANSWER ---
            keys = list(questions.keys())
            valid_options = ", ".join(keys)
            await channel.send(f"⚠️ **Type the field name to revise:**\n`{valid_options}`")
            
            try:
                retry_msg = await bot.wait_for('message', check=check, timeout=60)
                choice = retry_msg.content.strip()
                
                # Match user input to a field key (Case Insensitive)
                matched_key = next((k for k in keys if k.lower() == choice.lower()), None)
                
                if matched_key:
                    await channel.send(f"🔄 Re-enter value for **{matched_key}**:")
                    # Inner Loop for Revision Validation
                    while True:
                        new_msg = await bot.wait_for('message', check=check, timeout=120)
                        if matched_key == "Player ID" and not new_msg.content.isdigit():
                            await channel.send("⚠️ **Invalid Player ID.** Numbers only.")
                            continue
                        
                        if new_msg.attachments:
                            captured_attachment = new_msg.attachments[0]
                            answers[matched_key] = "*(Image Attached)*"
                        else:
                            if answers[matched_key] == "*(Image Attached)*": captured_attachment = None
                            answers[matched_key] = new_msg.content
                        break
                else:
                    await channel.send("❌ Invalid field.")

            except asyncio.TimeoutError:
                break

# ==========================================
# 🛠️ SECTION 6: COMMANDS & STARTUP
# ==========================================

@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    """
    Admin Command: Force deletes the ticket channel instantly.
    Usage: !close
    """
    if isinstance(ctx.channel, discord.TextChannel) and ctx.channel.name.startswith(("bug-", "suggestion-", "complaint-")):
        await ctx.send("⛔ **Admin Force Close Initiated.**")
        await asyncio.sleep(2)
        await ctx.channel.delete()
    else:
        await ctx.send("You can only use this inside a Ticket channel.")

@bot.command()
async def setup(ctx):
    """
    Setup Command: Deploys the main menu with buttons.
    Usage: !setup
    """
    desc = """
Your eyes and ears are the lifeblood of our city. We need your brilliant insights and frosty findings to keep our alliance strong and our furnace burning bright!

### 🐛 BUGS & GLITCHES 🐛
Spotted something... *off*? A glitch in the game or our Discord that's colder than a malfunctioning furnace? 🥶
► **Report the issue!** Our tech survivors will get their tools and thaw out the problem!

### 🔥 SPARKS OF GENIUS (Suggestions) 🔥
Have a brilliant idea to make our alliance or Discord server stronger? A new strategy or a way to improve our home? 💭
► **Share your brainwave!** Your spark of genius could be the very thing that helps us all thrive in this frozen wasteland!

### 🛡️ ALLIANCE PEACEKEEPERS (Complaints) 🛡️
Found someone breaking the peace? 😠 An unauthorized attack on your city? Someone poaching your gathering spot? Or ignoring our sacred NAP rules? 📜
► **Let us know!** Our Alliance Peacekeepers will investigate the incident and ensure order is restored.

»»————- ❄️ TOGETHER WE SURVIVE ❄️ ————-««
    """
    embed = discord.Embed(title="Greetings, Chiefs! 👋", description=desc, color=discord.Color.from_rgb(52, 152, 219))
    await ctx.send(embed=embed, view=TicketLauncher())

# Start the Flask Web Server (To keep Render happy)
keep_alive()

# Start the Discord Bot
bot.run(TOKEN)
