import os
import openpyxl
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify, render_template_string

# ==========================================
# 1. CONFIGURATION
# ==========================================
EXCEL_FILE = r"C:\Users\91860\Downloads\OnBoarding Agent data\Vanguard_Onboarding.xlsx"
EMAIL_ADDRESS = "shaikbaji860566@gmail.com"  # Your sender email
EMAIL_PASSWORD = "" # The App Password you generated
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# (Optional) Add your Gemini API key here for full conversational LLM capabilities,
# or leave it empty to use the built-in intelligent rule-based agent!
GEMINI_API_KEY = ""

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to Vanguard, {Name}! Action Required",
        "body": "Hi {Name},\n\nWelcome to Vanguard! Your account profile has been created.\n\nPlease upload BGC documents.\n\nBest,\nTeam"
    }
}

app = Flask(__name__)

# ==========================================
# 2. HELPERS & AUTOMATION ENGINE
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
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def get_user_data(target_user):
    target = target_user.strip().lower()
    if not os.path.exists(EXCEL_FILE):
        return None, "Excel file not found"
    
    try:
        wb = openpyxl.load_workbook(EXCEL_FILE)
    except PermissionError:
        return None, "Excel is open in another app. Please close it."

    sheet = wb.active
    record = None
    event_msg = None

    for i in range(2, sheet.max_row + 1):
        name = clean_val(sheet.cell(row=i, column=1).value)
        email = clean_val(sheet.cell(row=i, column=2).value)
        if not email: continue

        if email.lower() == target or name.lower() == target:
            profile_created = sheet.cell(row=i, column=3).value
            bgc_status = clean_val(sheet.cell(row=i, column=4).value) or "Pending"
            onboarding_status = clean_val(sheet.cell(row=i, column=5).value) or "In Progress"
            welcome_sent = sheet.cell(row=i, column=6).value

            # Automated Welcome Trigger
            if is_yes(profile_created) and not is_yes(welcome_sent):
                if send_email(email, name, "welcome"):
                    sheet.cell(row=i, column=6).value = "Yes"
                    welcome_sent = "Yes"
                    wb.save(EXCEL_FILE)
                    event_msg = f"Welcome email sent to {name}!"

            info_sec = clean_val(sheet.cell(row=i, column=10).value) or "Pending"
            conduct = clean_val(sheet.cell(row=i, column=11).value) or "Pending"
            posh = clean_val(sheet.cell(row=i, column=12).value) or "Pending"
            privacy = clean_val(sheet.cell(row=i, column=13).value) or "Pending"
            creds = clean_val(sheet.cell(row=i, column=9).value)

            # Determine pending items
            pending_trainings = []
            if info_sec.lower() != "completed" and not is_yes(info_sec): pending_trainings.append("Information Security")
            if conduct.lower() != "completed" and not is_yes(conduct): pending_trainings.append("Code of Conduct")
            if posh.lower() != "completed" and not is_yes(posh): pending_trainings.append("POSH")
            if privacy.lower() != "completed" and not is_yes(privacy): pending_trainings.append("Data Privacy")

            record = {
                "name": name,
                "email": email,
                "profile_created": "Yes" if is_yes(profile_created) else "Pending",
                "welcome_sent": "Yes" if is_yes(welcome_sent) else "Pending",
                "bgc_status": bgc_status,
                "onboarding_status": onboarding_status,
                "info_sec": info_sec,
                "code_of_conduct": conduct,
                "posh": posh,
                "data_privacy": privacy,
                "credentials_sent": "Yes" if is_yes(creds) else "Pending",
                "pending_trainings": pending_trainings
            }
            break

    return record, event_msg

# ==========================================
# 3. AI AGENT ENGINE (PROMPT & SUGGESTIONS)
# ==========================================
def generate_agent_response(user_data, prompt):
    """
    Answers user queries based on their Excel record and suggests next steps.
    """
    p = prompt.strip().lower()
    name = user_data["name"]
    pending_tr = user_data["pending_trainings"]
    bgc = user_data["bgc_status"]
    creds = user_data["credentials_sent"]

    # 1. Check for Pending Items / Status
    if any(k in p for k in ["pending", "incomplete", "what is left", "checklist", "remaining"]):
        items = []
        if user_data["profile_created"] != "Yes":
            items.append("Account Profile creation by HR")
        if bgc.lower() == "pending":
            items.append("Background Check (BGC) document verification")
        if pending_tr:
            items.append(f"Mandatory Trainings: {', '.join(pending_tr)}")
        if creds != "Yes":
            items.append("Final Credentials Issuance")
        
        if not items:
            return f"🎉 Great news {name}! You have no pending items. Your onboarding is 100% complete!"
        return f"📋 **Pending Checklist for {name}:**\n- " + "\n- ".join(items)

    # 2. Suggestions / Next Steps
    if any(k in p for k in ["suggest", "next", "what should i do", "action", "recommend", "how to"]):
        if bgc.lower() == "pending":
            return f"💡 **Suggested Next Step:** Your BGC is currently **Pending**. Please upload your government ID and address proofs to the BGC portal to avoid delays."
        elif pending_tr:
            return f"💡 **Suggested Next Step:** You have **{len(pending_tr)} pending training(s)**: {', '.join(pending_tr)}. Completing these will unblock your credentials!"
        elif creds != "Yes":
            return f"💡 **Suggested Next Step:** All your trainings and BGC are verified! Your credentials are being generated by IT and will be sent shortly."
        else:
            return f"🌟 You are fully onboarded! Reach out to your project manager for project assignments."

    # 3. Training questions
    if any(k in p for k in ["training", "posh", "infosec", "conduct", "privacy"]):
        if not pending_tr:
            return f"✅ All 4 mandatory trainings (InfoSec, Code of Conduct, POSH, Data Privacy) are **Completed**!"
        return f"📚 **Training Status:** You have completed {4 - len(pending_tr)} of 4 trainings.\nStill pending: **{', '.join(pending_tr)}**."

    # 4. BGC questions
    if any(k in p for k in ["bgc", "background", "document", "verification"]):
        if bgc.lower() in ["completed", "verified"]:
            return f"✅ Your Background Check (BGC) is **Verified and Cleared**."
        return f"⏳ Your Background Check is currently **{bgc}**. Please ensure all required identity and address proofs are submitted."

    # 5. Credentials questions
    if any(k in p for k in ["credential", "password", "login", "access"]):
        if creds == "Yes":
            return f"🔑 Your credentials have been issued and sent to {user_data['email']}!"
        reasons = []
        if bgc.lower() == "pending": reasons.append("BGC verification")
        if pending_tr: reasons.append("Mandatory trainings")
        return f"🔒 Credentials cannot be released yet. They require: {', '.join(reasons) if reasons else 'final IT approval'}."

    # General Overview
    return (
        f"Hi {name}! Here is a quick summary of your profile:\n"
        f"• Profile: {user_data['profile_created']}\n"
        f"• BGC Status: {user_data['bgc_status']}\n"
        f"• Pending Trainings: {len(pending_tr)} left\n"
        f"• Credentials: {user_data['credentials_sent']}\n\n"
        f"Ask me: *'What should I do next?'* or *'What trainings are pending?'*"
    )

# ==========================================
# 4. WEB INTERFACE (HTML + TAILWIND)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vanguard Onboarding Portal & AI Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 min-h-screen font-sans">
    <div class="max-w-5xl mx-auto py-8 px-4">
        
        <!-- LOGIN CARD -->
        <div id="loginCard" class="max-w-md mx-auto bg-white p-8 rounded-xl shadow border mt-10">
            <h2 class="text-2xl font-bold text-slate-800 text-center mb-1">🛡️ Vanguard Portal</h2>
            <p class="text-slate-500 text-sm text-center mb-6">Enter your email to view your profile and chat with the agent</p>
            <input id="emailInput" type="email" value="shaikbaji331@gmail.com" placeholder="name@example.com" class="w-full border px-4 py-2 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500 outline-none">
            <button onclick="login()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg">Access Portal →</button>
            <p id="loginError" class="text-red-500 text-sm mt-3 text-center hidden"></p>
        </div>

        <!-- MAIN DASHBOARD (Hidden Initially) -->
        <div id="dashCard" class="hidden">
            <!-- Navbar -->
            <div class="flex justify-between items-center bg-slate-800 text-white p-4 rounded-t-xl">
                <span class="font-bold text-lg">VANGUARD AGENT PORTAL</span>
                <button onclick="location.reload()" class="text-xs bg-slate-700 px-3 py-1.5 rounded hover:bg-slate-600">Log Out</button>
            </div>

            <div class="bg-white p-6 rounded-b-xl shadow mb-6">
                <!-- User Header -->
                <div class="flex flex-wrap justify-between items-center mb-6 pb-4 border-b">
                    <div>
                        <h1 id="userName" class="text-2xl font-bold text-slate-800">Welcome</h1>
                        <p id="userEmail" class="text-sm text-blue-600 font-medium"></p>
                    </div>
                    <button onclick="fetchUpdates()" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold px-4 py-2 rounded-lg border">🔄 Sync Sheet</button>
                </div>

                <!-- PROACTIVE AGENT SUGGESTION BANNER -->
                <div id="agentBanner" class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded-r-lg">
                    <div class="flex items-start">
                        <span class="text-xl mr-3">🤖</span>
                        <div>
                            <h4 class="font-bold text-blue-900 text-sm">Agent Recommendation for you:</h4>
                            <p id="bannerText" class="text-sm text-blue-800 mt-1">Analyzing your onboarding status...</p>
                        </div>
                    </div>
                </div>

                <!-- 2-COLUMN LAYOUT: CARDS + AI CHAT AGENT -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    
                    <!-- LEFT COLUMN: STATUS CARDS -->
                    <div class="space-y-4">
                        <h3 class="text-sm font-bold uppercase text-slate-500 tracking-wider">Your Live Status</h3>
                        
                        <div class="border p-4 rounded-lg bg-slate-50">
                            <h4 class="font-bold text-slate-700 mb-2">1. Profile & Welcome</h4>
                            <div class="flex justify-between text-sm py-1 border-b"><span>Profile Created:</span><span id="badgeProfile"></span></div>
                            <div class="flex justify-between text-sm py-1"><span>Welcome Email:</span><span id="badgeWelcome"></span></div>
                        </div>

                        <div class="border p-4 rounded-lg bg-slate-50">
                            <h4 class="font-bold text-slate-700 mb-2">2. BGC Verification</h4>
                            <div class="flex justify-between text-sm py-1"><span>Status:</span><span id="badgeBgc"></span></div>
                        </div>

                        <div class="border p-4 rounded-lg bg-slate-50">
                            <h4 class="font-bold text-slate-700 mb-2">3. Mandatory Trainings</h4>
                            <div class="grid grid-cols-2 gap-2 text-xs">
                                <div class="flex justify-between p-1.5 bg-white rounded border"><span>InfoSec:</span><span id="badgeInfoSec"></span></div>
                                <div class="flex justify-between p-1.5 bg-white rounded border"><span>Conduct:</span><span id="badgeConduct"></span></div>
                                <div class="flex justify-between p-1.5 bg-white rounded border"><span>POSH:</span><span id="badgePosh"></span></div>
                                <div class="flex justify-between p-1.5 bg-white rounded border"><span>Privacy:</span><span id="badgePrivacy"></span></div>
                            </div>
                        </div>

                        <div class="border p-4 rounded-lg bg-slate-50">
                            <h4 class="font-bold text-slate-700 mb-2">4. Credentials</h4>
                            <div class="flex justify-between text-sm py-1"><span>Credentials Sent:</span><span id="badgeCreds"></span></div>
                        </div>
                    </div>

                    <!-- RIGHT COLUMN: INTERACTIVE AI PROMPT AGENT -->
                    <div class="border rounded-xl p-4 bg-slate-50 flex flex-col h-[520px]">
                        <div class="flex items-center mb-3">
                            <span class="text-xl mr-2">💬</span>
                            <h3 class="font-bold text-slate-800 text-sm">Ask Onboarding Agent</h3>
                        </div>

                        <!-- Quick Action Chips -->
                        <div class="flex flex-wrap gap-1.5 mb-3">
                            <button onclick="askPrompt('What is pending for me?')" class="text-xs bg-white border hover:bg-blue-50 hover:border-blue-400 text-slate-600 px-2.5 py-1 rounded-full shadow-sm">📋 What's pending?</button>
                            <button onclick="askPrompt('Suggest next steps')" class="text-xs bg-white border hover:bg-blue-50 hover:border-blue-400 text-slate-600 px-2.5 py-1 rounded-full shadow-sm">💡 Suggest next step</button>
                            <button onclick="askPrompt('When will I get my credentials?')" class="text-xs bg-white border hover:bg-blue-50 hover:border-blue-400 text-slate-600 px-2.5 py-1 rounded-full shadow-sm">🔑 Credentials status</button>
                        </div>

                        <!-- Chat Messages History -->
                        <div id="chatHistory" class="flex-1 bg-white border rounded-lg p-3 overflow-y-auto text-sm space-y-3 mb-3">
                            <div class="bg-blue-50 text-blue-900 p-2.5 rounded-lg text-xs leading-relaxed">
                                👋 Hi! I am your Onboarding Agent. You can give me prompts or ask any questions about your sheet details!
                            </div>
                        </div>

                        <!-- Prompt Input Box -->
                        <div class="flex gap-2">
                            <input id="promptInput" type="text" placeholder="Type a prompt (e.g. 'What trainings are pending?')..." class="flex-1 border px-3 py-2 text-sm rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" onkeydown="if(event.key==='Enter') sendPrompt()">
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
            document.getElementById("badgeInfoSec").innerHTML = makeBadge(u.info_sec);
            document.getElementById("badgeConduct").innerHTML = makeBadge(u.code_of_conduct);
            document.getElementById("badgePosh").innerHTML = makeBadge(u.posh);
            document.getElementById("badgePrivacy").innerHTML = makeBadge(u.data_privacy);
            document.getElementById("badgeCreds").innerHTML = makeBadge(u.credentials_sent);

            // Fetch Proactive Recommendation
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
                div.className = "bg-blue-50 text-blue-900 p-2.5 rounded-lg text-xs leading-relaxed mr-8 whitespace-pre-wrap";
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
# 5. API ROUTES
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
        return jsonify({"success": False, "error": f"User '{email}' not found in Excel sheet"})
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
        return jsonify({"reply": "User not found in the sheet."})

    reply = generate_agent_response(record, prompt)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
