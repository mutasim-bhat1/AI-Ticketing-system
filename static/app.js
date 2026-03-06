/* ════════════════════════════════════════════════════════════
   AI TICKETING SYSTEM — Dashboard Application Logic
   ════════════════════════════════════════════════════════════ */

const API_URL = "http://127.0.0.1:8000";

// ─── State ─────────────────────────────────────────────────
let tickets = [];
let activityLog = [];
let ticketCounter = 0;
let chatCounter = 0;
let currentView = "dashboard";
let currentRole = "admin";
let dashboardMode = "table";
let dashboardFilter = "all";

const PANELS = ["panel-dashboard", "panel-tickets", "panel-chat"];

// ─── Init ──────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadState();
  loadTheme();

  const selector = document.getElementById("role-selector");
  if (selector) currentRole = selector.value;

  applyRoleVisibility();
  switchView(currentRole === "user" ? "chat" : "dashboard");

  document.querySelectorAll(".nav-item[data-view]").forEach(item => {
    item.addEventListener("click", () => {
      if (currentRole === "user" && item.dataset.view === "dashboard") return;
      switchView(item.dataset.view);
    });
  });

  document.getElementById("global-search")?.addEventListener("input", handleSearch);

  // Keyboard shortcuts
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeModal();
  });
});

// ─── Theme ─────────────────────────────────────────────────
function toggleTheme() {
  const next = (document.documentElement.getAttribute("data-theme") || "light") === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("ai_desk_theme", next);
  updateThemeIcon(next);
}

function loadTheme() {
  const saved = localStorage.getItem("ai_desk_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeIcon(saved);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById("theme-icon");
  if (icon) icon.className = theme === "dark" ? "ri-sun-line" : "ri-moon-line";
}

// ─── Toast Notifications ───────────────────────────────────
function showToast(message, type = "success", icon = "ri-checkbox-circle-line") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="${icon}"></i><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 4200);
}

// ─── Role Switching ────────────────────────────────────────
function switchRole(role) {
  currentRole = role;
  applyRoleVisibility();
  switchView(role === "admin" ? "dashboard" : "chat");
}

function applyRoleVisibility() {
  document.querySelectorAll(".admin-only").forEach(el => el.style.display = currentRole === "admin" ? "flex" : "none");
  document.querySelectorAll(".user-only").forEach(el => el.style.display = currentRole === "user" ? "flex" : "none");
  document.querySelectorAll(".admin-col").forEach(el => el.style.display = currentRole === "admin" ? "" : "none");

  const statsRow = document.querySelector(".stats-row");
  if (statsRow) statsRow.style.display = currentRole === "admin" ? "grid" : "none";

  const ticketLabel = document.getElementById("tickets-nav-label");
  const allTitle = document.getElementById("all-tickets-title");
  if (ticketLabel) ticketLabel.textContent = currentRole === "admin" ? "All Tickets" : "My Tickets";
  if (allTitle) allTitle.textContent = currentRole === "admin" ? "All Tickets" : "My Tickets";

  const avatar = document.getElementById("user-avatar-icon");
  const name = document.getElementById("user-display-name");
  const role = document.getElementById("user-display-role");

  if (currentRole === "admin") {
    avatar.textContent = "AD"; name.textContent = "Admin User"; role.textContent = "System Administrator";
    avatar.style.background = "linear-gradient(135deg, var(--accent-blue), var(--accent-purple))";
  } else {
    avatar.textContent = "US"; name.textContent = "Normal User"; role.textContent = "Student / Employee";
    avatar.style.background = "linear-gradient(135deg, var(--accent-teal), var(--accent-green))";
    updateUserSummary();
  }

  // Quick actions visibility (inside chat panel, user only)
  const qa = document.getElementById("card-quick-actions");
  if (qa) qa.style.display = currentRole === "user" ? "block" : "none";
}

// ─── View Switching ────────────────────────────────────────
function switchView(view) {
  currentView = view;
  PANELS.forEach(id => { const el = document.getElementById(id); if (el) el.style.display = "none"; });
  const target = document.getElementById("panel-" + view);
  if (target) target.style.display = "block";

  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const navItem = document.querySelector(`.nav-item[data-view="${view}"]`);
  if (navItem) navItem.classList.add("active");

  // Sidebar: show only for user on chat
  const sidebar = document.getElementById("content-sidebar");
  if (sidebar) sidebar.classList.toggle("hidden", !(currentRole === "user" && view === "chat"));

  if (view === "chat") setTimeout(() => document.getElementById("chat-input")?.focus(), 100);
  if (view === "tickets") renderTickets();
  if (view === "dashboard") { updateStats(); renderDashboard(); renderActivity(); }
}

// ─── Search ────────────────────────────────────────────────
function handleSearch(e) {
  const query = e.target.value.toLowerCase().trim();
  const filtered = query
    ? tickets.filter(t =>
        t.subject?.toLowerCase().includes(query) ||
        t.department?.toLowerCase().includes(query) ||
        t.id?.includes(query) ||
        t.intent?.toLowerCase().includes(query)
      )
    : [...tickets];

  if (currentView === "dashboard") {
    const tbody = document.getElementById("tickets-tbody");
    const emptyEl = document.getElementById("tickets-empty");
    if (filtered.length === 0) { tbody.innerHTML = ""; emptyEl.style.display = "block"; }
    else { emptyEl.style.display = "none"; tbody.innerHTML = filtered.reverse().slice(0, 12).map(t => ticketRowHTML(t)).join(""); }
  } else if (currentView === "tickets") {
    const tbody = document.getElementById("all-tickets-tbody");
    const emptyEl = document.getElementById("all-tickets-empty");
    if (filtered.length === 0) { tbody.innerHTML = ""; emptyEl.style.display = "block"; }
    else { emptyEl.style.display = "none"; tbody.innerHTML = filtered.reverse().map(t => allTicketRowHTML(t, currentRole === "admin", currentRole === "admin")).join(""); }
  }
}

// ─── Dashboard Stats ───────────────────────────────────────
function updateStats() {
  const el = id => document.getElementById(id);
  el("stat-total").textContent = tickets.length;
  el("stat-pending").textContent = tickets.filter(t => t.status === "open" || t.status === "pending").length;
  el("stat-resolved").textContent = tickets.filter(t => t.status === "resolved").length;
  el("stat-escalated").textContent = tickets.filter(t => t.status === "escalated").length;
  el("stat-chats").textContent = chatCounter;
  el("ticket-count-badge").textContent = tickets.length;
  el("recent-count-badge").textContent = tickets.length;
  el("all-tickets-badge").textContent = tickets.length;
}

function updateUserSummary() {
  const el = id => document.getElementById(id);
  if (el("user-stat-open")) el("user-stat-open").textContent = tickets.filter(t => t.status === "open" || t.status === "pending").length;
  if (el("user-stat-resolved")) el("user-stat-resolved").textContent = tickets.filter(t => t.status === "resolved").length;
  if (el("user-stat-chats")) el("user-stat-chats").textContent = chatCounter;
}

// ─── Dashboard: Filter & Mode ──────────────────────────────
function filterDashboardByStatus(status) {
  dashboardFilter = status;

  // Highlight active stat card
  document.querySelectorAll(".stat-card").forEach(c => c.classList.remove("active-filter"));
  const cardMap = { all: "stat-card-all", pending: "stat-card-pending", resolved: "stat-card-resolved", escalated: "stat-card-escalated" };
  const activeCard = document.getElementById(cardMap[status]);
  if (activeCard && status !== "all") activeCard.classList.add("active-filter");

  // Filter chip
  const chip = document.getElementById("filter-chip");
  const chipText = document.getElementById("filter-chip-text");
  if (status !== "all") {
    chip.style.display = "inline-flex";
    chipText.textContent = capitalize(status);
  } else {
    chip.style.display = "none";
  }

  renderDashboard();
}

function clearDashboardFilter() {
  dashboardFilter = "all";
  document.querySelectorAll(".stat-card").forEach(c => c.classList.remove("active-filter"));
  document.getElementById("filter-chip").style.display = "none";
  renderDashboard();
}

function setDashboardMode(mode, btn) {
  dashboardMode = mode;
  document.querySelectorAll("#tabs-dashboard .view-tab").forEach(t => t.classList.remove("active"));
  if (btn) btn.classList.add("active");
  document.getElementById("dashboard-table-container").style.display = (mode === "table") ? "block" : "none";
  document.getElementById("dashboard-cards-container").style.display = (mode === "cards") ? "block" : "none";
  renderDashboard();
}

// ─── Render Dashboard ──────────────────────────────────────
function renderDashboard() {
  let data = [...tickets].reverse();
  if (dashboardFilter === "pending") data = data.filter(t => t.status === "open" || t.status === "pending");
  else if (dashboardFilter === "resolved") data = data.filter(t => t.status === "resolved");
  else if (dashboardFilter === "escalated") data = data.filter(t => t.status === "escalated");

  const recent = data.slice(0, 12);
  const tbody = document.getElementById("tickets-tbody");
  const emptyTable = document.getElementById("tickets-empty");
  if (recent.length === 0) { tbody.innerHTML = ""; emptyTable.style.display = "block"; }
  else { emptyTable.style.display = "none"; tbody.innerHTML = recent.map(t => ticketRowHTML(t)).join(""); }

  const grid = document.getElementById("ticket-cards-grid");
  const emptyCards = document.getElementById("cards-empty");
  if (recent.length === 0) { grid.innerHTML = ""; emptyCards.style.display = "block"; }
  else { emptyCards.style.display = "none"; grid.innerHTML = recent.map(t => ticketCardHTML(t)).join(""); }
}

function ticketRowHTML(t) {
  return `<tr onclick="openTicketModal('${t.id}')">
    <td><span class="ticket-id">#${t.id}</span></td>
    <td><span class="ticket-subject">${esc(t.subject)}</span></td>
    <td><span class="ticket-dept">${esc(t.department)}</span></td>
    <td>${statusBadge(t.status)}</td>
    <td>${priorityBadge(t.priority)}</td>
    <td><span class="ticket-time">${fmtTime(t.created)}</span></td>
  </tr>`;
}

function allTicketRowHTML(t, showP, showE) {
  return `<tr onclick="openTicketModal('${t.id}')">
    <td><span class="ticket-id">#${t.id}</span></td>
    <td><span class="ticket-subject">${esc(t.subject)}</span></td>
    <td><span class="ticket-dept">${esc(t.department)}</span></td>
    ${showE ? `<td><span class="ticket-dept">${esc(t.email)}</span></td>` : ""}
    <td>${statusBadge(t.status)}</td>
    ${showP ? `<td>${priorityBadge(t.priority)}</td>` : ""}
    <td><span class="ticket-time">${fmtTime(t.created)}</span></td>
  </tr>`;
}

function ticketCardHTML(t) {
  return `<div class="ticket-card" onclick="openTicketModal('${t.id}')">
    <div class="ticket-card-top ${t.priority}"><span>${cap(t.priority)} Priority</span>${statusBadge(t.status)}</div>
    <div class="ticket-card-body">
      <h4>${esc(t.subject)}</h4>
      <div class="ticket-card-meta"><i class="ri-building-2-line"></i> ${esc(t.department)}</div>
      <div class="ticket-card-meta"><i class="ri-mail-line"></i> ${esc(t.email)}</div>
    </div>
    <div class="ticket-card-footer"><span class="card-id">#${t.id}</span><span class="card-time">${fmtTime(t.created)}</span></div>
  </div>`;
}

function statusBadge(s) { return `<span class="status-badge ${s}"><span class="dot"></span> ${cap(s)}</span>`; }
function priorityBadge(p) { return `<span class="priority-badge ${p}">${{urgent:"🔴",high:"🟠",medium:"🔵",low:"🟢"}[p]||"⚪"} ${cap(p)}</span>`; }

// ─── Render Tickets (All/My) ───────────────────────────────
function renderTickets() {
  const deptF = document.getElementById("filter-dept")?.value || "all";
  const statusF = document.getElementById("filter-status")?.value || "all";
  let filtered = [...tickets];
  if (deptF !== "all") filtered = filtered.filter(t => t.department === deptF);
  if (statusF !== "all") filtered = filtered.filter(t => t.status === statusF);

  const tbody = document.getElementById("all-tickets-tbody");
  const emptyEl = document.getElementById("all-tickets-empty");
  if (filtered.length === 0) { tbody.innerHTML = ""; emptyEl.style.display = "block"; return; }
  emptyEl.style.display = "none";
  filtered.reverse();
  tbody.innerHTML = filtered.map(t => allTicketRowHTML(t, currentRole === "admin", currentRole === "admin")).join("");
}

// ─── Chat ──────────────────────────────────────────────────
async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const query = input.value.trim();
  if (!query) return;

  input.value = "";
  addChatBubble("user", query);
  const typingEl = addTypingIndicator();
  const sendBtn = document.getElementById("chat-send-btn");
  sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    removeTypingIndicator(typingEl);

    if (data.status === "success") {
      addChatBubble("bot", data.response);
      if (data.tickets_created && data.tickets_created.length > 0) {
        data.tickets_created.forEach(t => {
          ticketCounter++;
          const ticket = {
            id: String(ticketCounter).padStart(4, "0"),
            subject: t.service || t.intent || query,
            intent: t.intent || query,
            department: extractDept(t.service),
            email: t.email || "N/A",
            status: t.log?.includes("Escalated") ? "escalated" : "open",
            priority: guessPriority(t.intent || query),
            response: data.response,
            created: new Date().toISOString(),
            log: t.log || "",
          };
          tickets.push(ticket);
          addActivity("email", `Ticket <strong>#${ticket.id}</strong> created — ${ticket.department}`);
          showToast(`Ticket #${ticket.id} created for ${ticket.department}`, "success", "ri-ticket-line");
        });
      } else {
        chatCounter++;
        addActivity("chat-act", "AI answered a general query");
      }
    } else {
      addChatBubble("bot", `⚠️ Error: ${data.error || "Something went wrong."}`);
      showToast("Something went wrong", "error", "ri-error-warning-line");
    }
  } catch (err) {
    removeTypingIndicator(typingEl);
    addChatBubble("bot", `❌ Could not connect to the server.`);
    showToast("Connection failed", "error", "ri-wifi-off-line");
  }

  sendBtn.disabled = false;
  saveState(); updateStats(); updateUserSummary(); renderDashboard(); renderActivity();
}

function addChatBubble(role, text) {
  const container = document.getElementById("chat-messages");
  const icon = role === "bot" ? "ri-robot-2-line" : "ri-user-3-line";
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const div = document.createElement("div");
  div.className = `chat-message ${role}`;
  div.innerHTML = `<div class="msg-avatar"><i class="${icon}"></i></div><div class="msg-bubble">${fmtChat(text)}<div class="msg-time">${now}</div></div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function addTypingIndicator() {
  const container = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "chat-message bot"; div.id = "typing-indicator";
  div.innerHTML = `<div class="msg-avatar"><i class="ri-robot-2-line"></i></div><div class="msg-bubble"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function removeTypingIndicator(el) { if (el?.parentNode) el.parentNode.removeChild(el); }
function fmtChat(text) { return esc(text).replace(/\n/g, "<br>").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>"); }

function quickQuery(query) {
  switchView("chat");
  setTimeout(() => { document.getElementById("chat-input").value = query; sendChatMessage(); }, 200);
}

// ─── Activity Feed ─────────────────────────────────────────
function addActivity(iconClass, text) {
  activityLog.unshift({ icon: iconClass, text, time: new Date().toISOString() });
  if (activityLog.length > 20) activityLog.pop();
}

function renderActivity() {
  const feed = document.getElementById("activity-feed");
  if (!feed) return;
  if (activityLog.length === 0) {
    feed.innerHTML = `<div class="empty-state" style="padding:20px 0"><i class="ri-history-line"></i><p>No recent activity</p></div>`;
    return;
  }
  const iconMap = { email: "ri-mail-send-line", resolve: "ri-checkbox-circle-line", warn: "ri-error-warning-line", "chat-act": "ri-chat-3-line" };
  feed.innerHTML = activityLog.slice(0, 8).map(a => `
    <div class="activity-item">
      <div class="activity-icon ${a.icon}"><i class="${iconMap[a.icon] || "ri-information-line"}"></i></div>
      <div><div class="activity-text">${a.text}</div><div class="activity-time">${fmtTime(a.time)}</div></div>
    </div>
  `).join("");
}

// ─── Ticket Modal ──────────────────────────────────────────
function openTicketModal(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) return;
  const isAdmin = currentRole === "admin";

  document.getElementById("modal-title").textContent = `Ticket #${t.id}`;
  document.getElementById("modal-body").innerHTML = `
    <div class="modal-field"><label>Subject</label><div class="value">${esc(t.subject)}</div></div>
    <div class="modal-field"><label>Department</label><div class="value">${esc(t.department)}</div></div>
    ${isAdmin ? `<div class="modal-field"><label>Email</label><div class="value">${esc(t.email)}</div></div>` : ""}
    <div class="modal-field"><label>Status</label><div class="value">${statusBadge(t.status)}</div></div>
    ${isAdmin ? `<div class="modal-field"><label>Priority</label><div class="value">${priorityBadge(t.priority)}</div></div>` : ""}
    <div class="modal-field"><label>Created</label><div class="value">${new Date(t.created).toLocaleString()}</div></div>
    <div class="modal-field"><label>AI Response</label><div class="value" style="white-space:pre-wrap;background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);font-size:12.5px;max-height:200px;overflow-y:auto">${esc(t.response||"N/A")}</div></div>
    ${isAdmin ? `<div class="modal-field"><label>Log</label><div class="value" style="font-size:12px;color:var(--text-muted)">${esc(t.log||"N/A")}</div></div>` : ""}
    <div style="display:flex;gap:8px;margin-top:20px">
      ${isAdmin && t.status !== "resolved" ? `<button class="btn btn-primary" onclick="markResolved('${t.id}')"><i class="ri-checkbox-circle-line"></i> Mark Resolved</button>` : ""}
      <button class="btn btn-outline" onclick="closeModal()">Close</button>
    </div>
  `;
  document.getElementById("ticket-modal").classList.add("active");
}

function closeModal() { document.getElementById("ticket-modal").classList.remove("active"); }

function markResolved(id) {
  const t = tickets.find(x => x.id === id);
  if (t) {
    t.status = "resolved";
    addActivity("resolve", `Ticket <strong>#${id}</strong> marked as resolved`);
    showToast(`Ticket #${id} resolved`, "success", "ri-checkbox-circle-line");
    saveState(); updateStats(); updateUserSummary(); renderDashboard(); renderTickets(); renderActivity(); closeModal();
  }
}

document.getElementById("ticket-modal")?.addEventListener("click", e => { if (e.target.id === "ticket-modal") closeModal(); });

// ─── Refresh ───────────────────────────────────────────────
function refreshDashboard() {
  updateStats(); updateUserSummary(); renderDashboard(); renderTickets(); renderActivity();
  showToast("Dashboard refreshed", "success", "ri-refresh-line");
}

// ─── Persistence ───────────────────────────────────────────
function saveState() {
  localStorage.setItem("ai_desk_tickets", JSON.stringify(tickets));
  localStorage.setItem("ai_desk_activity", JSON.stringify(activityLog));
  localStorage.setItem("ai_desk_ticket_counter", ticketCounter);
  localStorage.setItem("ai_desk_chat_counter", chatCounter);
}

function loadState() {
  try {
    const t = localStorage.getItem("ai_desk_tickets");
    const a = localStorage.getItem("ai_desk_activity");
    if (t) tickets = JSON.parse(t);
    if (a) activityLog = JSON.parse(a);
    ticketCounter = parseInt(localStorage.getItem("ai_desk_ticket_counter") || "0");
    chatCounter = parseInt(localStorage.getItem("ai_desk_chat_counter") || "0");
  } catch (e) { console.error("State load error:", e); }
}

// ─── Utilities ─────────────────────────────────────────────
function esc(text) {
  if (!text) return "";
  return String(text).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;");
}

function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }

function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const m = Math.floor((Date.now() - d) / 60000);
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function extractDept(service) {
  if (!service) return "General Support";
  const s = service.toLowerCase();
  if (/password|software|network|it/.test(s)) return "IT Support";
  if (/fee|payment|refund|finance/.test(s)) return "Finance";
  if (/bus|transport|route/.test(s)) return "Transport";
  if (/library|book/.test(s)) return "Library";
  if (/course|exam|academic|grade/.test(s)) return "Academics";
  if (/complaint|harassment/.test(s)) return "Student Affairs";
  return "General Support";
}

function guessPriority(intent) {
  if (!intent) return "medium";
  const i = intent.toLowerCase();
  if (/urgent|emergency|harassment|blocked/.test(i)) return "urgent";
  if (/payment|password|locked|refund/.test(i)) return "high";
  if (/bus|schedule|library/.test(i)) return "low";
  return "medium";
}
