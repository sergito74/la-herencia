const state = { purchases: [], catalogs: { suppliers: [], categories: [] }, sqlObjects: [] };
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const field = (row, name) => row[name] ?? row[name.charAt(0).toUpperCase() + name.slice(1)];

const formatMoney = value => new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(Number(value || 0));
const formatDate = value => value ? new Intl.DateTimeFormat('es-AR').format(new Date(value)) : '-';

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('No se pudo cargar la información.');
  return response.json();
}

async function loadDashboard() {
  const summary = await getJson('/api/dashboard');
  $('#metric-purchases').textContent = summary.purchases ?? 0;
  $('#metric-cattle').textContent = summary.cattleSales ?? 0;
  $('#metric-grains').textContent = summary.grainSales ?? 0;
  $('#metric-bank').textContent = summary.bankMovements ?? 0;
}

function purchaseRow(purchase) {
  return `<tr class="clickable-row" data-purchase-id="${field(purchase, 'id')}"><td>${formatDate(field(purchase, 'date'))}</td><td><strong>${field(purchase, 'supplier') || 'Sin proveedor'}</strong></td><td>${field(purchase, 'documentType') || '-'}</td><td>${field(purchase, 'letter') || ''} ${field(purchase, 'documentNumber') || '-'}</td><td>${formatMoney(field(purchase, 'subtotal'))}</td><td>${formatMoney(field(purchase, 'tax'))}</td></tr>`;
}

async function loadPurchases() {
  state.purchases = await getJson('/api/purchases');
  renderPurchases();
}

function renderPurchases() {
  const term = ($('#purchase-search')?.value || '').toLowerCase();
  const filtered = state.purchases.filter(purchase => `${field(purchase, 'supplier') || ''} ${field(purchase, 'documentNumber') || ''}`.toLowerCase().includes(term));
  const html = filtered.length ? filtered.map(purchaseRow).join('') : '<tr><td colspan="6" class="empty">No hay compras para mostrar.</td></tr>';
  $('#all-purchases').innerHTML = html;
  $('#recent-purchases').innerHTML = filtered.slice(0, 6).map(purchaseRow).join('') || '<tr><td colspan="5" class="empty">No hay actividad reciente.</td></tr>';
}

async function loadCatalogs() {
  state.catalogs = await getJson('/api/catalogs');
  $('#supplier-select').innerHTML = '<option value="">Seleccionar proveedor</option>' + state.catalogs.suppliers.map(item => `<option value="${field(item, 'id')}">${field(item, 'name')}</option>`).join('');
  $$('.line-category').forEach(select => fillCategories(select));
}

function fillCategories(select) {
  select.innerHTML = '<option value="">Rubro</option>' + state.catalogs.categories.map(item => `<option value="${field(item, 'id')}">${field(item, 'name')}</option>`).join('');
}

function showView(viewName) {
  $$('.view').forEach(view => view.classList.toggle('active-view', view.id === `${viewName}-view`));
  $$('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === viewName));
  const titles = { overview: 'Resumen operativo', purchases: 'Compras', accounts: 'Cuentas corrientes', 'new-purchase': 'Nueva compra', operations: 'Operaciones', treasury: 'Tesorería', reports: 'Informes', 'sql-data': 'Datos SQL' };
  $('#page-title').textContent = titles[viewName] || 'La Herencia';
  if (viewName === 'purchases') loadPurchases().catch(showError);
  if (viewName === 'accounts') loadAccounts().catch(showError);
  if (viewName === 'operations') loadOperations().catch(showError);
  if (viewName === 'treasury') loadTreasury().catch(showError);
  if (viewName === 'sql-data' && !state.sqlObjects.length) loadSqlObjects().catch(showError);
}

async function loadOperations() {
  const data = await getJson('/api/operations');
  $('#cattle-count').textContent = `${data.cattle.length} operaciones mostradas`;
  $('#grain-count').textContent = `${data.grains.length} operaciones mostradas`;
  $('#cattle-operations').innerHTML = data.cattle.map(item => `<tr><td>${formatDate(field(item, 'date'))}</td><td>${field(item, 'documentNumber') || '-'}</td><td>#${field(item, 'consigneeId') ?? '-'}</td><td>${formatMoney(field(item, 'freight'))}</td><td>${formatMoney(field(item, 'otherExpenses'))}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">No hay ventas de hacienda.</td></tr>';
  $('#grain-operations').innerHTML = data.grains.map(item => `<tr><td>${formatDate(field(item, 'date'))}</td><td><strong>${field(item, 'grain') || '-'}</strong></td><td>${field(item, 'documentNumber') || '-'}</td><td>${field(item, 'quantity') ?? '-'}</td><td>${formatMoney(field(item, 'unitPrice'))}</td><td>${formatMoney(field(item, 'netReceivable'))}</td></tr>`).join('') || '<tr><td colspan="6" class="empty">No hay ventas de granos.</td></tr>';
}

async function loadTreasury() {
  const accounts = await getJson('/api/treasury/accounts');
  $('#treasury-account').innerHTML = '<option value="">Todas las cuentas</option>' + accounts.map(item => `<option value="${field(item, 'account')}">${field(item, 'account')} (${field(item, 'movementCount')} movimientos)</option>`).join('');
  $('#treasury-cashbox').innerHTML = '<option value="">Todas las cajas</option>' + [...new Set(accounts.map(item => field(item, 'cashbox')))].filter(Boolean).map(item => `<option value="${item}">${item}</option>`).join('');
  await loadTreasuryMovements();
}

async function loadTreasuryMovements() {
  const account = encodeURIComponent($('#treasury-account').value);
  const cashbox = encodeURIComponent($('#treasury-cashbox').value);
  const movements = await getJson(`/api/treasury/movements?account=${account}&cashbox=${cashbox}`);
  $('#treasury-movements').innerHTML = movements.map(item => `<tr><td>${formatDate(field(item, 'date'))}</td><td>${field(item, 'movementType') || '-'}</td><td>${field(item, 'documentType') || '-'} ${field(item, 'documentNumber') || ''}</td><td>${field(item, 'account') || '-'}</td><td>${field(item, 'cashbox') || '-'}</td><td>${formatMoney(field(item, 'amount'))}</td><td>#${field(item, 'contactId') || '-'}</td></tr>`).join('') || '<tr><td colspan="7" class="empty">No hay movimientos para los filtros seleccionados.</td></tr>';
}

async function loadAccounts() {
  const search = encodeURIComponent($('#account-search').value);
  const type = encodeURIComponent($('#account-type').value);
  const accounts = await getJson(`/api/accounts?search=${search}&type=${type}`);
  $('#account-list').innerHTML = accounts.map(item => `<button class="account-item" data-account-id="${field(item, 'id')}"><strong>${field(item, 'name')}</strong><small>${field(item, 'contactType')} · Saldo ${formatMoney(field(item, 'netBalance'))}</small></button>`).join('') || '<p class="empty">No se encontraron entidades.</p>';
  $$('.account-item').forEach(item => item.addEventListener('click', () => loadAccountDetail(item.dataset.accountId).catch(showError)));
}

async function loadAccountDetail(id) {
  const movements = await getJson(`/api/accounts/${id}`);
  const first = movements[0];
  $('#account-summary').className = 'account-summary';
  $('#account-summary').innerHTML = `<div><p class="eyebrow">CUENTA CORRIENTE</p><h3>${field(first, 'name') || 'Entidad'}</h3><p class="muted">${movements.length} movimientos · saldo actual ${formatMoney(field(first, 'runningBalance'))}</p></div>`;
  $('#account-movements').innerHTML = movements.map(item => `<tr><td>${formatDate(field(item, 'date'))}</td><td>${field(item, 'document') || '-'}</td><td>${field(item, 'documentNumber') || '-'}</td><td>${formatMoney(field(item, 'debt'))}</td><td>${formatMoney(field(item, 'credit'))}</td><td>${formatMoney(field(item, 'runningBalance'))}</td><td>${field(item, 'origin') || '-'} #${field(item, 'originId') || ''}</td></tr>`).join('') || '<tr><td colspan="7" class="empty">La entidad no tiene movimientos.</td></tr>';
}

async function loadSqlObjects() {
  state.sqlObjects = await getJson('/api/sql-objects');
  renderSqlObjects();
}

function renderSqlObjects() {
  const term = ($('#sql-object-search')?.value || '').toLowerCase();
  const objects = state.sqlObjects.filter(item => `${field(item, 'name')} ${field(item, 'type')}`.toLowerCase().includes(term));
  $('#sql-objects').innerHTML = objects.map(item => `<button class="sql-object" data-sql-name="${field(item, 'name')}"><span>${field(item, 'name')}</span><small>${field(item, 'type') === 'VIEW' ? 'Vista' : 'Tabla'}</small></button>`).join('') || '<p class="empty">No hay objetos.</p>';
  $$('.sql-object').forEach(item => item.addEventListener('click', () => loadSqlPreview(item.dataset.sqlName)));
}

async function loadSqlPreview(name) {
  $('#sql-selected-name').textContent = name;
  $('#sql-row-count').textContent = 'Consultando...';
  const rows = await getJson(`/api/sql-preview?name=${encodeURIComponent(name)}&limit=100`);
  const columns = rows.length ? Object.keys(rows[0]) : [];
  $('#sql-preview-head').innerHTML = columns.map(column => `<th>${column}</th>`).join('');
  $('#sql-preview-body').innerHTML = rows.length ? rows.map(row => `<tr>${columns.map(column => `<td>${row[column] ?? '<span class="null-value">NULL</span>'}</td>`).join('')}</tr>`).join('') : '<tr><td class="empty">El objeto no tiene registros.</td></tr>';
  $('#sql-row-count').textContent = `${rows.length} registros mostrados`;
}

function showError(error) { showToast(error.message || 'Ocurrió un error.', true); }
function showToast(message, isError = false) { const toast = $('#toast'); toast.textContent = message; toast.className = `toast visible ${isError ? 'error' : ''}`; setTimeout(() => toast.classList.remove('visible'), 3500); }

function addLine() {
  const template = $('.line-row').cloneNode(true);
  template.querySelectorAll('input').forEach(input => input.value = input.classList.contains('line-tax') ? '21' : '');
  fillCategories($('.line-category', template));
  $('#purchase-lines').appendChild(template);
}

async function submitPurchase(event) {
  event.preventDefault();
  showToast('El sistema está en modo consulta. No se permiten modificaciones.', true);
  return;
  const form = event.target;
  const lines = $$('.line-row').map(row => ({ quantity: Number($('.line-quantity', row).value) || null, description: $('.line-description', row).value, categoryId: Number($('.line-category', row).value) || null, netAmount: Number($('.line-net', row).value) || null, taxRate: Number($('.line-tax', row).value) || null })).filter(line => line.description.trim());
  const data = { date: form.date.value, supplierId: Number(form.supplierId.value), documentType: form.documentType.value, letter: form.letter.value, documentNumber: form.documentNumber.value, grossIncomeTax: Number(form.grossIncomeTax.value) || null, nonTaxable: null, lines };
  const response = await fetch('/api/purchases', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.message || 'No se pudo guardar la compra.');
  form.reset();
  $('#purchase-lines').innerHTML = '';
  addLine();
  showToast(`Compra #${result.id} guardada correctamente.`);
  await loadPurchases();
  showView('purchases');
}

$$('.nav-item').forEach(item => item.addEventListener('click', () => showView(item.dataset.view)));
$$('[data-view-target]').forEach(item => item.addEventListener('click', () => showView(item.dataset.viewTarget)));
$('#refresh-purchases').addEventListener('click', () => loadPurchases().catch(showError));
$('#purchase-search').addEventListener('input', renderPurchases);
$('#add-line').addEventListener('click', addLine);
$('#purchase-lines').addEventListener('click', event => { if (event.target.classList.contains('remove-line') && $$('.line-row').length > 1) event.target.closest('.line-row').remove(); });
$('#purchase-form').addEventListener('submit', event => submitPurchase(event).catch(showError));
$('#sql-object-search').addEventListener('input', renderSqlObjects);
$('#account-search').addEventListener('input', () => loadAccounts().catch(showError));
$('#account-type').addEventListener('change', () => loadAccounts().catch(showError));
$('#treasury-account').addEventListener('change', () => loadTreasuryMovements().catch(showError));
$('#treasury-cashbox').addEventListener('change', () => loadTreasuryMovements().catch(showError));
$('#refresh-treasury').addEventListener('click', () => loadTreasury().catch(showError));
document.addEventListener('click', event => {
  const row = event.target.closest('[data-purchase-id]');
  if (row) loadPurchaseDetail(row.dataset.purchaseId).catch(showError);
});

async function loadPurchaseDetail(id) {
  const data = await getJson(`/api/purchases/${id}`);
  const detail = data.details.map(item => `${field(item, 'description') || 'Sin descripción'}: ${field(item, 'quantity') ?? 0} x ${formatMoney(field(item, 'netAmount'))} + IVA ${field(item, 'taxRate') ?? 0}%`).join('\n');
  showToast(`Compra #${id}\n${detail || 'Sin detalle'}`);
}

Promise.all([loadDashboard(), loadCatalogs(), loadPurchases()]).catch(showError);
