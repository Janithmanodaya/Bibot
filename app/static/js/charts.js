// Global Chart instance variable
let priceChartInstance = null;
let currentChartSymbol = null;
let currentChartTimeframe = null; // To store current timeframe string e.g. "1m", "5m"
let socket = null;

function getSocket() {
    if (!socket || !socket.connected) {
        if (typeof io === 'undefined') {
            console.error("Socket.IO client not found.");
            return null;
        }
        socket = io(location.protocol + '//' + document.domain + ':' + location.port);
        socket.on('connect', () => {
            console.log('Socket.IO connected for chart updates.');
            if (currentChartSymbol) subscribeToPriceUpdates(currentChartSymbol);
        });
        socket.on('disconnect', () => console.log('Socket.IO disconnected for chart updates.'));
        socket.on('connect_error', (err) => console.error('Chart Socket.IO connection error:', err));
        socket.on('price_update', function(data) {
            if (data.symbol === currentChartSymbol && priceChartInstance) {
                updateChartWithRealtimeData(data);
            }
        });
        socket.on('status', (data) => console.log('Subscription status:', data.data));
    }
    return socket;
}

function subscribeToPriceUpdates(symbol) {
    const s = getSocket();
    if (s && symbol) {
        console.log(`Subscribing to price updates for ${symbol}`);
        s.emit('subscribe_to_symbol_price', { symbol: symbol });
        currentChartSymbol = symbol; // Set after successful emit or confirmation? For now, optimistic.
    }
}

function unsubscribeFromPriceUpdates(symbol) {
    const s = getSocket();
    if (s && symbol) {
        console.log(`Unsubscribing from price updates for ${symbol}`);
        s.emit('unsubscribe_from_symbol_price', { symbol: symbol });
        if (currentChartSymbol === symbol) currentChartSymbol = null;
    }
}

async function fetchOhlcData(symbol, timeframe, limit = 200) {
    // Ensure timeframe is passed to API
    const response = await fetch(`/api/ohlc_data?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

function timeframeToMilliseconds(timeframeStr) {
    if (!timeframeStr) return 0;
    const unit = timeframeStr.slice(-1);
    const value = parseInt(timeframeStr.slice(0, -1));
    if (isNaN(value)) return 0;

    if (unit === 'm') return value * 60 * 1000;
    if (unit === 'h') return value * 60 * 60 * 1000;
    if (unit === 'd') return value * 24 * 60 * 60 * 1000;
    console.error("Unsupported timeframe unit for ms conversion:", timeframeStr);
    return 0;
}

function updateChartWithRealtimeData(priceData) {
    if (!priceChartInstance || !priceChartInstance.data.datasets[0] || !currentChartTimeframe) {
        // console.warn("Chart not ready for update:", !priceChartInstance, !priceChartInstance.data.datasets[0], !currentChartTimeframe);
        return;
    }

    const dataset = priceChartInstance.data.datasets[0].data;
    if (dataset.length === 0) {
        console.warn("Chart dataset is empty, cannot update with real-time data yet.");
        return;
    }

    const newPrice = parseFloat(priceData.price);
    const eventTime = parseInt(priceData.event_time);

    if (isNaN(newPrice) || isNaN(eventTime)) {
        console.error("Invalid price or event_time in priceData:", priceData);
        return;
    }

    const intervalMs = timeframeToMilliseconds(currentChartTimeframe);
    if (intervalMs === 0) {
        console.error("IntervalMs is 0, cannot process candle update for timeframe:", currentChartTimeframe);
        return;
    }

    let lastCandle = dataset[dataset.length - 1];
    const lastCandleOpenTime = lastCandle.x; // This is a timestamp
    const nextCandleOpenTime = lastCandleOpenTime + intervalMs;

    if (eventTime >= lastCandleOpenTime && eventTime < nextCandleOpenTime) {
        // Update falls within the current last candle's interval
        lastCandle.c = newPrice;
        if (newPrice > lastCandle.h) lastCandle.h = newPrice;
        if (newPrice < lastCandle.l) lastCandle.l = newPrice;
    } else if (eventTime >= nextCandleOpenTime) {
        // Price update signifies a new candle or candles
        let currentNewCandleOpenTime = nextCandleOpenTime;
        // Loop to fill potential gaps if multiple candle periods have passed
        while(eventTime >= currentNewCandleOpenTime + intervalMs) {
            const gapCandle = {
                x: currentNewCandleOpenTime,
                o: lastCandle.c, h: lastCandle.c, l: lastCandle.c, c: lastCandle.c // Fill with previous close
            };
            dataset.push(gapCandle);
            lastCandle = gapCandle; // The newly added gap candle is now the last one
            currentNewCandleOpenTime += intervalMs;
        }

        // Create the actual new candle for the current eventTime period
        const newCandle = {
            x: currentNewCandleOpenTime,
            o: newPrice, h: newPrice, l: newPrice, c: newPrice
        };
        dataset.push(newCandle);

        const MAX_CANDLES_DISPLAYED = 500; // Example limit
        while (dataset.length > MAX_CANDLES_DISPLAYED) {
            dataset.shift();
        }
    } else {
        // Event time is before the last candle's open time (e.g. old message, ignore)
        // console.log("Received old price update, ignoring.", {eventTime: eventTime, lastCandleOpenTime: lastCandleOpenTime});
    }
    priceChartInstance.update('quiet');
}

function renderPriceChart(ohlcData, symbol, timeframe) {
    // Store the timeframe, it's used by updateChartWithRealtimeData
    currentChartTimeframe = timeframe;
    const ctx = document.getElementById('priceChart').getContext('2d');

    // Ensure data is sorted by time for candlestick
    ohlcData.sort((a, b) => a.x - b.x);

    const chartData = {
        datasets: [{
            label: `${symbol} (${timeframe}) Price`,
            data: ohlcData, // Expects {x, o, h, l, c}
            // type: 'candlestick', // Already default for the chart instance type
        }]
    };

    if (priceChartInstance) {
        priceChartInstance.destroy();
    }

    priceChartInstance = new Chart(ctx, {
        type: 'candlestick', // Ensure this type is registered if using extensions
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute', // This should be dynamically set based on timeframe
                        tooltipFormat: 'PPpp' // Example: Feb 2, 2024, 10:30:00 AM
                    },
                    title: { display: true, text: 'Time' }
                },
                y: {
                    title: { display: true, text: 'Price' }
                }
            },
            plugins: {
                tooltip: {
                    intersect: false,
                    mode: 'index',
                    callbacks: {
                        label: function(context) {
                            const d = context.raw;
                            if (d && typeof d.o !== 'undefined') {
                                return `O:${d.o} H:${d.h} L:${d.l} C:${d.c}`;
                            }
                            return `${context.dataset.label}: ${context.parsed.y}`;
                        }
                    }
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    getSocket(); // Initialize socket connection early
    const loadChartBtn = document.getElementById('load-chart-btn');

    if (loadChartBtn) {
        loadChartBtn.addEventListener('click', async function() {
            const symbol = document.getElementById('chart-symbol').value.toUpperCase();
            const timeframe = document.getElementById('chart-timeframe').value;

            // Unsubscribe from old symbol if currentChartSymbol is set and different
            if (currentChartSymbol && currentChartSymbol !== symbol) {
                unsubscribeFromPriceUpdates(currentChartSymbol);
            }
            // Update currentChartTimeframe regardless, as it might change even for the same symbol
            currentChartTimeframe = timeframe;

            try {
                const ohlcData = await fetchOhlcData(symbol, timeframe); // Pass timeframe
                if (ohlcData && ohlcData.length > 0) {
                    renderPriceChart(ohlcData, symbol, timeframe); // Pass timeframe to render
                    // Subscribe to new symbol's updates if it's different or no symbol was current
                    if (currentChartSymbol !== symbol) {
                         subscribeToPriceUpdates(symbol);
                    } else if (!currentChartSymbol) { // Or if no symbol was subscribed yet
                         subscribeToPriceUpdates(symbol);
                    }
                } else {
                    alert(`No OHLC data found for ${symbol} with timeframe ${timeframe}.`);
                    if (priceChartInstance) priceChartInstance.destroy();
                    if (currentChartSymbol) unsubscribeFromPriceUpdates(currentChartSymbol); // Unsubscribe if chart is cleared
                    currentChartSymbol = null;
                    currentChartTimeframe = null;
                }
            } catch (error) {
                console.error(`Failed to load chart data for ${symbol} / ${timeframe}:`, error);
                alert(`Failed to load chart data: ${error.message}. Check console.`);
                if (priceChartInstance) priceChartInstance.destroy();
                if (currentChartSymbol) unsubscribeFromPriceUpdates(currentChartSymbol);
                currentChartSymbol = null;
                currentChartTimeframe = null;
            }
        });
    }
});
