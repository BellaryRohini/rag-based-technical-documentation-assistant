const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = { lastQuestion: '', lastAnswer: '', view: 'ask', toastTimer: null };

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const type = response.headers.get('content-type') || '';
  const payload = type.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = payload && typeof payload === 'object' ? (payload.detail || payload.message) : payload;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail || `Request failed (${response.status})`));
  }
  return payload;
}

function toast(message) {
  const element = $('#toast');
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => element.classList.remove('show'), 3400);
}

function showMessage(selector, message, isError = false) {
  const element = $(selector);
  element.textContent = message;
  element.classList.remove('hidden', 'error');
  if (isError) element.classList.add('error');
}
function clearMessage(selector) { $(selector).classList.add('hidden'); }
function setBusy(button, busy, busyText = 'Working…') {
  if (!button.dataset.originalText) button.dataset.originalText = button.innerHTML;
  button.disabled = busy;
  button.innerHTML = busy ? `<span class="mini-spinner"></span>${busyText}` : button.dataset.originalText;
}
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function extension(name) { const match = String(name).split('.').pop(); return match && match.length <= 4 ? match.toUpperCase() : 'DOC'; }

function navigate(view) {
  state.view = view;
  $$('.view').forEach(section => section.classList.toggle('active', section.id === `view-${view}`));
  $$('.nav-item').forEach(button => button.classList.toggle('active', button.dataset.view === view));
  const names = { ask: 'Ask', library: 'Library', add: 'Add documents' };
  $('#breadcrumb-current').textContent = names[view] || 'Ask';
  if (view === 'library') loadDocuments();
  if (view === 'ask') $('#question-input').focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function checkHealth() {
  const dot = $('#connection-dot');
  const label = $('#connection-label');
  try {
    await api('/health');
    dot.style.background = '#92a98e';
    label.textContent = 'API connected';
  } catch {
    dot.style.background = '#c37b60';
    label.textContent = 'API unavailable';
  }
}

async function loadDocuments() {
  const list = $('#document-list');
  list.innerHTML = '<div class="loading-row">Loading your library…</div>';
  try {
    const data = await api('/documents');
    const docs = data.documents || [];
    $('#sidebar-doc-count').textContent = docs.length;
    $('#library-count').textContent = docs.length;
    if (!docs.length) {
      list.innerHTML = '<div class="empty-state"><strong>Your library is empty for now.</strong>Add a Markdown, text or HTML file, or a public documentation page. Then build the library to make it searchable.</div>';
      return;
    }
    list.innerHTML = docs.map(doc => `<div class="document-row"><div class="document-file-icon">${escapeHtml(extension(doc.name))}</div><div class="document-info"><strong>${escapeHtml(doc.name)}</strong><small>${escapeHtml(doc.path || doc.name)}</small></div><span class="document-size">${formatSize(doc.bytes || 0)}</span></div>`).join('');
  } catch (error) {
    list.innerHTML = `<div class="empty-state"><strong>Couldn't load the library.</strong>${escapeHtml(error.message)}</div>`;
  }
}

function renderAnswer(result) {
  const panel = $('#answer-panel');
  state.lastQuestion = result.question || $('#question-input').value.trim();
  state.lastAnswer = result.answer || '';
  $('#asked-question').textContent = state.lastQuestion;
  $('#answer-body').textContent = state.lastAnswer;
  const answered = result.status === 'answered';
  const status = $('#answer-status');
  status.textContent = answered ? 'Response ready' : 'Not enough context';
  status.classList.toggle('warning', !answered);
  const sources = result.sources || [];
  $('#source-count').textContent = `${sources.length} ${sources.length === 1 ? 'source' : 'sources'}`;
  $('#source-list').innerHTML = sources.length ? sources.map((source, index) => `<article class="source-card"><div class="source-card-top"><span class="source-index">${String(index + 1).padStart(2, '0')}</span><span class="source-name">${escapeHtml(source.source || 'Document')}</span></div><p class="source-preview">${escapeHtml(source.preview || 'No preview available.')}</p></article>`).join('') : '<div class="empty-state">No supporting passages were returned. Try adding more documentation or asking a narrower question.</div>';
  $('#feedback-message').textContent = '';
  $$('.feedback-button').forEach(button => button.classList.remove('selected'));
  panel.classList.remove('hidden');
  clearMessage('#ask-message');
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

$('#question-form').addEventListener('submit', async event => {
  event.preventDefault();
  const question = $('#question-input').value.trim();
  if (question.length < 3) { showMessage('#ask-message', 'Please enter a question with at least three characters.', true); return; }
  const button = $('#ask-button');
  setBusy(button, true, 'Searching your library…');
  clearMessage('#ask-message');
  $('#answer-panel').classList.add('hidden');
  try {
    const result = await api('/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) });
    renderAnswer(result);
  } catch (error) {
    showMessage('#ask-message', `I couldn't answer that yet. ${error.message}\n\nIf this is your first run, open Add documents, select “Rebuild library”, and wait for it to finish. Check that your Google API key is set in .env if the error mentions Gemini or GOOGLE_API_KEY.`, true);
  } finally { setBusy(button, false); }
});

$$('.suggestion-card').forEach(button => button.addEventListener('click', () => {
  $('#question-input').value = button.dataset.question;
  navigate('ask');
  $('#question-form').requestSubmit();
}));
$('#clear-answer').addEventListener('click', () => { $('#answer-panel').classList.add('hidden'); $('#question-input').focus(); });

$$('.nav-item').forEach(button => button.addEventListener('click', () => navigate(button.dataset.view)));
$$('[data-go]').forEach(button => button.addEventListener('click', () => navigate(button.dataset.go)));
$('#refresh-documents').addEventListener('click', loadDocuments);

const fileInput = $('#file-input');
const selectedFiles = $('#selected-files');
function updateSelectedFiles(files) {
  const list = [...files];
  if (!list.length) { selectedFiles.classList.add('hidden'); selectedFiles.textContent = ''; return; }
  selectedFiles.classList.remove('hidden');
  selectedFiles.textContent = list.map(file => `${file.name} · ${formatSize(file.size)}`).join('\n');
}
fileInput.addEventListener('change', () => updateSelectedFiles(fileInput.files));
const dropZone = $('#drop-zone');
dropZone.addEventListener('dragover', event => { event.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', event => {
  event.preventDefault(); dropZone.classList.remove('dragover');
  if (event.dataTransfer?.files?.length) {
    const transfer = new DataTransfer();
    [...event.dataTransfer.files].forEach(file => transfer.items.add(file));
    fileInput.files = transfer.files; updateSelectedFiles(fileInput.files);
  }
});

$('#upload-form').addEventListener('submit', async event => {
  event.preventDefault(); clearMessage('#ingest-message');
  const files = [...fileInput.files];
  if (!files.length) { showMessage('#ingest-message', 'Choose at least one .md, .txt or .html file first.', true); return; }
  const unsupported = files.find(file => !/\.(md|txt|html)$/i.test(file.name));
  if (unsupported) { showMessage('#ingest-message', `${unsupported.name} is not supported. Choose a Markdown (.md), text (.txt) or HTML (.html) file.`, true); return; }
  const tooLarge = files.find(file => file.size > 2 * 1024 * 1024);
  if (tooLarge) { showMessage('#ingest-message', `${tooLarge.name} is larger than 2 MB. Choose a smaller file.`, true); return; }
  const form = new FormData(); files.forEach(file => form.append('files', file));
  const button = $('#upload-button'); setBusy(button, true, 'Uploading…');
  try {
    const result = await api('/ingest/files', { method: 'POST', body: form });
    showMessage('#ingest-message', `Your files are saved and searchable. ${result.documents_loaded ?? files.length} document(s) are ready, with ${result.chunks_indexed ?? 'an updated number of'} text sections indexed. Next: open Ask and try a question about this material.`);
    fileInput.value = ''; updateSelectedFiles([]); await loadDocuments(); toast('Files uploaded and indexed. You can ask a question now.');
  } catch (error) { showMessage('#ingest-message', `Upload didn't finish. ${error.message}`, true); }
  finally { setBusy(button, false); }
});

$('#url-form').addEventListener('submit', async event => {
  event.preventDefault(); clearMessage('#ingest-message');
  const url = $('#url-input').value.trim();
  const button = $('#url-button'); setBusy(button, true, 'Reading page…');
  try {
    const result = await api('/ingest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ urls: [url] }) });
    showMessage('#ingest-message', `Page saved and indexed. ${result.chunks_indexed} text sections are searchable across ${result.documents_loaded} document(s). Next: open Ask and try a question about this page.`);
    $('#url-input').value = ''; await loadDocuments(); toast('Web page saved and indexed.');
  } catch (error) { showMessage('#ingest-message', `Couldn't add that page. ${error.message}`, true); }
  finally { setBusy(button, false); }
});

$('#build-index-button').addEventListener('click', async () => {
  clearMessage('#ingest-message');
  const button = $('#build-index-button'); setBusy(button, true, 'Rebuilding…');
  try {
    const result = await api('/ingest/local', { method: 'POST' });
    showMessage('#ingest-message', `Your library is refreshed. ${result.chunks_indexed} text sections have been indexed. Next: open Ask and enter a question about the updated documents.`);
    $$('.step-item').forEach(item => item.classList.remove('current'));
    $$('.step-item')[1]?.classList.add('current');
    await loadDocuments(); toast(`Library refreshed: ${result.chunks_indexed} text sections indexed.`);
  } catch (error) {
    showMessage('#ingest-message', `The library couldn't be built. ${error.message}\n\nCheck that your documents contain readable text. If this is the first run, the local embedding model may need to download and can take a few minutes.`, true);
  } finally { setBusy(button, false); }
});

$$('.feedback-button').forEach(button => button.addEventListener('click', async () => {
  if (!state.lastQuestion || !state.lastAnswer) return;
  try {
    await api('/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: state.lastQuestion, answer: state.lastAnswer, rating: button.dataset.rating }) });
    $$('.feedback-button').forEach(item => item.classList.toggle('selected', item === button));
    $('#feedback-message').textContent = 'Thanks — feedback saved.';
  } catch (error) { $('#feedback-message').textContent = `Couldn't save feedback: ${error.message}`; }
}));

checkHealth();
loadDocuments();
