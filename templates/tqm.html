<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daraz TQM Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f7f9fb; }
        .card { transition: all 0.3s ease; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); }
        .card:hover { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1); transform: translateY(-2px); }
        .row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px dashed #e5e7eb; }
        .row:last-child { border-bottom: none; }
        .modal-overlay { background-color: rgba(0, 0, 0, 0.5); z-index: 50; }
        .modal-content { max-height: 80vh; max-width: 90vw; }
        .data-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
        .data-grid > div { background: white; padding: 1rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    </style>
</head>
<body class="p-4 sm:p-8">

    <!-- Header and Controls -->
    <header class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800">Daraz TQM Dashboard / Vendor Payment Tracker</h1>
        <form id="filter-form" class="flex flex-col sm:flex-row items-end gap-3 mt-4 bg-white p-4 rounded-lg shadow-sm">
            <div class="flex flex-col flex-grow w-full sm:w-auto">
                <label for="from" class="text-sm font-medium text-gray-600">Order Date From:</label>
                <input type="date" id="from" name="from" value="{{ created_after }}"
                       class="mt-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500">
            </div>
            <div class="flex flex-col flex-grow w-full sm:w-auto">
                <label for="to" class="text-sm font-medium text-gray-600">Order Date To (Optional):</label>
                <input type="date" id="to" name="to" value="{{ created_before }}"
                       class="mt-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500">
            </div>
            <button type="submit"
                    class="w-full sm:w-auto px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md shadow-md hover:bg-indigo-700 transition duration-150">
                Apply Filter
            </button>
        </form>
    </header>

    <!-- Stat Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">

        <!-- Net Payables (Liability Card) -->
        <div class="card p-5 bg-white rounded-xl border border-gray-200">
            <h3 class="text-lg font-semibold text-gray-700 mb-2">Net Vendor Payables</h3>
            <p class="text-2xl font-bold {{ 'text-red-600' if stats.net_payables_raw is defined and stats.net_payables_raw > 0 else 'text-green-600' }}">
                {{ stats.net_payables }}
            </p>
            <p class="text-sm text-gray-500 mt-2">Total Liability - Payments Made
            </p>
            <button onclick="openPaymentModal()"
                    class="mt-3 text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                Record New Payment
            </button>
        </div>

        <!-- Total Vendor Cost (Liability Breakdown) -->
        <div class="card p-5 bg-white rounded-xl border border-gray-200">
            <h3 class="text-lg font-semibold text-gray-700 mb-2">Total Vendor Cost Liability</h3>
            <div class="card-content">
                <div class="row text-lg font-bold"><span>Total Cost</span><span class="text-gray-900">{{ stats.vendor_cost_total }}</span></div>
                <div class="row text-sm text-gray-500 mt-1"><span>- Tick Bags Liability</span><span>{{ stats.payables_tick }}</span></div>
                <div class="row text-sm text-gray-500"><span>- Sleek Space Liability</span><span>{{ stats.payables_sleek }}</span></div>
            </div>
            <p class="text-sm text-gray-500 mt-2">Total Cost of Goods & Packaging</p>
        </div>

        <!-- Total Payments Made -->
        <div class="card p-5 bg-white rounded-xl border border-gray-200">
            <h3 class="text-lg font-semibold text-gray-700 mb-2">Total Payments Recorded</h3>
            <p class="text-2xl font-bold text-green-600">
                {{ stats.total_paid }}
            </p>
            <p class="text-sm text-gray-500 mt-2">Historic Payments to Vendors</p>
            <button onclick="openHistoryModal()"
                    class="mt-3 text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                View Payment History
            </button>
        </div>

        <!-- Net Profit Collected -->
        <div class="card p-5 bg-white rounded-xl border border-gray-200">
            <h3 class="text-lg font-semibold text-gray-700 mb-2">Net Profit Collected</h3>
            <p class="text-2xl font-bold text-blue-600">
                {{ stats.net_profit_collected }}
            </p>
            <p class="text-sm text-gray-500 mt-2">Profit from Paid/Settled Orders (After Daraz Fees)</p>
        </div>

    </div>

    <!-- Order List -->
    <div class="bg-white rounded-xl shadow-lg p-6">
        <h2 class="text-2xl font-semibold text-gray-800 mb-4">{{ orders | length }} Orders Found</h2>
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead>
                    <tr class="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wider">
                        <th class="px-3 py-3 text-left">Order ID / Date</th>
                        <th class="px-3 py-3 text-left">Customer / Address</th>
                        <th class="px-3 py-3 text-right">Invoice Status</th>
                        <th class="px-3 py-3 text-right">Net Received</th>
                        <th class="px-3 py-3 text-right">Vendor Cost</th>
                        <th class="px-3 py-3 text-right">Net Profit</th>
                        <th class="px-3 py-3 text-center">Items</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {% for order in orders %}
                    <tr class="hover:bg-gray-50">
                        <td class="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {{ order.order_id }}<br>
                            <span class="text-xs text-gray-500">{{ order.order_date }}</span>
                        </td>
                        <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                            <strong>{{ order.customer.name }}</strong><br>
                            <span class="text-xs">{{ order.customer.address | first_words(6) }}</span>
                        </td>
                        <td class="px-3 py-4 whitespace-nowrap text-right">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full
                                {% if 'Paid' in order.paid_status %} bg-green-100 text-green-800
                                {% elif 'Not Paid' in order.paid_status %} bg-yellow-100 text-yellow-800
                                {% else %} bg-red-100 text-red-800
                                {% endif %}"
                            >
                                {{ order.paid_status }}
                            </span>
                            <br>
                            <span class="text-xs text-gray-500">{{ order.statement | first_words(4) }}</span>
                        </td>
                        <td class="px-3 py-4 whitespace-nowrap text-sm text-right text-gray-900 font-medium">
                            {{ order.invoice_amount }}
                        </td>
                        <td class="px-3 py-4 whitespace-nowrap text-sm text-right text-red-600 font-medium">
                            {{ order.product_cost_total }}<br>
                            <span class="text-xs text-gray-500">+ {{ order.packaging_total }} (Pkg)</span>
                        </td>
                        <td class="px-3 py-4 whitespace-nowrap text-sm text-right font-bold
                            {% if order.net_profit_num | float < 0 %} text-red-700 {% else %} text-green-700 {% endif %}">
                            {{ order.net_profit }}
                        </td>
                        <td class="px-3 py-4 whitespace-nowrap text-center text-sm">
                            <button onclick="openDetailModal({{ order.order_id }})"
                                class="text-indigo-600 hover:text-indigo-900 text-sm font-medium">
                                {{ order.items_list | length }} Item(s)
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% if not orders %}
        <p class="text-center text-gray-500 py-10">No orders found matching your criteria.</p>
        {% endif %}
    </div>


    <!-- Modals (Hidden by default) -->
    <div id="detail-modal-overlay" class="modal-overlay fixed inset-0 hidden items-center justify-center">
        <div id="detail-modal" class="bg-white rounded-xl shadow-2xl p-6 w-11/12 md:w-4/5 lg:w-3/5 modal-content overflow-y-auto transform scale-95 transition-transform">
            <div class="flex justify-between items-start mb-4 border-b pb-2">
                <h3 class="text-xl font-bold text-gray-800">Order Details: <span id="modal-order-id" class="text-indigo-600"></span></h3>
                <button onclick="closeDetailModal()" class="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
            </div>
            <div id="modal-content-area" class="space-y-6">
                <!-- Content will be injected here -->
            </div>
        </div>
    </div>

    <!-- Record Payment Modal -->
    <div id="payment-modal-overlay" class="modal-overlay fixed inset-0 hidden items-center justify-center">
        <div class="bg-white rounded-xl shadow-2xl p-6 w-11/12 md:w-1/3 modal-content overflow-y-auto transform scale-95 transition-transform">
            <div class="flex justify-between items-start mb-4 border-b pb-2">
                <h3 class="text-xl font-bold text-gray-800">Record Vendor Payment</h3>
                <button onclick="closePaymentModal()" class="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
            </div>
            <form id="record-payment-form" class="space-y-4">
                <div>
                    <label for="payment-vendor" class="block text-sm font-medium text-gray-700">Vendor</label>
                    <select id="payment-vendor" name="vendor" required
                            class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                        {% for vendor in vendors %}
                        <option value="{{ vendor }}">{{ vendor }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div>
                    <label for="payment-amount" class="block text-sm font-medium text-gray-700">Amount (PKR)</label>
                    <input type="number" id="payment-amount" name="amount" step="0.01" min="0.01" required
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                </div>
                <div>
                    <label for="payment-date" class="block text-sm font-medium text-gray-700">Payment Date</label>
                    <!-- The value attribute was removed and is now set by JavaScript -->
                    <input type="date" id="payment-date" name="date" required
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                </div>
                <button type="submit" id="payment-submit-btn"
                        class="w-full px-4 py-2 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                    Record Payment
                </button>
                <div id="payment-message" class="text-center mt-3 hidden"></div>
            </form>
        </div>
    </div>

    <!-- Payment History Modal -->
    <div id="history-modal-overlay" class="modal-overlay fixed inset-0 hidden items-center justify-center">
        <div class="bg-white rounded-xl shadow-2xl p-6 w-11/12 md:w-2/3 lg:w-2/5 modal-content overflow-y-auto transform scale-95 transition-transform">
            <div class="flex justify-between items-start mb-4 border-b pb-2">
                <h3 class="text-xl font-bold text-gray-800">Vendor Payment History</h3>
                <button onclick="closeHistoryModal()" class="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
            </div>
            <div id="history-content-area" class="space-y-3">
                <!-- History will be injected here -->
                <p class="text-gray-500 text-center py-4" id="history-loading">Loading payment history...</p>
            </div>
            <div id="history-message" class="text-center mt-3 hidden"></div>
        </div>
    </div>


<script type="text/javascript">
    // Helper function to find order data by ID
    const ORDERS_DATA = JSON.parse('{{ orders | tojson }}');

    function getOrderData(orderId) {
        return ORDERS_DATA.find(o => String(o.order_id) === String(orderId));
    }

    function _d(x) {
        try {
            return parseFloat(String(x).replace(/[^0-9.-]/g, '')) || 0;
        } catch {
            return 0;
        }
    }

    // --- Detail Modal Functions ---

    function renderDetailContent(order) {
        let content = `
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                <div>
                    <p class="font-semibold text-gray-700">Customer Info:</p>
                    <p>${order.customer.name}</p>
                    <p class="text-xs text-gray-500">${order.customer.address}</p>
                    <p class="text-xs text-gray-500">${order.customer.phone}</p>
                </div>
                <div>
                    <p class="font-semibold text-gray-700">Financial Summary:</p>
                    <div class="row text-xs"><span>Order Price:</span><span>${order.price}</span></div>
                    <div class="row text-xs"><span>Net Received:</span><span class="font-bold">${order.invoice_amount}</span></div>
                    <div class="row text-xs"><span>Total Product Cost:</span><span class="text-red-600">${order.product_cost_total}</span></div>
                    <div class="row text-xs"><span>Total Packaging Cost:</span><span class="text-red-600">${order.packaging_total}</span></div>
                    <div class="row text-xs font-bold mt-1"><span>Net Profit:</span><span class="${_d(order.net_profit_num) < 0 ? 'text-red-700' : 'text-green-700'}">${order.net_profit}</span></div>
                    <p class="text-xs text-gray-500 mt-2 italic">Statement: ${order.statement || 'N/A'}</p>
                </div>
            </div>

            <h4 class="text-lg font-semibold text-gray-700 mt-4 mb-2">Invoice Breakdown (Net Received = Sum of below)</h4>
            <div class="data-grid text-xs">
                ${order.invoice_breakdown.map(item => `
                    <div class="row text-xs"><span>${item.label}:</span><span class="${_d(item.amount_fmt) < 0 ? 'text-red-600' : 'text-green-600'}">${item.amount_fmt}</span></div>
                `).join('')}
            </div>

            <h4 class="text-lg font-semibold text-gray-700 mt-6 mb-2">Order Items (Status & Costs)</h4>
            <div class="space-y-4">
            ${order.items_list.map(item => `
                <div class="data-grid border p-3 rounded-lg bg-gray-50">
                    <div class="sm:col-span-2">
                        <p class="font-bold text-sm">${item.item_title}</p>
                        <p class="text-xs text-gray-500">SKU: ${item.key}</p>
                        ${item.is_returned ? '<span class="text-xs font-semibold text-red-600">ITEM RETURNED / FAILED</span>' : ''}
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-700">Qty / Status</p>
                        <p class="text-sm">${item.quantity} / <span class="font-semibold text-indigo-600">${item.status}</span></p>
                    </div>
                    <div class="col-span-1 sm:col-span-2">
                        <p class="text-xs font-medium text-gray-700">Costs & Vendor</p>
                        <div class="flex justify-between text-xs">
                            <span>Product Cost:</span>
                            <span class="${item.is_returned ? 'line-through text-gray-400' : 'text-red-600'}">PKR ${item.product_cost}</span>
                        </div>
                        <div class="flex justify-between text-xs">
                            <span>Packaging Cost:</span>
                            <span class="text-red-600">PKR ${item.packaging}</span>
                        </div>
                        <div class="flex justify-between text-xs mt-1">
                            <span>Vendor:</span>
                            <span class="font-semibold text-gray-700">${item.vendor || 'Other'}</span>
                        </div>
                        ${item.needs_cost ? `
                        <div class="mt-2 p-2 bg-yellow-100 text-yellow-800 rounded-md text-xs">
                            ⚠️ Cost is missing. Please update.
                        </div>
                        <form onsubmit="saveItemCost(event, '${item.key}')" class="mt-2 space-y-1 text-xs">
                            <input type="hidden" name="key" value="${item.key}">
                            <input type="number" name="product_cost" placeholder="Product Cost" step="0.01" value="${item.product_cost}" class="w-full p-1 border rounded-md">
                            <input type="number" name="packaging" placeholder="Packaging Cost" step="0.01" value="${item.packaging}" class="w-full p-1 border rounded-md">
                            <select name="vendor" class="w-full p-1 border rounded-md">
                                {% for vendor in vendors %}
                                <option value="{{ vendor }}" ${item.vendor === '{{ vendor }}' ? 'selected' : ''}>{{ vendor }}</option>
                                {% endfor %}
                            </select>
                            <button type="submit" class="w-full bg-indigo-500 text-white py-1 rounded-md hover:bg-indigo-600">Save Cost</button>
                        </form>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
            </div>
        `;
        document.getElementById('modal-content-area').innerHTML = content;
    }

    function openDetailModal(orderId) {
        const order = getOrderData(orderId);
        if (!order) {
            console.error('Order not found:', orderId);
            return;
        }

        document.getElementById('modal-order-id').textContent = orderId;
        renderDetailContent(order);
        document.getElementById('detail-modal-overlay').classList.remove('hidden');
        document.getElementById('detail-modal-overlay').classList.add('flex');
    }

    function closeDetailModal() {
        document.getElementById('detail-modal-overlay').classList.add('hidden');
        document.getElementById('detail-modal-overlay').classList.remove('flex');
    }

    async function saveItemCost(event, itemKey) {
        event.preventDefault();
        const form = event.target;
        const key = form.elements['key'].value;
        const product_cost = form.elements['product_cost'].value;
        const packaging = form.elements['packaging'].value;
        const vendor = form.elements['vendor'].value;

        try {
            const response = await fetch('/api/save_cost', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, product_cost, packaging, vendor })
            });

            const result = await response.json();
            if (result.ok) {
                // Simplified success: just show a message and disable the form
                const saveButton = form.querySelector('button[type="submit"]');
                if (saveButton) {
                    saveButton.textContent = 'Saved!';
                    saveButton.classList.remove('bg-indigo-500', 'hover:bg-indigo-600');
                    saveButton.classList.add('bg-green-500');
                    saveButton.disabled = true;
                }
                // Optional: Reload the page to refresh all data if needed, but we'll rely on the manual reload for now
                // window.location.reload();
            } else {
                alert('Failed to save cost: ' + result.error);
            }
        } catch (error) {
            console.error('Save cost error:', error);
            alert('An unexpected error occurred while saving the cost.');
        }
    }


    // --- Record Payment Modal Functions ---

    function openPaymentModal() {
        document.getElementById('payment-modal-overlay').classList.remove('hidden');
        document.getElementById('payment-modal-overlay').classList.add('flex');
        document.getElementById('payment-message').classList.add('hidden');
        // Set default date to today using JavaScript
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('payment-date').value = today;
    }

    function closePaymentModal() {
        document.getElementById('payment-modal-overlay').classList.add('hidden');
        document.getElementById('payment-modal-overlay').classList.remove('flex');
    }

    document.getElementById('record-payment-form').addEventListener('submit', async function(event) {
        event.preventDefault();
        const form = event.target;
        const submitBtn = document.getElementById('payment-submit-btn');
        const messageDiv = document.getElementById('payment-message');
        messageDiv.classList.add('hidden');

        submitBtn.disabled = true;
        submitBtn.textContent = 'Recording...';

        const vendor = form.elements['vendor'].value;
        const amount = form.elements['amount'].value;
        const date = form.elements['date'].value;

        try {
            const response = await fetch('/api/record_payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vendor, amount: parseFloat(amount), date })
            });

            const result = await response.json();

            if (result.ok) {
                messageDiv.textContent = 'Payment recorded successfully!';
                messageDiv.classList.remove('hidden', 'text-red-600');
                messageDiv.classList.add('text-green-600');
                form.reset();
                setTimeout(() => {
                    closePaymentModal();
                    window.location.reload(); // Hard reload to update stats
                }, 1500);
            } else {
                messageDiv.textContent = 'Error: ' + (result.error || 'Failed to record payment.');
                messageDiv.classList.remove('hidden', 'text-green-600');
                messageDiv.classList.add('text-red-600');
            }
        } catch (error) {
            messageDiv.textContent = 'An unexpected error occurred.';
            messageDiv.classList.remove('hidden', 'text-green-600');
            messageDiv.classList.add('text-red-600');
            console.error('Payment record error:', error);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Record Payment';
        }
    });


    // --- Payment History Modal Functions ---

    function openHistoryModal() {
        document.getElementById('history-modal-overlay').classList.remove('hidden');
        document.getElementById('history-modal-overlay').classList.add('flex');
        loadPaymentHistory();
    }

    function closeHistoryModal() {
        document.getElementById('history-modal-overlay').classList.add('hidden');
        document.getElementById('history-modal-overlay').classList.remove('flex');
    }

    async function loadPaymentHistory() {
        const loadingDiv = document.getElementById('history-loading');
        const contentDiv = document.getElementById('history-content-area');
        loadingDiv.classList.remove('hidden');
        contentDiv.innerHTML = '';

        try {
            const response = await fetch('/api/get_payments');
            const result = await response.json();

            if (result.ok) {
                loadingDiv.classList.add('hidden');
                if (result.history.length === 0) {
                    contentDiv.innerHTML = '<p class="text-gray-500 text-center py-4">No payment history found.</p>';
                    return;
                }

                let historyHtml = `
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead>
                            <tr class="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                <th class="px-3 py-3 text-left">Date</th>
                                <th class="px-3 py-3 text-left">Vendor</th>
                                <th class="px-3 py-3 text-right">Amount</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                `;

                result.history.forEach(p => {
                    historyHtml += `
                        <tr class="hover:bg-gray-50">
                            <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-500">${p.date}</td>
                            <td class="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">${p.vendor}</td>
                            <td class="px-3 py-2 whitespace-nowrap text-sm text-right font-semibold text-green-700">${p.amount_fmt}</td>
                        </tr>
                    `;
                });

                historyHtml += `
                        </tbody>
                    </table>
                `;
                contentDiv.innerHTML = historyHtml;

            } else {
                loadingDiv.textContent = 'Error loading history: ' + (result.error || 'Unknown error.');
                loadingDiv.classList.remove('hidden');
                loadingDiv.classList.add('text-red-600');
            }
        } catch (error) {
            loadingDiv.textContent = 'An unexpected error occurred while fetching history.';
            loadingDiv.classList.remove('hidden');
            loadingDiv.classList.add('text-red-600');
            console.error('History load error:', error);
        }
    }

    // Set today's date for filter input if 'created_before' is empty (to default to filtering up to today)
    window.onload = function() {
        const toInput = document.getElementById('to');
        if (!toInput.value) {
            toInput.value = new Date().toISOString().split('T')[0];
        }
    }

</script>
</body>
</html>
