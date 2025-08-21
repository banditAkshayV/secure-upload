(function () {
  // Form validation elements
  const form = document.getElementById('entry-form');
  const comment = document.getElementById('comment-input');
  const file = document.getElementById('file-input');
  const maxSize = Number(form.dataset.maxBytes) || 5 * 1024 * 1024;
  const allowedExts = JSON.parse(form.dataset.allowedExts || "[]");
  const allowedMimes = JSON.parse(form.dataset.allowedMimes || "[]");

  // Search elements
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search');
  const searchStats = document.getElementById('search-stats');
  const searchResultsText = document.getElementById('search-results-text');
  const resultsBadge = document.getElementById('results-badge');
  const entriesTable = document.querySelector('.table-responsive');
  const noResultsDiv = document.getElementById('no-results');

  // Store all entries for client-side search
  const allEntries = Array.from(document.querySelectorAll('.entry-row'));
  const totalEntries = allEntries.length;

  // Optimized injection detection patterns
  const injectionPatterns = [
    { pattern: /\b(union|select|drop|delete)\b/i, type: 'SQL' },
    { pattern: /<script|javascript:|alert\s*\(/i, type: 'XSS' },
    { pattern: /;\s*(cat|ls|whoami)/i, type: 'Command' },
    { pattern: /\$where|\$ne/i, type: 'NoSQL' }
  ];

  let injectionWarningTimeout;

  function sarcastic(msg) {
    const alertDiv = document.createElement('div');
    alertDiv.className =
      'alert alert-danger alert-dismissible fade show position-fixed';
    alertDiv.style.cssText =
      'top:20px; left:50%; transform:translateX(-50%); z-index:9999; max-width:500px;';
    alertDiv.innerHTML = `
      <i class="bi bi-exclamation-triangle-fill scary-icon"></i>
      <strong>Digital Judgment:</strong> ${msg}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    setTimeout(() => {
      if (alertDiv.parentNode) {
        alertDiv.remove();
      }
    }, 5000);
  }

  function getExtension(name) {
    const idx = name.lastIndexOf('.');
    return idx >= 0 ? name.slice(idx).toLowerCase() : '';
  }

  // Client-side search
  function performSearch(searchTerm) {
    searchTerm = searchTerm.toLowerCase().trim();

    if (!searchTerm) {
      allEntries.forEach((row) => (row.style.display = ''));
      updateSearchStats(totalEntries, '');
      return;
    }

    let matchCount = 0;

    allEntries.forEach((row) => {
      const confessionText = row
        .getAttribute('data-confession')
        .toLowerCase();

      if (confessionText.includes(searchTerm)) {
        row.style.display = '';
        matchCount++;
      } else {
        row.style.display = 'none';
      }
    });

    updateSearchStats(matchCount, searchTerm);
  }

  function updateSearchStats(matchCount, searchTerm) {
    if (searchTerm) {
      searchStats.style.display = 'block';
      const plural = matchCount !== 1 ? 's' : '';
      searchResultsText.textContent = `Found ${matchCount} confession${plural} matching "${searchTerm}"`;
      resultsBadge.textContent = `${matchCount} Found`;
      resultsBadge.className = 'badge bg-danger ms-2';

      if (matchCount === 0) {
        if (entriesTable) entriesTable.style.display = 'none';
        noResultsDiv.style.display = 'block';
      } else {
        if (entriesTable) entriesTable.style.display = 'block';
        noResultsDiv.style.display = 'none';
      }
    } else {
      searchStats.style.display = 'none';
      resultsBadge.textContent = `${totalEntries} Total Victims`;
      resultsBadge.className = 'badge bg-secondary ms-2';

      if (entriesTable) entriesTable.style.display = 'block';
      noResultsDiv.style.display = 'none';
    }
  }

  // Search event listeners
  if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', function () {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        performSearch(this.value);
      }, 300);
    });

    searchInput.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        performSearch(this.value);
      }
    });
  }

  if (clearSearchBtn) {
    clearSearchBtn.addEventListener('click', function () {
      searchInput.value = '';
      performSearch('');
    });
  }

  // Injection detection
  function detectInjectionAttempt(text) {
    if (!text) return null;

    for (let pattern of injectionPatterns) {
      if (pattern.pattern.test(text)) return pattern.type;
    }

    if ((text.match(/['"`;<>{}[\]()]/g) || []).length > 5) {
      return 'Generic';
    }

    return null;
  }

  function showInjectionWarning(type) {
    const messages = {
      SQL: '🤖 SQL injection detected! Your hack attempt will be preserved as plain text.',
      XSS: '🚨 XSS attempt spotted! Your script dreams will become text nightmares.',
      Command:
        '💻 Command injection detected! Your terminal skills are about to be terminated.',
      NoSQL: '🍃 NoSQL injection found! Your MongoDB mischief is now just plain text.',
      Generic:
        '🎯 Suspicious patterns detected! Your injection cocktail is brewing...'
    };

    const warningDiv = document.createElement('div');
    warningDiv.className =
      'alert alert-warning alert-dismissible fade show position-fixed';
    warningDiv.style.cssText =
      'top:80px; right:20px; z-index:9999; max-width:400px; animation:slideInRight 0.3s ease;';
    warningDiv.innerHTML = `
      <i class="bi bi-shield-exclamation"></i>
      <strong>Live Detection:</strong> ${messages[type] || messages['Generic']}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(warningDiv);

    setTimeout(() => {
      if (warningDiv.parentNode) {
        warningDiv.remove();
      }
    }, 3000);
  }

  if (comment) {
    comment.addEventListener('input', function () {
      const text = this.value;

      if (injectionWarningTimeout) {
        clearTimeout(injectionWarningTimeout);
      }

      injectionWarningTimeout = setTimeout(() => {
        const injectionType = detectInjectionAttempt(text);
        if (injectionType && text.length > 15) {
          showInjectionWarning(injectionType);
        }
      }, 2000);
    });
  }

  // Form submit validation
  form.addEventListener('submit', function (evt) {
    const hasComment = comment.value.trim().length > 0;
    const hasFile = file.files && file.files.length > 0;

    if (!hasComment && !hasFile) {
      evt.preventDefault();
      sarcastic(
        "The void speaks louder than your empty submission. Confess something or provide evidence of your digital sins."
      );
      return;
    }

    if (hasFile) {
      const f = file.files[0];
      const ext = getExtension(f.name);
      const type = (f.type || '').toLowerCase();

      if (!allowedExts.includes(ext)) {
        evt.preventDefault();
        sarcastic(
          'Your cursed file extension is forbidden in this digital realm. Only PNG, JPG, JPEG souls are accepted.'
        );
        return;
      }

      if (!allowedMimes.includes(type)) {
        evt.preventDefault();
        sarcastic(
          `The digital spirits reject your "${type}" offering. We feast only on image souls.`
        );
        return;
      }

      if (
        (ext === '.png' && type !== 'image/png') ||
        ((ext === '.jpg' || ext === '.jpeg') && type !== 'image/jpeg')
      ) {
        evt.preventDefault();
        sarcastic(
          'Deception detected! Your file wears a false identity. The digital overlords see through your disguise.'
        );
        return;
      }

      if (f.size > maxSize) {
        evt.preventDefault();
        sarcastic(
          `Your digital offering is too bloated for our altar. Compress your sins to under ${Math.round(
            maxSize / 1024 / 1024
          )}MB.`
        );
        return;
      }
    }
  });
})();
