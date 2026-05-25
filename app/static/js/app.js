// app/static/js/app.js

const state = {
  docId:         null,
  docName:       null,
  questionCount: 0,
  isLoading:     false
};

document.addEventListener('DOMContentLoaded', () => {
  setupDropZone();
  document.getElementById('fileInput')
    .addEventListener('change', e => handleFile(e.target.files[0]));
});

function setupDropZone() {
  const zone = document.getElementById('dropZone');
  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('over');
    handleFile(e.dataTransfer.files[0]);
  });
}

async function handleFile(file) {
  if (!file || !file.name.endsWith('.pdf')) {
    showToast('Solo se aceptan PDFs', 'error'); return;
  }
  setStatus('processing', 'Procesando...');
  showLoading('Procesando documento...');
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res  = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    state.docId  = data.doc_id;
    state.docName = file.name;
    document.getElementById('docInfo').classList.remove('hidden');
    document.getElementById('docName').textContent = file.name;
    if (data.cached) {
      document.getElementById('docMeta').textContent = 'Cargado desde caché';
    } else {
      const s = data.stats;
      document.getElementById('docMeta').textContent =
        `${s.total_pages} págs · ~${s.estimated_words.toLocaleString()} palabras`;
      document.getElementById('statsCard').style.display = 'block';
      document.getElementById('statPages').textContent = s.total_pages;
      document.getElementById('statWords').textContent = s.estimated_words.toLocaleString();
    }
    const input = document.getElementById('questionInput');
    input.disabled = false;
    input.placeholder = 'Escribe tu pregunta sobre el documento...';
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('chatWelcome').style.display = 'none';
    setStatus('ready', 'Listo');
    showToast(data.cached ? 'Documento en caché' : 'Documento procesado', 'success');
  } catch (err) {
    setStatus('idle', 'Error');
    showToast(err.message, 'error');
  } finally {
    hideLoading();
  }
}

async function sendQuestion() {
  const input    = document.getElementById('questionInput');
  const question = input.value.trim();
  if (!question || !state.docId || state.isLoading) return;

  state.isLoading = true;
  input.disabled  = true;
  document.getElementById('sendBtn').disabled = true;

  appendMessage('user', question);
  input.value = '';
  autoResize(input);

  const typingId = appendTyping();

  try {
    const res  = await fetch('/api/ask', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ question, doc_id: state.docId })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const result = await pollResult(data.job_id);
    removeTyping(typingId);
    appendBotMessage(result.answer, result.sources || [], result.model);

    state.questionCount++;
    document.getElementById('statQuestions').textContent = state.questionCount;

  } catch (err) {
    removeTyping(typingId);
    appendBotMessage('❌ ' + err.message, []);
    showToast(err.message, 'error');
  } finally {
    state.isLoading = false;
    input.disabled  = false;
    document.getElementById('sendBtn').disabled = false;
    setStatus('ready', 'Listo');
  }
}

async function pollResult(jobId) {
  const MAX_WAIT = 10 * 60 * 1000;  // 10 minutos
  const INTERVAL = 2500;
  const start    = Date.now();

  while (Date.now() - start < MAX_WAIT) {
    await sleep(INTERVAL);

    const res  = await fetch(`/api/result/${jobId}`);
    const data = await res.json();

    // Mostrar info de cola al usuario
    if (data.status === 'pending') {
      const pos = data.queue_pos || '?';
      setStatus('thinking', `En cola — posición ${pos}`);
    } else if (data.status === 'processing') {
      const secs = data.elapsed || 0;
      setStatus('thinking', `Generando respuesta... ${secs}s`);
    }

    if (data.status === 'done') {
      if (!data.result) throw new Error('Respuesta vacía');
      return data.result;
    }

    if (data.status === 'error') {
      throw new Error(data.error || 'Error procesando la pregunta');
    }
  }

  throw new Error('Tiempo agotado. Intenta con una pregunta más corta.');
}

// Actualiza appendBotMessage para mostrar qué modelo respondió
function appendBotMessage(answer, sources, model) {
  const container = document.getElementById('chatMessages');
  const div       = document.createElement('div');
  div.className   = 'msg bot';

  const formatted = escapeHtml(answer)
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g,   '<br>');

  const modelBadge = model
    ? `<span class="model-badge">${model === 'groq' ? '⚡ Groq' : '🖥 Phi3'}</span>`
    : '';

  let sourcesHtml = '';
  if (sources.length > 0) {
    const items = sources.map((s, i) =>
      `<div class="source-item">
        <span class="source-relevance">Relevancia ${s.relevance}%</span><br>
        ${escapeHtml(s.text)}
       </div>`
    ).join('');
    sourcesHtml = `
      <div class="sources-toggle" onclick="toggleSources(this)">
        📎 ${sources.length} fragmento(s) utilizados ▾
      </div>
      <div class="sources-list" style="display:none">${items}</div>`;
  }

  div.innerHTML = `
    <div class="msg-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           style="width:17px;height:17px">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5Z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
    </div>
    <div>
      <div class="msg-bubble">
        ${modelBadge}
        <p>${formatted}</p>
      </div>
      ${sourcesHtml}
    </div>`;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Construir mensajes ────────────────────────────────────────
function appendMessage(role, text) {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  const avatar = role === 'user'
    ? `<div class="msg-avatar">Tú</div>`
    : `<div class="msg-avatar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:17px;height:17px"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg></div>`;
  div.innerHTML = `${avatar}<div class="msg-bubble">${escapeHtml(text)}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendBotMessage(answer, sources) {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'msg bot';
  const formatted = escapeHtml(answer)
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
  let sourcesHtml = '';
  if (sources.length > 0) {
    const items = sources.map((s, i) =>
      `<div class="source-item">
        <span class="source-relevance">Relevancia ${s.relevance}%</span><br>
        ${escapeHtml(s.text)}
       </div>`
    ).join('');
    sourcesHtml = `
      <div class="sources-toggle" onclick="toggleSources(this)">
        📎 Ver ${sources.length} fragmento(s) ▾
      </div>
      <div class="sources-list" style="display:none">${items}</div>`;
  }
  div.innerHTML = `
    <div class="msg-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:17px;height:17px">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
    </div>
    <div>
      <div class="msg-bubble"><p>${formatted}</p></div>
      ${sourcesHtml}
    </div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function toggleSources(el) {
  const list = el.nextElementSibling;
  const open = list.style.display !== 'none';
  list.style.display = open ? 'none' : 'flex';
  el.textContent = el.textContent.replace(open ? '▴':'▾', open ? '▾':'▴');
}

let typingCounter = 0;
function appendTyping() {
  const id        = 'typing-' + (++typingCounter);
  const container = document.getElementById('chatMessages');
  const div       = document.createElement('div');
  div.className   = 'msg bot typing-indicator';
  div.id          = id;
  div.innerHTML   = `
    <div class="msg-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:17px;height:17px">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
      </svg>
    </div>
    <div class="msg-bubble" style="display:flex;gap:5px;align-items:center">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}
function removeTyping(id) { document.getElementById(id)?.remove(); }

function useQuestion(btn) {
  if (!state.docId) { showToast('Primero sube un documento', 'info'); return; }
  const input = document.getElementById('questionInput');
  input.value = btn.textContent.trim();
  autoResize(input);
  input.focus();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion(); }
}
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}
function setStatus(type, label) {
  const badge = document.getElementById('statusBadge');
  badge.querySelector('.status-dot').className = `status-dot ${type}`;
  badge.lastChild.textContent = ' ' + label;
}
function showLoading(text) {
  document.getElementById('loadingText').textContent = text;
  document.getElementById('loadingOverlay').classList.remove('hidden');
}
function hideLoading() {
  document.getElementById('loadingOverlay').classList.add('hidden');
}
function showToast(msg, type = 'info') {
  const host  = document.getElementById('toastHost');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${{success:'✓',error:'✕',info:'ℹ'}[type]}</span> ${escapeHtml(msg)}`;
  host.prepend(toast);
  requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add('in')));
  setTimeout(() => { toast.classList.remove('in'); setTimeout(() => toast.remove(), 400); }, 4000);
}
function escapeHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}