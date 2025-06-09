let priceChartInstance = null;
let currentChartSymbol = null;
let currentChartTimeframe = null;
let socket = null;

function getSocket() { /* ... (same as before) ... */
    if (!socket || !socket.connected) {
        if (typeof io === 'undefined') { console.error("Socket.IO client not found."); return null; }
        socket = io(location.protocol + '//' + document.domain + ':' + location.port);
        socket.on('connect', () => { if (currentChartSymbol) subscribeToPriceUpdates(currentChartSymbol); });
        socket.on('disconnect', () => console.log('Socket.IO disconnected for chart updates.'));
        socket.on('connect_error', (err) => console.error('Chart Socket.IO connection error:', err));
        socket.on('price_update', data => { if (data.symbol === currentChartSymbol && priceChartInstance) updateChartWithRealtimeData(data); });
        socket.on('status', data => console.log('Subscription status:', data.data));
    }
    return socket;
}
function subscribeToPriceUpdates(symbol) { /* ... (same as before) ... */
    const s = getSocket(); if (s && symbol) s.emit('subscribe_to_symbol_price', { symbol: symbol }); currentChartSymbol = symbol;
}
function unsubscribeFromPriceUpdates(symbol) { /* ... (same as before) ... */
    const s = getSocket(); if (s && symbol) s.emit('unsubscribe_from_symbol_price', { symbol: symbol }); if (currentChartSymbol === symbol) currentChartSymbol = null;
}

async function fetchOhlcData(symbol, timeframe, limit = 200, indicators = []) {
    let url = `/api/ohlc_data?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`;
    if (indicators.length > 0) {
        url += `&indicators=${indicators.join(',')}`;
    }
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}, message: ${await response.text()}`);
    return await response.json();
}

function timeframeToMilliseconds(timeframeStr) { /* ... (same as before) ... */
    if (!timeframeStr) return 0; const unit = timeframeStr.slice(-1); const value = parseInt(timeframeStr.slice(0, -1)); if (isNaN(value)) return 0;
    if (unit === 'm') return value * 60 * 1000; if (unit === 'h') return value * 60 * 60 * 1000; if (unit === 'd') return value * 24 * 60 * 60 * 1000; return 0;
}

function updateChartWithRealtimeData(priceData) { /* ... (same as before, advanced logic) ... */
    if (!priceChartInstance || !priceChartInstance.data.datasets[0] || !currentChartTimeframe) return;
    const ohlcDataset = priceChartInstance.data.datasets.find(ds => ds.type === 'candlestick' || ds.label.includes('Price'));
    if (!ohlcDataset || ohlcDataset.data.length === 0) return;
    const dataset = ohlcDataset.data;

    const newPrice = parseFloat(priceData.price); const eventTime = parseInt(priceData.event_time);
    if (isNaN(newPrice) || isNaN(eventTime)) { console.error("Invalid price/event_time:", priceData); return; }
    const intervalMs = timeframeToMilliseconds(currentChartTimeframe); if (intervalMs === 0) return;
    let lastCandle = dataset[dataset.length - 1]; const lastCandleOpenTime = lastCandle.x; const nextCandleOpenTime = lastCandleOpenTime + intervalMs;
    if (eventTime >= lastCandleOpenTime && eventTime < nextCandleOpenTime) {
        lastCandle.c = newPrice; if (newPrice > lastCandle.h) lastCandle.h = newPrice; if (newPrice < lastCandle.l) lastCandle.l = newPrice;
    } else if (eventTime >= nextCandleOpenTime) {
        let currentNewCandleOpenTime = nextCandleOpenTime;
        while(eventTime >= currentNewCandleOpenTime + intervalMs) {
            dataset.push({ x: currentNewCandleOpenTime, o: lastCandle.c, h: lastCandle.c, l: lastCandle.c, c: lastCandle.c });
            lastCandle = dataset[dataset.length-1]; currentNewCandleOpenTime += intervalMs;
        }
        dataset.push({ x: currentNewCandleOpenTime, o: newPrice, h: newPrice, l: newPrice, c: newPrice });
        const MAX_CANDLES = 500; if (dataset.length > MAX_CANDLES) dataset.splice(0, dataset.length - MAX_CANDLES);
    }
    // TODO: Update indicators based on new price data if needed, or wait for full refresh.
    priceChartInstance.update('quiet');
}

function renderPriceChart(apiResponse, symbol, timeframe) {
    currentChartTimeframe = timeframe;
    const ctx = document.getElementById('priceChart').getContext('2d');

    const ohlcData = apiResponse.ohlc || [];
    ohlcData.sort((a, b) => a.x - b.x);

    const datasets = [{
        label: `${symbol} (${timeframe}) Price`,
        data: ohlcData,
        type: 'candlestick',
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)'
    }];

    const indicatorColors = ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)', 'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)'];
    let colorIndex = 0;
    for (const key in apiResponse) {
        if (key !== 'ohlc' && Array.isArray(apiResponse[key])) {
            const indicatorData = apiResponse[key].map(point => ({x: point.x, y: parseFloat(point.y)}));
            indicatorData.sort((a,b) => a.x - b.x);
            datasets.push({
                label: key.toUpperCase(),
                data: indicatorData,
                type: 'line',
                borderColor: indicatorColors[colorIndex % indicatorColors.length],
                borderWidth: 1.5,
                fill: false,
                pointRadius: 0,
                yAxisID: 'y',
            });
            colorIndex++;
        }
    }

    if (priceChartInstance) priceChartInstance.destroy();

    priceChartInstance = new Chart(ctx, {
        data: { datasets: datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { x: { type: 'time', time: { unit: 'minute', tooltipFormat: 'PPpp' }, title: { display: true, text: 'Time' } },
                      y: { position: 'left', title: { display: true, text: 'Price' } } }, // Ensure y-axis is defined
            plugins: { tooltip: { intersect: false, mode: 'index', callbacks: { label: function(context) {
                const datasetLabel = context.dataset.label || '';
                const raw = context.raw;
                if (context.dataset.type === 'candlestick' && raw && typeof raw.o === 'number') {
                     return `${datasetLabel}: O:${raw.o.toFixed(2)} H:${raw.h.toFixed(2)} L:${raw.l.toFixed(2)} C:${raw.c.toFixed(2)}`;
                } else if (context.dataset.type === 'line') {
                     return `${datasetLabel}: ${context.parsed.y.toFixed(4)}`;
                }
                return `${datasetLabel}: ${context.parsed.y}`;
            }}}}
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    getSocket();
    const loadChartBtn = document.getElementById('load-chart-btn');
    const indicatorsSelect = document.getElementById('chart-indicators');


    if (loadChartBtn) {
        loadChartBtn.addEventListener('click', async function() {
            const symbol = document.getElementById('chart-symbol').value.toUpperCase();
            const timeframe = document.getElementById('chart-timeframe').value;
            const selectedIndicators = Array.from(indicatorsSelect.selectedOptions).map(opt => opt.value);

            if (currentChartSymbol && currentChartSymbol !== symbol) {
                unsubscribeFromPriceUpdates(currentChartSymbol);
            }
            currentChartTimeframe = timeframe;

            try {
                const apiResponse = await fetchOhlcData(symbol, timeframe, 200, selectedIndicators);
                if (apiResponse && apiResponse.ohlc && apiResponse.ohlc.length > 0) {
                    renderPriceChart(apiResponse, symbol, timeframe);
                    if (currentChartSymbol !== symbol || !socket.connected) { // Resubscribe if symbol changed or if socket reconnected
                         subscribeToPriceUpdates(symbol);
                    }
                } else {
                    alert(`No OHLC data for ${symbol}/${timeframe}.`);
                    if (priceChartInstance) priceChartInstance.destroy();
                    if (currentChartSymbol) unsubscribeFromPriceUpdates(currentChartSymbol);
                    currentChartSymbol = null; currentChartTimeframe = null;
                }
            } catch (error) {
                console.error(`Failed to load chart:`, error); alert(`Failed to load chart: ${error.message}`);
                if (priceChartInstance) priceChartInstance.destroy();
                if (currentChartSymbol) unsubscribeFromPriceUpdates(currentChartSymbol);
                currentChartSymbol = null; currentChartTimeframe = null;
            }
        });
    }
});
