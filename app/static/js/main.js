// Main JavaScript file for common functionalities
document.addEventListener('DOMContentLoaded', function() {
    console.log('Main JS loaded. DOM fully loaded and parsed.');
    // Example: Add event listeners for Start/Stop buttons if they exist on the current page
    const startButton = document.getElementById('startStrategy');
    const stopButton = document.getElementById('stopStrategy');
    if(startButton) {
        startButton.addEventListener('click', () => alert('Start Strategy Clicked!'));
    }
    if(stopButton) {
        stopButton.addEventListener('click', () => alert('Stop Strategy Clicked!'));
    }
});
