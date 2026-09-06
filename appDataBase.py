import os
import smtplib
import psycopg2
from psycopg2.extras import RealDictCursor
from email.message import EmailMessage
from flask import Flask, request, jsonify, render_template_string

# ==========================================
# 1. CONFIGURATION (UPDATE THESE!)
# ==========================================
# 🐘 PostgreSQL Settings
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "Bajisk@591"  # 👈 Enter the password you set during installation

# 📧 Email Settings
EMAIL_ADDRESS = "shaikbaji860566@gmail.com"  # 👈 Your sender email
EMAIL_PASSWORD = "eycsrblsevdxzsjj"           # 👈 The App Password you generated
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to Vanguard, {Name}! Action Required",
        "body": "Hi {Name},\n\nWelcome to Vanguard! Your account profile has been created.\n\nPlease upload BGC documents.\n\nBest,\nTeam"
    }
}

app = Flask(__name__)

# ==========================================
# 2. DATABASE CONNECTION HELPER
# ==========================================
def get_db_connection():
    """Establishes and returns a connection to PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"❌ PostgreSQL Connection Error: {e}")
        return None

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def is_yes(val):
    return str(val).strip().lower() == "yes" if val is not None else False

def clean_val(val):
    return str(val).strip() if val is not None else ""

def send_email(to_email, name, template_key):
    template = EMAIL_TEMPLATES.get(template_key)
    if not template: return False
    msg = EmailMessage()
    msg.set_content(template["body"].replace("{Name}", name))
    msg['Subject'] = template["subject"].replace("{Name}", name)
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Welcome email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# ==========================================
# 4. POSTGRESQL DATA FETCH & UPDATE
# ==========================================
def get_user_data(target_user):
    target = target_user.strip().lower()
    conn = get_db_connection()
    if not conn:
        return None, "Database connection failed. Ensure PostgreSQL service is running."

    record = None
    event_msg = None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Query the User from onboarding_users table
            cur.execute("""
                SELECT * FROM onboarding_users 
                WHERE LOWER(email) = %s OR LOWER(name) = %s 
                LIMIT 1;
            """, (target, target))
            user_row = cur.fetchone()

            if not user_row:
                return None, f"User '{target_user}' not found in database."

            user_id = user_row["id"]
            name = clean_val(user_row["name"])
            email = clean_val(user_row["email"])
            profile_created = user_row.get("profile_created")
            welcome_sent = user_row.get("welcome_sent")

            # 2. TRIGGER: If profile_created is 'Yes' & welcome email not sent yet
            if is_yes(profile_created) and not is_yes(welcome_sent):
                if send_email(email, name, "welcome"):
                    # 💾 UPDATE DATABASE: Set welcome_sent = 'Yes'
                    cur.execute("""
                        UPDATE onboarding_users 
                        SET welcome_sent = 'Yes', updated_at = NOW() 
                        WHERE id = %s;
                    """, (user_id,))
                    conn.commit()
                    welcome_sent = "Yes"
                    event_msg = f"Welcome email sent to {name} and recorded in database!"
                    print(f"💾 Updated PostgreSQL: welcome_sent='Yes' for user ID {user_id}")

            # 3. Query User's Assigned Trainings using SQL JOIN
            cur.execute("""
                SELECT 
                    t.training_name,
                    ut.status,
                    ut.completed_at
                FROM user_trainings ut
                JOIN trainings_catalog t ON ut.training_id = t.id
                WHERE ut.user_id = %s
                ORDER BY t.id;
            """, (user_id,))
            training_rows = cur.fetchall()

            trainings_list = []
            pending_trainings = []
            for t in training_rows:
                t_name = t["training_name"]
                t_status = clean_val(t["status"]) or "Pending"
                trainings_list.append({
                    "name": t_name,
                    "status": t_status
                })
                if t_status.lower() != "completed":
                    pending_trainings.append(t_name)

            record = {
                "name": name,
                "email": email,
                "profile_created": "Yes" if is_yes(profile_created) else "Pending",
                "welcome_sent": "Yes" if is_yes(welcome_sent) else "Pending",
                "bgc_status": clean_val(user_row.get("bgc_status")) or "Pending",
                "onboarding_status": clean_val(user_row.get("onboarding_status")) or "In Progress",
                "credentials_sent": "Yes" if is_yes(user_row.get("credentials_sent")) else "Pending",
                "trainings": trainings_list,
                "pending_trainings": pending_trainings
            }

    except Exception as e:
        print(f"❌ Error during database query: {e}")
        return None, f"Database error: {e}"
    finally:
        conn.close()

    return record, event_msg

# ==========================================
# 5. AI AGENT ENGINE (PROMPTS & SUGGESTIONS)
# ==========================================
def generate_agent_response(user_data, prompt):
    p = prompt.strip().lower()
    name = user_data["name"]
    pending_tr = user_data["pending_trainings"]
    bgc = user_data["bgc_status"]
    creds = user_data["credentials_sent"]

    if any(k in p for k in ["pending", "incomplete", "checklist", "remaining"]):
        items = []
        if user_data["profile_created"] != "Yes": items.append("Account Profile creation by HR")
        if bgc.lower() == "pending": items.append("Background Check (BGC) verification")
        if pending_tr: items.append(f"Mandatory Trainings: {', '.join(pending_tr)}")
        if creds != "Yes": items.append("Final Credentials Issuance")
        return f"📋 **Pending Checklist for {name}:**\n- " + "\n- ".join(items) if items else f"🎉 All onboarding steps complete!"

    if any(k in p for k in ["suggest", "next", "what should i do"]):
        if bgc.lower() == "pending":
            return f"💡 **Suggested Next Step:** Upload your government ID to complete your Background Check (BGC)."
        elif pending_tr:
            return f"💡 **Suggested Next Step:** You have **{len(pending_tr)} pending training(s)**: {', '.join(pending_tr)}."
        elif creds != "Yes":
            return f"💡 **Suggested Next Step:** All requirements satisfied! Credentials generation is in progress."
        return f"🌟 You are fully onboarded!"

    return (
        f"Hi {name}! Profile summary from PostgreSQL:\n"
        f"• Profile Created: {user_data['profile_created']}\n"
        f"• BGC Status: {user_data['bgc_status']}\n"
        f"• Assigned Trainings: {len(user_data['trainings'])} total ({len(pending_tr)} pending)\n"
        f"• Credentials: {user_data['credentials_sent']}"
    )

# ==========================================
# 6. WEB INTERFACE (HTML + TAILWIND)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vanguard Portal (PostgreSQL Connected)</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 min-h-screen font-sans">
    <div class="max-w-5xl mx-auto py-8 px-4">
        
        <!-- LOGIN CARD -->
        <div id="loginCard" class="max-w-md mx-auto bg-white p-8 rounded-xl shadow border mt-10">
            <h2 class="text-2xl font-bold text-slate-800 text-center mb-1">🐘 Vanguard Portal</h2>
            <p class="text-slate-500 text-sm text-center mb-6">Connected to PostgreSQL Database</p>
            <input id="emailInput" type="email" value="shaikbaji331@gmail.com" placeholder="name@example.com" class="w-full border px-4 py-2 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500 outline-none">
            <button onclick="login()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg">Access Portal →</button>
            <p id="loginError" class="text-red-500 text-sm mt-3 text-center hidden"></p>
        </div>

        <!-- MAIN DASHBOARD (Hidden Initially) -->
        <div id="dashCard" class="hidden">
            <div class="flex justify-between items-center bg-slate-800 text-white p-4 rounded-t-xl">
                <span class="font-bold text-lg tracking-wide">VANGUARD AGENT PORTAL</span>
                <button onclick="location.reload()" class="text-xs bg-slate-700 px-3 py-1.5 rounded hover:bg-slate-600">Log Out</button>
            </div>

            <div class="bg-white p-6 rounded-b-xl shadow mb-6">
                <!-- User Header -->
                <div class="flex flex-wrap justify-between items-center mb-6 pb-4 border-b">
                    <div>
                        <h1 id="userName" class="text-2xl font-bold text-slate-800">Welcome</h1>
                        <p id="userEmail" class="text-sm text-blue-600 font-medium"></p>
                    </div>
                    <button onclick="fetchUpdates()" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold px-4 py-2 rounded-lg border">🔄 Sync Database</button>
                </div>

                <!-- Proactive Recommendation Banner -->
                <div id="agentBanner" class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded-r-lg">
                    <div class="flex items-start">
                        <span class="text-xl mr-3">🤖</span>
                        <div>
                            <h4 class="font-bold text-blue-900 text-sm">Agent Recommendation:</h4>
                            <p id="bannerText" class="text-sm text-blue-800 mt-1">Analyzing database record...</p>
                        </div>
                    </div>
                </div>

                <!-- 2-COLUMN GRID -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <!-- LEFT COLUMN: STATUS CARDS -->
                    <div class="space-y-4">
                        <h3 class="text-sm font-bold uppercase text-slate-500 tracking-wider">Live Database Status</h3>
                        
                        <div class="border p-4 rounded-lg bg-slate-50">
                            <h4 class="font-bold text-slate-700 mb-2">1. Profile & Welcome</h4>
                            <div class="flex justify-between text-sm py-1 border-b"><span>Profile Created:</span><span id="badgeProfile"></span></div>
                            <div class="flex justify-between text-sm py-1"><span>Welcome Email:</span><span id="badgeWelcome"></span></div>
                        </div>

                        <div class="border p-4 rounded-lg bg-slate-50">
                            <h4 class="font-bold text-slate-700 mb-2">2. Verification</h4>
                            <div class="flex justify-between text-sm py-1"><span>BGC Status:</span><span id="badgeBgc"></span></div>
                        </div>

                        <!-- DYNAMIC TRAININGS CARD (Rendered from DB) -->
                        <div class="border p-4 rounded-lg bg-slate-50">
                            <div class="flex justify-between items-center mb-2">
                                <h4 class="font-bold text-slate-700">3. Assigned Trainings</h4>
                                <span id="trainingsCount" class="text-xs text-slate-500 font-semibold"></span>
                            </div>
                            <div id="trainingsGrid" class="grid grid-cols-1 gap-2 text-xs">
                                <!-- Dynamically generated badges from PostgreSQL -->
                            </div>
                        </div>

                        <div class="border p-4 rounded-lg bg-slate-50">
                            <h4 class="font-bold text-slate-700 mb-2">4. Credentials</h4>
                            <div class="flex justify-between text-sm py-1"><span>Credentials Sent:</span><span id="badgeCreds"></span></div>
                        </div>
                    </div>

                    <!-- RIGHT COLUMN: INTERACTIVE AGENT CHAT -->
                    <div class="border rounded-xl p-4 bg-slate-50 flex flex-col h-[520px]">
                        <div class="flex items-center mb-3">
                            <span class="text-xl mr-2">💬</span>
                            <h3 class="font-bold text-slate-800 text-sm">Ask Onboarding Agent</h3>
                        </div>

                        <!-- Quick Prompts -->
                        <div class="flex flex-wrap gap-1.5 mb-3">
                            <button onclick="askPrompt('What is pending for me?')" class="text-xs bg-white border hover:bg-blue-50 text-slate-600 px-2.5 py-1 rounded-full shadow-sm">📋 What's pending?</button>
                            <button onclick="askPrompt('Suggest next steps')" class="text-xs bg-white border hover:bg-blue-50 text-slate-600 px-2.5 py-1 rounded-full shadow-sm">💡 Suggest next step</button>
                        </div>

                        <!-- Chat History -->
                        <div id="chatHistory" class="flex-1 bg-white border rounded-lg p-3 overflow-y-auto text-sm space-y-3 mb-3">
                            <div class="bg-blue-50 text-blue-900 p-2.5 rounded-lg text-xs">
                                👋 Connected to PostgreSQL! Ask me any questions about your onboarding status.
                            </div>
                        </div>

                        <!-- Chat Input -->
                        <div class="flex gap-2">
                            <input id="promptInput" type="text" placeholder="Type a prompt (e.g. 'What is pending?')..." class="flex-1 border px-3 py-2 text-sm rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" onkeydown="if(event.key==='Enter') sendPrompt()">
                            <button onclick="sendPrompt()" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg">Send</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentUser = "";

        function makeBadge(val) {
            let color = "bg-amber-100 text-amber-800";
            let v = val ? val.toString().trim() : "Pending";
            if (["yes", "completed", "verified", "passed"].includes(v.toLowerCase())) {
                color = "bg-green-100 text-green-800";
            } else if (["no", "rejected", "failed"].includes(v.toLowerCase())) {
                color = "bg-red-100 text-red-800";
            }
            return `<span class="px-2 py-0.5 rounded text-xs font-semibold ${color}">${v}</span>`;
        }

        async function login() {
            const email = document.getElementById("emailInput").value.trim();
            if (!email) return;
            currentUser = email;
            await fetchUpdates();
        }

        async function fetchUpdates() {
            const res = await fetch(`/api/user?email=${encodeURIComponent(currentUser)}`);
            const data = await res.json();
            if (!data.success) {
                document.getElementById("loginError").innerText = data.error;
                document.getElementById("loginError").classList.remove("hidden");
                return;
            }

            document.getElementById("loginCard").classList.add("hidden");
            document.getElementById("dashCard").classList.remove("hidden");

            const u = data.user;
            document.getElementById("userName").innerText = `Welcome, ${u.name}`;
            document.getElementById("userEmail").innerText = u.email;

            document.getElementById("badgeProfile").innerHTML = makeBadge(u.profile_created);
            document.getElementById("badgeWelcome").innerHTML = makeBadge(u.welcome_sent);
            document.getElementById("badgeBgc").innerHTML = makeBadge(u.bgc_status);
            document.getElementById("badgeCreds").innerHTML = makeBadge(u.credentials_sent);

            // Dynamically Render Trainings List from PostgreSQL
            const grid = document.getElementById("trainingsGrid");
            grid.innerHTML = "";
            let completedCount = 0;
            
            u.trainings.forEach(t => {
                if (t.status.toLowerCase() === "completed") completedCount++;
                const item = document.createElement("div");
                item.className = "flex justify-between items-center p-2 bg-white rounded border shadow-sm";
                item.innerHTML = `<span>${t.name}</span> ${makeBadge(t.status)}`;
                grid.appendChild(item);
            });

            document.getElementById("trainingsCount").innerText = `${completedCount} of ${u.trainings.length} completed`;

            // Proactive AI Suggestion from Agent
            const sugRes = await fetch(`/api/chat`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ email: currentUser, prompt: "suggest next steps" })
            });
            const sugData = await sugRes.json();
            if (sugData.reply) {
                document.getElementById("bannerText").innerText = sugData.reply.replace(/[*#]/g, '');
            }
        }

        function appendMessage(sender, text) {
            const box = document.getElementById("chatHistory");
            const div = document.createElement("div");
            if (sender === "user") {
                div.className = "bg-slate-100 text-slate-800 p-2.5 rounded-lg text-xs self-end ml-8";
                div.innerHTML = `<strong>You:</strong> ${text}`;
            } else {
                div.className = "bg-blue-50 text-blue-900 p-2.5 rounded-lg text-xs mr-8 whitespace-pre-wrap";
                div.innerHTML = `<strong>Agent:</strong>\n${text}`;
            }
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        function askPrompt(p) {
            document.getElementById("promptInput").value = p;
            sendPrompt();
        }

        async function sendPrompt() {
            const input = document.getElementById("promptInput");
            const prompt = input.value.trim();
            if (!prompt) return;
            input.value = "";
            appendMessage("user", prompt);

            const res = await fetch(`/api/chat`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ email: currentUser, prompt: prompt })
            });
            const data = await res.json();
            appendMessage("agent", data.reply || "Could not fetch details.");
        }
    </script>
</body>
</html>
"""

# ==========================================
# 7. FLASK ROUTES
# ==========================================
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/user")
def api_user():
    email = request.args.get("email")
    if not email:
        return jsonify({"success": False, "error": "Email is required"})
    record, event = get_user_data(email)
    if not record:
        return jsonify({"success": False, "error": event or f"User '{email}' not found"})
    return jsonify({"success": True, "user": record, "event": event})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    email = data.get("email")
    prompt = data.get("prompt")
    
    if not email or not prompt:
        return jsonify({"reply": "Missing email or prompt."})

    record, _ = get_user_data(email)
    if not record:
        return jsonify({"reply": "User not found in PostgreSQL database."})

    reply = generate_agent_response(record, prompt)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
