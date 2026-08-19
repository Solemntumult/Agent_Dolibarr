/* Application web IFFEN — Agent IA Dolibarr — réalisé par ICT Consulting */
(function () {
  "use strict";

  var API = "/api";
  var AGENT_NAME = "IFFEN";
  var AGENT_AVATAR = "IF";

  var state = {
    token: localStorage.getItem("ict_agent_token") || null,
    user: JSON.parse(localStorage.getItem("ict_agent_user") || "null"),
    conversations: [],
    currentConversationId: null,
    sending: false,
  };

  var TOOL_LABELS = {
    create_client: "Création de client",
    create_quote: "Création de devis",
    create_invoice: "Création de facture",
    log_event: "Journalisation d'un événement agenda",
  };

  var $ = function (id) { return document.getElementById(id); };

  // ------------------------------------------------------------ requêtes API
  function api(path, options) {
    options = options || {};
    var headers = { "Content-Type": "application/json" };
    if (state.token) headers["Authorization"] = "Bearer " + state.token;

    // Abandon après 120 s si le serveur ne répond pas (ex. redémarrage du backend) :
    // sans cela, une requête coupée laissait state.sending à true et bloquait le chat.
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timeoutId = controller ? setTimeout(function () { controller.abort(); }, 120000) : null;

    return fetch(API + path, {
      method: options.method || "GET",
      headers: headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller ? controller.signal : undefined,
    }).then(function (res) {
      if (res.status === 401) { logout(); throw new Error("Session expirée"); }
      return res.json().then(function (data) {
        if (!data.success) throw new Error(data.message || "Erreur");
        return data.data;
      });
    }).finally(function () {
      if (timeoutId) clearTimeout(timeoutId);
    });
  }

  // ------------------------------------------------------------ thème
  function initTheme() {
    var theme = localStorage.getItem("ict_agent_theme") || "dark";
    applyTheme(theme);
  }
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme === "light" ? "light" : "dark");
    localStorage.setItem("ict_agent_theme", theme);
  }
  function toggleMobileSidebar(forceClose) {
    var sidebar = $("sidebar");
    var overlay = $("sidebar-overlay");
    if (!sidebar || !overlay) return;
    var isOpen = sidebar.classList.contains("open");
    if (forceClose || isOpen) {
      sidebar.classList.remove("open");
      overlay.classList.remove("active");
    } else {
      sidebar.classList.add("open");
      overlay.classList.add("active");
    }
  }
  function closeMobileSidebar() {
    toggleMobileSidebar(true);
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    applyTheme(current === "light" ? "dark" : "light");
  }

  // ------------------------------------------------------------ vues
  function showLogin() {
    $("chat-view").classList.add("hidden");
    $("login-view").classList.remove("hidden");
    $("login-view").style.display = "";
  }
  function showChat() {
    $("login-view").classList.add("hidden");
    $("chat-view").classList.remove("hidden");
    $("chat-view").style.display = ""; // lève le display:none inline initial
    $("user-name").textContent = state.user.full_name || state.user.email;
    $("user-role").textContent = state.user.role || "";
    $("user-avatar").textContent = initials(state.user.full_name || state.user.email);
    showView("chat");
    loadConversations();
  }

  function showView(name) {
    closeMobileSidebar();
    var panels = { chat: "chat-panel", dashboard: "dashboard-panel", settings: "settings-panel" };
    Object.keys(panels).forEach(function (key) {
      $(panels[key]).classList.toggle("hidden", key !== name);
    });
    document.querySelectorAll(".menu-item").forEach(function (item) {
      item.classList.toggle("active", item.getAttribute("data-view") === name);
    });
    if (name === "dashboard") loadDashboard();
    if (name === "settings") loadSettings();
  }

  function initials(name) {
    var parts = String(name || "?").trim().split(/\s+/);
    return ((parts[0] || "?").charAt(0) + (parts[1] ? parts[1].charAt(0) : "")).toUpperCase();
  }

  function logout() {
    if (state.token) {
      api("/auth/logout", { method: "POST" }).catch(function () {});
    }
    state.token = null;
    state.user = null;
    localStorage.removeItem("ict_agent_token");
    localStorage.removeItem("ict_agent_user");
    showLogin();
  }

  // ------------------------------------------------------------ conversations
  function loadConversations() {
    api("/chat/conversations").then(function (convs) {
      state.conversations = convs || [];
      renderConversations();
    }).catch(function () {});
  }

  function renderConversations() {
    var list = $("conversation-list");
    list.innerHTML = "";
    if (!state.conversations.length) {
      list.innerHTML = '<div class="conv-empty">Aucune discussion</div>';
      return;
    }
    state.conversations.forEach(function (conv) {
      var item = document.createElement("div");
      item.className = "conv-item" + (conv.id === state.currentConversationId ? " active" : "");
      item.setAttribute("data-id", conv.id);

      var title = document.createElement("span");
      title.className = "conv-title";
      title.textContent = conv.title || "Conversation";

      var actions = document.createElement("span");
      actions.className = "conv-actions";
      actions.innerHTML =
        '<button class="conv-action" data-act="rename" title="Renommer">' + ICONS.pencil + "</button>" +
        '<button class="conv-action danger" data-act="delete" title="Supprimer">' + ICONS.trash + "</button>";

      item.appendChild(title);
      item.appendChild(actions);
      item.addEventListener("click", function (e) {
        if (e.target.closest(".conv-action")) return;
        openConversation(conv.id);
      });
      actions.querySelector('[data-act="rename"]').addEventListener("click", function () {
        renameConversation(conv);
      });
      actions.querySelector('[data-act="delete"]').addEventListener("click", function () {
        deleteConversation(conv);
      });
      list.appendChild(item);
    });
  }

  function renameConversation(conv) {
    var target = document.querySelector('.conv-item[data-id="' + conv.id + '"]');
    if (!target) return;
    if (target.querySelector(".conv-rename-input")) return; // un renommage est déjà en cours

    var input = document.createElement("input");
    input.className = "conv-rename-input";
    input.value = conv.title || "";
    target.querySelector(".conv-title").replaceWith(input);
    target.querySelector(".conv-actions").style.display = "none";
    input.focus();
    input.select();

    function cancel() {
      var span = document.createElement("span");
      span.className = "conv-title";
      span.textContent = conv.title || "Conversation";
      input.replaceWith(span);
      if (target.querySelector(".conv-actions")) target.querySelector(".conv-actions").style.display = "";
    }
    function save() {
      var value = input.value.trim();
      if (value && value !== conv.title) {
        api("/chat/conversations/" + conv.id, { method: "PUT", body: { title: value } })
          .then(function () {
            conv.title = value;
            loadConversations();
          })
          .catch(function (err) {
            cancel();
            alert(err.message || "Impossible de renommer la discussion.");
          });
      } else {
        cancel();
      }
    }
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); save(); }
      if (e.key === "Escape") { e.preventDefault(); cancel(); }
    });
    input.addEventListener("blur", save);
  }

  function deleteConversation(conv) {
    if (!window.confirm("Supprimer définitivement cette discussion ?")) return;
    api("/chat/conversations/" + conv.id, { method: "DELETE" })
      .then(function () {
        if (state.currentConversationId === conv.id) {
          newConversation();
        } else {
          loadConversations();
        }
      })
      .catch(function (err) {
        alert(err.message || "Impossible de supprimer la discussion.");
      });
  }

  var welcomeTemplate = null;

  function bindSuggestions() {
    document.querySelectorAll(".suggestion-chip").forEach(function (chip) {
      chip.onclick = function () {
        var input = $("message-input");
        if (!input) return;
        input.value = chip.getAttribute("data-prompt");
        input.style.height = "auto";
        if (sendMessage(input.value)) {
          input.value = "";
        }
      };
    });
  }

  function hideWelcome() {
    var welcome = document.querySelector(".welcome-screen");
    if (welcome) welcome.remove();
  }

  function newConversation() {
    state.currentConversationId = null;
    showView("chat");
    renderConversations();
    $("chat-title").textContent = "Nouvelle discussion";
    var messages = $("messages");
    messages.innerHTML = "";
    if (welcomeTemplate) {
      messages.appendChild(welcomeTemplate.cloneNode(true));
      bindSuggestions();
    }
    $("message-input").focus();
  }

  function openConversation(id) {
    state.currentConversationId = id;
    showView("chat");
    renderConversations();
    var conv = state.conversations.find(function (c) { return c.id === id; });
    $("chat-title").textContent = conv ? (conv.title || "Conversation") : "Conversation";
    var messages = $("messages");
    messages.innerHTML = "";
    api("/chat/conversations/" + id + "/messages").then(function (msgs) {
      (msgs || []).forEach(function (m) {
        if (m.role === "user") renderUserMessage(m.content, m.created_at);
        else if (m.role === "assistant") renderAssistantMessage(m.content, m.created_at, false);
      });
      scrollBottom();
      loadPendingForConversation(id);
    }).catch(function () {});
  }

  // ------------------------------------------------------------ rendu messages
  function renderUserMessage(content, time) {
    hideWelcome();
    var msg = document.createElement("div");
    msg.className = "msg user";
    msg.innerHTML =
      '<div class="msg-avatar">' + initials(state.user ? state.user.full_name : "U") + "</div>" +
      '<div class="msg-body"><div class="msg-bubble">' + escapeText(content) + "</div>" +
      (time ? '<div class="msg-time">' + formatTime(time) + "</div>" : "") + "</div>";
    $("messages").appendChild(msg);
  }

  function renderAssistantMessage(content, time, withPending, meta) {
    meta = meta || {};
    var msg = document.createElement("div");
    msg.className = "msg assistant";
    var usageHtml = "";
    if (meta.usage && meta.usage.total_tokens) {
      usageHtml = '<div class="msg-usage">' + meta.usage.total_tokens.toLocaleString("fr-FR") +
        " tokens · " + escapeText(meta.usage.model || "") + "</div>";
    }
    var body = '<div class="msg-body">' +
      '<div class="msg-bubble markdown">' + renderMarkdown(content || "") + "</div>" +
      '<div class="msg-actions">' +
        '<button class="msg-action-btn copy-btn" title="Copier le texte">' + ICONS.copy + ' <span>Copier</span></button>' +
      '</div>' +
      usageHtml +
      (time ? '<div class="msg-time">' + formatTime(time) + "</div>" : "") +
      "</div>";
    msg.innerHTML = '<div class="msg-avatar">' + AGENT_AVATAR + "</div>" + body;

    var copyBtn = msg.querySelector(".copy-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", function () {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(content || "").then(function () {
            copyBtn.querySelector("span").textContent = "Copié !";
            setTimeout(function () {
              copyBtn.querySelector("span").textContent = "Copier";
            }, 2000);
          });
        }
      });
    }

    // Gestion des liens de documents Dolibarr avec authentification JWT
    msg.querySelectorAll("a.doc-link").forEach(function (link) {
      var href = link.getAttribute("href");
      if (href && href.startsWith("/api/")) {
        link.addEventListener("click", function (e) {
          e.preventDefault();
          var filename = link.textContent.trim().replace(/^.*[\\\/]/, '') || "document.pdf";
          if (!filename.toLowerCase().endsWith(".pdf")) filename += ".pdf";
          fetch(href, {
            headers: state.token ? { "Authorization": "Bearer " + state.token } : {},
          })
            .then(function (res) {
              if (!res.ok) throw new Error("Téléchargement impossible (" + res.status + ")");
              return res.blob();
            })
            .then(function (blob) {
              var url = URL.createObjectURL(blob);
              var a = document.createElement("a");
              a.href = url;
              a.download = filename;
              document.body.appendChild(a);
              a.click();
              a.remove();
              URL.revokeObjectURL(url);
            })
            .catch(function (err) {
              alert(err.message || "Erreur lors du téléchargement.");
            });
        });
      }
    });

    if (withPending && window._lastPending && window._lastPending.length) {
      window._lastPending.forEach(function (execution) {
        msg.querySelector(".msg-body").appendChild(buildConfirmCard(execution));
      });
      window._lastPending = [];
    }
    $("messages").appendChild(msg);
  }

  function renderTyping(statusText) {
    var msg = document.createElement("div");
    msg.className = "msg assistant typing";
    msg.innerHTML = '<div class="msg-avatar">' + AGENT_AVATAR + "</div>" +
      '<div class="msg-body"><div class="typing-status">' + escapeText(statusText || "Analyse en cours…") + "</div>" +
      '<div class="msg-bubble">' +
      '<span class="dot"></span><span class="dot"></span><span class="dot"></span>' +
      "</div></div>";
    $("messages").appendChild(msg);
    return msg;
  }

  function getStatusLabel(text) {
    var t = String(text || "").toLowerCase();
    if (/\b(chiffre|ca\b|affaires|trimestre)\b/.test(t)) return "Calcul du chiffre d'affaires…";
    if (/\b(impay|retard)\b/.test(t)) return "Consultation des factures impayées…";
    if (/\b(stock|rupture)\b/.test(t)) return "Analyse des niveaux de stock…";
    if (/\b(devis)\b/.test(t)) return "Recherche des devis…";
    if (/\b(créer|creer|nouveau|nouvelle)\b/.test(t)) return "Préparation d'une action…";
    if (/\b(client|tiers)\b/.test(t)) return "Recherche client…";
    if (/\b(produit|catalogue)\b/.test(t)) return "Consultation du catalogue…";
    return "Analyse de votre demande…";
  }

  function formatConfirmResult(data) {
    if (!data || !data.result) return "";
    var r = data.result.result || data.result;
    if (typeof r !== "object") return String(r);
    var lines = [];
    if (r.ref) lines.push("Référence : " + r.ref);
    if (r.name) lines.push("Nom : " + r.name);
    if (r.id) lines.push("ID Dolibarr : " + r.id);
    if (r.total_ht !== undefined) lines.push("Total HT : " + r.total_ht);
    if (r.total_ttc !== undefined) lines.push("Total TTC : " + r.total_ttc);
    return lines.length ? lines.join("\n") : "";
  }

  function escapeText(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function formatTime(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }

  function scrollBottom() {
    var el = $("messages");
    el.scrollTop = el.scrollHeight;
  }

  // ------------------------------------------------------------ confirmations
  function buildConfirmCard(execution) {
    var card = document.createElement("div");
    card.className = "confirm-card";
    card.setAttribute("data-id", execution.id);

    var label = TOOL_LABELS[execution.tool_name] || execution.tool_name;
    var params = execution.parameters || {};
    var summary = summarizeParams(execution.tool_name, params);

    card.innerHTML =
      '<div class="confirm-title"><span class="badge-pending">En attente</span> ' + escapeText(label) + "</div>" +
      '<div class="confirm-desc">Cette action sera exécutée dans Dolibarr après votre validation.</div>' +
      '<div class="confirm-detail">' + escapeText(summary) + "</div>" +
      '<div class="confirm-actions">' +
      '<button class="btn btn-small btn-primary confirm-yes">Confirmer</button>' +
      '<button class="btn btn-small confirm-no">Refuser</button>' +
      "</div>" +
      '<div class="confirm-result hidden"></div>';

    card.querySelector(".confirm-yes").addEventListener("click", function () {
      confirmAction(card, execution.id, true);
    });
    card.querySelector(".confirm-no").addEventListener("click", function () {
      confirmAction(card, execution.id, false);
    });
    return card;
  }

  function summarizeParams(toolName, params) {
    try {
      if (toolName === "create_client") {
        return "Nom : " + (params.name || "—") +
          (params.email ? "\nE-mail : " + params.email : "") +
          (params.phone ? "\nTéléphone : " + params.phone : "") +
          (params.city ? "\nVille : " + params.city : "");
      }
      if (toolName === "create_quote" || toolName === "create_invoice") {
        var lines = (params.lines || []).map(function (l, i) {
          return (i + 1) + ". " + (l.label || "") + " — " + (l.qty || 1) + " x " + (l.price || 0) +
            (l.vat ? " (TVA " + l.vat + "%)" : "");
        }).join("\n");
        return "Client ID : " + (params.client_id || "—") + "\nLignes :\n" + lines;
      }
      if (toolName === "log_event") {
        return "Libellé : " + (params.label || "—") +
          (params.note ? "\nNote : " + params.note : "");
      }
      return JSON.stringify(params, null, 2);
    } catch (e) {
      return JSON.stringify(params);
    }
  }

  function confirmAction(card, id, approve) {
    var buttons = card.querySelectorAll("button");
    buttons.forEach(function (b) { b.disabled = true; });
    var resultDiv = card.querySelector(".confirm-result");
    resultDiv.classList.remove("hidden");
    resultDiv.textContent = approve ? "Exécution en cours…" : "Refus en cours…";

    api("/confirmation/" + id + (approve ? "/confirm" : "/reject"), { method: "POST" })
      .then(function (data) {
        resultDiv.textContent = approve
          ? "Action exécutée." + (data && data.result ? " Référence : " + safeRef(data.result) : "")
          : "Action refusée.";
        resultDiv.classList.add("ok");
        card.querySelector(".badge-pending").textContent = approve ? "Confirmée" : "Refusée";
        var detail = card.querySelector(".confirm-detail");
        if (approve && data && data.result) {
          var formatted = formatConfirmResult(data);
          detail.textContent = formatted || summarizeParams(execution.tool_name, execution.parameters || {});
        }
        // Après une écriture confirmée, propose le téléchargement du PDF généré (§4.4)
        if (approve && data && data.result && data.result.document) {
          var doc = data.result.document;
          var dl = document.createElement("button");
          dl.className = "btn btn-primary pdf-download-btn";
          dl.style.marginTop = "6px";
          dl.innerHTML = ICONS.download + " <span>Télécharger le PDF (" + (doc.filename || "document.pdf") + ")</span>";
          dl.addEventListener("click", function (e) {
            e.preventDefault();
            downloadDocument(id, doc.filename || "document.pdf");
          });
          var actionsBox = card.querySelector(".confirm-actions");
          actionsBox.innerHTML = "";
          actionsBox.appendChild(dl);
        }
      })
      .catch(function (err) {
        resultDiv.textContent = err.message || "Erreur lors du traitement.";
        resultDiv.classList.add("err");
        buttons.forEach(function (b) { b.disabled = false; });
      });
  }

  function downloadDocument(id, filename) {
    // Téléchargement authentifié : fetch avec le token, puis blob -> lien de téléchargement
    fetch(API + "/confirmation/" + id + "/document", {
      headers: state.token ? { "Authorization": "Bearer " + state.token } : {},
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (d) {
            throw new Error(d.message || "Téléchargement impossible.");
          });
        }
        return res.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = filename || "document.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      })
      .catch(function (err) {
        alert(err.message || "Impossible de télécharger le PDF.");
      });
  }

  function safeRef(result) {
    if (result && result.id) return "#" + result.id;
    if (result && result.ref) return result.ref;
    return "";
  }

  function loadPendingForConversation(conversationId) {
    api("/chat/pending").then(function (pending) {
      (pending || []).forEach(function (execution) {
        if (execution.conversation_id === conversationId) {
          var container = $("messages");
          var wrapper = document.createElement("div");
          wrapper.className = "msg assistant";
          wrapper.innerHTML = '<div class="msg-avatar">' + AGENT_AVATAR + '</div><div class="msg-body"></div>';
          wrapper.querySelector(".msg-body").appendChild(buildConfirmCard(execution));
          container.appendChild(wrapper);
          scrollBottom();
        }
      });
    }).catch(function () {});
  }

  // ------------------------------------------------------------ envoi de message
  function sendMessage(text) {
    if (state.sending) return false;
    if (!text.trim()) return false;
    state.sending = true;

    try {
      renderUserMessage(text, new Date().toISOString());
      scrollBottom();
      var typing = renderTyping(getStatusLabel(text));
      scrollBottom();

      api("/chat/", {
        method: "POST",
        body: { message: text, conversation_id: state.currentConversationId },
      }).then(function (data) {
        typing.remove();
        state.currentConversationId = data.conversation_id;
        window._lastPending = data.pending || [];
        renderAssistantMessage(data.reply, new Date().toISOString(), true, {
          usage: data.usage,
          optimization: data.optimization,
        });
        scrollBottom();
        loadConversations();
      }).catch(function (err) {
        typing.remove();
        var msg = document.createElement("div");
        msg.className = "msg assistant";
        msg.innerHTML = '<div class="msg-avatar">' + AGENT_AVATAR + "</div>" +
          '<div class="msg-body"><div class="msg-bubble markdown"><p style="color:#C62828">' +
          escapeText(err.message || "Une erreur est survenue.") + "</p></div></div>";
        $("messages").appendChild(msg);
        scrollBottom();
      }).finally(function () {
        state.sending = false;
      });
      return true;
    } catch (e) {
      state.sending = false;
      return false;
    }
  }

  // ------------------------------------------------------------ tableau de bord
  function loadDashboard() {
    var cards = $("dash-cards");
    var errBox = $("dash-error");
    cards.innerHTML = '<div class="dash-card"><div class="dash-label">Chargement…</div></div>';
    errBox.classList.add("hidden");
    api("/chat/dashboard").then(function (d) {
      cards.innerHTML = "";
      var issues = [];
      var evo = dashEvolution(d.ca && d.ca.evolution_pct);
      cards.appendChild(dashCard("CA du mois", formatMoney(d.ca && d.ca.total_ttc),
        evo.text, !(d.ca && d.ca.total_ttc !== undefined), false, evo.cls));
      cards.appendChild(dashCard("Factures impayées", d.unpaid ? d.unpaid.count : "—",
        d.unpaid ? "Total : " + formatMoney(d.unpaid.total_ttc) : "Indisponible",
        !d.unpaid || d.unpaid.error, d.unpaid && d.unpaid.count > 0));
      cards.appendChild(dashCard("Devis en attente", d.quotes ? d.quotes.count : "—",
        d.quotes ? "Total : " + formatMoney(d.quotes.total_ttc) : "Indisponible",
        !d.quotes || d.quotes.error));
      var alertCard = dashCard("Alertes stock", d.stock ? d.stock.alert_count : "—",
        d.stock ? "Seuil : " + (d.stock.threshold !== undefined ? d.stock.threshold : "—") : "Indisponible",
        !d.stock || d.stock.error, d.stock && d.stock.alert_count > 0);
      cards.appendChild(alertCard);
      cards.appendChild(dashCard("Actions en attente", d.pending_confirmations !== undefined ? d.pending_confirmations : 0,
        "À confirmer dans l'interface", false, d.pending_confirmations > 0));

      ["ca", "unpaid", "quotes", "stock"].forEach(function (k) {
        if (d[k] && d[k].error) issues.push("Dolibarr : " + d[k].error);
      });
      if (issues.length) {
        errBox.textContent = issues.join(" — ");
        errBox.classList.remove("hidden");
      }
    }).catch(function (err) {
      cards.innerHTML = "";
      errBox.textContent = err.message || "Impossible de charger le tableau de bord.";
      errBox.classList.remove("hidden");
    });
  }

  function dashCard(label, value, sub, disabled, alert, subClass) {
    var card = document.createElement("div");
    card.className = "dash-card" + (alert ? " alert" : "");
    var subHtml = sub ? '<div class="dash-sub' + (subClass ? " " + subClass : "") + '">' +
      escapeText(sub) + "</div>" : "";
    card.innerHTML =
      '<div class="dash-label">' + escapeText(label) + "</div>" +
      '<div class="dash-value">' + escapeText(String(value === undefined || value === null ? "—" : value)) + "</div>" +
      subHtml;
    if (disabled) card.style.opacity = "0.55";
    return card;
  }

  function formatMoney(v) {
    if (v === undefined || v === null) return "—";
    return Number(v).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
  }
  function dashEvolution(pct) {
    if (pct === undefined || pct === null) return { text: "vs mois précédent", cls: "" };
    var sign = pct >= 0 ? "+" : "";
    return { text: sign + pct + " % vs mois précédent", cls: pct >= 0 ? "up" : "down" };
  }

  // ------------------------------------------------------------ paramètres
  function loadSettings() {
    var fields = $("settings-fields");
    var status = $("settings-status");
    status.textContent = "";
    status.className = "settings-status";
    fields.innerHTML = '<div class="dash-card"><div class="dash-label">Chargement…</div></div>';
    api("/admin/agent_config/settings").then(function (settings) {
      fields.innerHTML = "";
      if (!settings || !settings.length) {
        fields.innerHTML = '<div class="dash-card"><div class="dash-label">Aucun paramètre disponible.</div></div>';
        return;
      }
      settings.forEach(function (s) {
        fields.appendChild(settingsField(s));
      });
    }).catch(function (err) {
      fields.innerHTML = "";
      status.textContent = "Paramètres visibles par les administrateurs uniquement. (" + (err.message || "accès refusé") + ")";
      status.className = "settings-status err";
    });
  }

  function settingsField(s) {
    var wrap = document.createElement("div");
    var key = s.key || "";
    var isBool = typeof s.value === "boolean";
    var isNumber = typeof s.value === "number";
    var isList = Array.isArray(s.value);

    if (isBool) {
      wrap.className = "settings-field checkbox-field";
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.id = "sf-" + key;
      cb.checked = !!s.value;
      wrap.innerHTML =
        '<div><div class="sf-label"><label for="sf-' + key + '">' + escapeText(humanize(key)) + "</label></div>" +
        (s.description ? '<div class="sf-desc">' + escapeText(s.description) + "</div>" : "") + "</div>";
      wrap.querySelector(".sf-label label").before(cb);
      return wrap;
    }

    wrap.className = "settings-field";
    wrap.innerHTML =
      '<div class="sf-label">' + escapeText(humanize(key)) + "</div>" +
      (s.description ? '<div class="sf-desc">' + escapeText(s.description) + "</div>" : "");

    var control;
    if (key === "model_tier_default") {
      control = document.createElement("select");
      ["light", "balanced", "advanced"].forEach(function (opt) {
        var o = document.createElement("option");
        o.value = opt;
        o.textContent = opt;
        if (String(s.value) === opt) o.selected = true;
        control.appendChild(o);
      });
    } else {
      control = document.createElement("input");
      control.type = isNumber ? "number" : "text";
      control.value = isList ? (s.value || []).join(", ") : String(s.value === undefined || s.value === null ? "" : s.value);
      control.dataset.list = isList ? "1" : "";
    }
    control.dataset.key = key;
    control.id = "sf-" + key;
    wrap.appendChild(control);
    return wrap;
  }

  function humanize(key) {
    return String(key || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function saveSettings(e) {
    e.preventDefault();
    var status = $("settings-status");
    var payload = {};
    var fields = $("settings-fields");
    fields.querySelectorAll("[data-key]").forEach(function (control) {
      var key = control.dataset.key;
      if (control.type === "checkbox") {
        payload[key] = control.checked;
      } else if (control.dataset.list === "1") {
        payload[key] = control.value.split(",").map(function (s) {
          return parseInt(s.trim(), 10);
        }).filter(function (n) { return !isNaN(n); });
      } else if (control.type === "number") {
        payload[key] = control.value === "" ? "" : Number(control.value);
      } else {
        payload[key] = control.value;
      }
    });
    status.textContent = "Enregistrement…";
    status.className = "settings-status";
    api("/admin/agent_config/settings", { method: "PUT", body: { settings: payload } })
      .then(function () {
        status.textContent = "Paramètres enregistrés.";
        status.className = "settings-status ok";
        loadSettings();
      })
      .catch(function (err) {
        status.textContent = err.message || "Erreur lors de l'enregistrement.";
        status.className = "settings-status err";
      });
  }

  // ------------------------------------------------------------ icônes SVG
  var ICONS = {
    pencil: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/></svg>',
    trash: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    copy: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    download: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
  };

  // ------------------------------------------------------------ initialisation
  function init() {
    initTheme();

    $("theme-toggle").addEventListener("click", toggleTheme);

    var mobileBtn = $("mobile-menu-btn");
    if (mobileBtn) mobileBtn.addEventListener("click", function () { toggleMobileSidebar(); });
    var overlay = $("sidebar-overlay");
    if (overlay) overlay.addEventListener("click", closeMobileSidebar);

    // Connexion
    $("login-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = $("login-btn");
      var err = $("login-error");
      err.classList.add("hidden");
      btn.disabled = true;
      btn.textContent = "Connexion…";
      api("/auth/login", {
        method: "POST",
        body: {
          email: $("login-email").value.trim(),
          password: $("login-password").value,
        },
      }).then(function (data) {
        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem("ict_agent_token", state.token);
        localStorage.setItem("ict_agent_user", JSON.stringify(state.user));
        showChat();
      }).catch(function (error) {
        err.textContent = error.message;
        err.classList.remove("hidden");
      }).finally(function () {
        btn.disabled = false;
        btn.textContent = "Se connecter";
      });
    });

    $("logout-btn").addEventListener("click", logout);

    // Menu sidebar
    $("brand-home").addEventListener("click", function () { showView("chat"); });
    $("menu-dashboard").addEventListener("click", function () { showView("dashboard"); });
    $("menu-settings").addEventListener("click", function () { showView("settings"); });
    $("dash-refresh").addEventListener("click", loadDashboard);

    // Paramètres
    $("settings-form").addEventListener("submit", saveSettings);

    // Saisie
    var input = $("message-input");
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (sendMessage(input.value)) {
          input.value = "";
          input.style.height = "auto";
        }
      }
    });
    input.addEventListener("input", function () {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 180) + "px";
    });
    $("send-btn").addEventListener("click", function () {
      if (sendMessage(input.value)) {
        input.value = "";
        input.style.height = "auto";
      }
    });

    // Suggestions
    var welcomeEl = document.querySelector(".welcome-screen");
    if (welcomeEl) welcomeTemplate = welcomeEl.cloneNode(true);
    bindSuggestions();

    $("new-chat-btn").addEventListener("click", newConversation);

    if (state.token && state.user) {
      showChat();
    } else {
      showLogin();
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
