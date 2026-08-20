/* Moteur de rendu Markdown optimisé — documents administratifs & tableaux Dolibarr */
(function (global) {
  "use strict";

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function inline(text) {
    var out = escapeHtml(text);
    // Code inline
    out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Liens [texte](url) — supporte URLs absolues, relatives et références avec parenthèses comme (PROV16)
    out = out.replace(/\[([^\]]+)\]\(((?:https?:\/\/|\/|api\/)(?:[^\s()]|\([^\s()]*\))+)\)/g,
      '<a href="$2" class="doc-link" rel="noopener noreferrer">$1</a>');
    // Gras **texte**
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    // Italique *texte* ou _texte_
    out = out.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    out = out.replace(/(^|[^_])_([^_]+)_/g, "$1<em>$2</em>");
    return out;
  }

  function renderCodeBlock(lines) {
    return "<div class=\"code-block-wrapper\"><pre><code>" + escapeHtml(lines.join("\n")) + "</code></pre></div>";
  }

  function parseTableAlignments(separatorLine) {
    var cells = separatorLine.trim().replace(/^\|/, "").replace(/\|$/, "").split("|");
    return cells.map(function (c) {
      var trimmed = c.trim();
      var leftColon = trimmed.charAt(0) === ":";
      var rightColon = trimmed.charAt(trimmed.length - 1) === ":";
      if (leftColon && rightColon) return "center";
      if (rightColon) return "right";
      if (leftColon) return "left";
      return "left";
    });
  }

  function renderTable(lines) {
    var alignSeparatorRegex = /^\s*\|?[\s:|-]+\|?\s*$/;
    var rawRows = [];
    var alignments = [];

    lines.forEach(function (line, index) {
      var trimmed = line.trim();
      if (!trimmed) return;
      // Ligne de séparation (---|---|---)
      if (alignSeparatorRegex.test(trimmed) && trimmed.indexOf("-") !== -1) {
        // Si on a déjà au moins 1 ligne de données, c'est le séparateur
        if (rawRows.length >= 1) {
          alignments = parseTableAlignments(trimmed);
          return;
        }
        // Sinon c'est peut-être la 2e ligne du bloc, on skip si ça ressemble à un séparateur
        if (index <= 1 && /^\s*\|?\s*:?-+:?\s*\|/.test(trimmed)) {
          return;
        }
      }
      var clean = trimmed.replace(/^\|/, "").replace(/\|$/, "");
      var cells = clean.split("|").map(function (c) { return c.trim(); });
      rawRows.push(cells);
    });

    if (rawRows.length === 0) return "";

    // Déterminer le nombre maximum de colonnes
    var maxCols = 0;
    rawRows.forEach(function (r) { if (r.length > maxCols) maxCols = r.length; });

    var headerRow = rawRows[0];
    var bodyRows = rawRows.slice(1);

    var html = '<div class="table-wrapper"><table class="admin-table">';

    // Header
    html += '<thead><tr>';
    for (var colIdx = 0; colIdx < maxCols; colIdx++) {
      var colText = headerRow[colIdx] !== undefined ? headerRow[colIdx] : "";
      var align = alignments[colIdx] || "left";
      html += '<th style="text-align:' + align + '">' + inline(colText) + '</th>';
    }
    html += '</tr></thead>';

    // Body
    if (bodyRows.length > 0) {
      html += '<tbody>';
      bodyRows.forEach(function (row) {
        html += '<tr>';
        for (var cIdx = 0; cIdx < maxCols; cIdx++) {
          var cellText = row[cIdx] !== undefined ? row[cIdx] : "";
          var cellAlign = alignments[cIdx] || "left";
          // Détection automatique de colonnes numériques ou monétaires si alignement non spécifié
          if (!alignments[cIdx] && (/^[\d\s.,]+(FCFA|€|\$|%|XOF)?$/i.test(cellText) || /^(Total|Sous-total|TVA|Montant|Prix)/i.test(headerRow[cIdx] || ""))) {
            cellAlign = "right";
          }
          html += '<td style="text-align:' + cellAlign + '">' + inline(cellText) + '</td>';
        }
        html += '</tr>';
      });
      html += '</tbody>';
    }

    html += '</table></div>';
    return html;
  }

  function renderList(lines, ordered) {
    var html = ordered ? "<ol class=\"admin-list\">" : "<ul class=\"admin-list\">";
    var open = false;
    lines.forEach(function (line) {
      var match = ordered
        ? line.match(/^\s*\d+[.)]\s+(.*)$/)
        : line.match(/^\s*[-*+]\s+(.*)$/);
      if (match) {
        if (open) { html += "</li>"; }
        html += "<li>" + inline(match[1]);
        open = true;
      } else {
        if (open) { html += "</li>"; open = false; }
        html += "<p>" + inline(line.trim()) + "</p>";
      }
    });
    if (open) { html += "</li>"; }
    return html + (ordered ? "</ol>" : "</ul>");
  }

  global.renderMarkdown = function (text) {
    if (!text) return "";
    var blocks = String(text).replace(/\r\n/g, "\n").split(/\n{2,}/);
    var html = "";

    blocks.forEach(function (block) {
      var lines = block.split("\n");
      var trimmed = block.trim();

      if (!trimmed) return;

      // Bloc de code
      var fence = lines[0].match(/^```(\w*)\s*$/);
      if (fence && lines[lines.length - 1].trim() === "```") {
        html += renderCodeBlock(lines.slice(1, -1));
        return;
      }

      // Tableau Markdown (détection avec | dans les lignes)
      var pipeCount = lines.filter(function (l) { return l.indexOf("|") !== -1; }).length;
      var hasSeparator = lines.some(function (l) { return /^\s*\|?\s*:?-+:?\s*\|/.test(l); });
      var isTable = lines.length >= 2 && pipeCount >= 2 && (lines[0].indexOf("|") !== -1 || hasSeparator);
      if (isTable) {
        html += renderTable(lines);
        return;
      }

      // Titres
      var heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
      if (heading) {
        var level = heading[1].length;
        html += "<h" + level + " class=\"admin-heading admin-h" + level + "\">" + inline(heading[2]) + "</h" + level + ">";
        return;
      }

      // Séparateur horizontal
      if (/^\s*([-*_])\s*\1\s*\1\s*$/.test(trimmed)) {
        html += "<hr class=\"admin-divider\">";
        return;
      }

      // Citation / Bloc administratif
      if (lines.every(function (l) { return /^\s*&gt;|^\s*>/.test(l); })) {
        html += "<blockquote class=\"admin-blockquote\">" + lines.map(function (l) {
          return "<p>" + inline(l.replace(/^\s*&gt;\s?/, "").replace(/^\s*>\s?/, "")) + "</p>";
        }).join("") + "</blockquote>";
        return;
      }

      // Listes
      var first = lines[0].trim();
      if (/^\s*[-*+]\s+/.test(first)) {
        html += renderList(lines, false);
        return;
      }
      if (/^\s*\d+[.)]\s+/.test(first)) {
        html += renderList(lines, true);
        return;
      }

      // Paragraphe classique
      html += "<p class=\"admin-paragraph\">" + inline(trimmed) + "</p>";
    });

    return html;
  };
})(window);
