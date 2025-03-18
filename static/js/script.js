// DOM Content Loaded Event
document.addEventListener('DOMContentLoaded', function() {
    // Initialize date pickers if they exist
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if (startDateInput && endDateInput) {
        // Set max date to today
        const today = new Date().toISOString().split('T')[0];
        startDateInput.max = today;
        endDateInput.max = today;
        
        // Set default end date to today if not already set
        if (!endDateInput.value) {
            endDateInput.value = today;
        }
        
        // Set default start date to 7 days ago if not already set
        if (!startDateInput.value) {
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            startDateInput.value = sevenDaysAgo.toISOString().split('T')[0];
        }
        
        // Ensure end date is not before start date
        startDateInput.addEventListener('change', function() {
            if (endDateInput.value && this.value > endDateInput.value) {
                endDateInput.value = this.value;
            }
        });
        
        endDateInput.addEventListener('change', function() {
            if (startDateInput.value && this.value < startDateInput.value) {
                startDateInput.value = this.value;
            }
        });
    }
    
    // Process Comments buttons
    const processButtons = document.querySelectorAll('.process-comments-btn');
    if (processButtons.length > 0) {
        processButtons.forEach(button => {
            button.addEventListener('click', function() {
                const channelId = this.getAttribute('data-channel-id');
                const startDate = document.getElementById('start_date_' + channelId) ? 
                                 document.getElementById('start_date_' + channelId).value : null;
                const endDate = document.getElementById('end_date_' + channelId) ? 
                               document.getElementById('end_date_' + channelId).value : null;
                
                processComments(channelId, startDate, endDate);
            });
        });
    }
    
    // Add Channel form validation
    const addChannelForm = document.getElementById('add-channel-form');
    if (addChannelForm) {
        addChannelForm.addEventListener('submit', function(event) {
            const channelIdInput = document.getElementById('channel_id');
            if (!channelIdInput.value.trim()) {
                event.preventDefault();
                showAlert('Please enter a YouTube Channel ID', 'danger');
            }
        });
    }
    
    // Verification code form validation
    const verifyForm = document.getElementById('verify-channel-form');
    if (verifyForm) {
        verifyForm.addEventListener('submit', function(event) {
            const codeInput = document.getElementById('verification_code');
            if (!codeInput.value.trim() || codeInput.value.trim().length !== 6) {
                event.preventDefault();
                showAlert('Please enter a valid 6-digit verification code', 'danger');
            }
        });
    }
});

/**
 * Process comments for a YouTube channel
 * @param {number} channelId - The channel ID in our database
 * @param {string} startDate - The start date in YYYY-MM-DD format
 * @param {string} endDate - The end date in YYYY-MM-DD format
 */
function processComments(channelId, startDate, endDate) {
    // Show loading state
    const button = document.querySelector(`.process-comments-btn[data-channel-id="${channelId}"]`);
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    // Prepare data
    const data = {
        start_date: startDate,
        end_date: endDate
    };
    
    // Send AJAX request
    fetch(`/process_comments/${channelId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        // Reset button state
        button.disabled = false;
        button.innerHTML = originalText;
        
        // Show result
        if (data.success) {
            showAlert(data.message, 'success');
            // If we processed comments, refresh the page after a delay
            if (data.processed > 0) {
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            }
        } else {
            showAlert(data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        button.disabled = false;
        button.innerHTML = originalText;
        showAlert('An error occurred. Please try again.', 'danger');
    });
}

/**
 * Show an alert message
 * @param {string} message - The message to display
 * @param {string} type - The alert type (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    alertsContainer.innerHTML += alertHtml;
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            alertElement.classList.remove('show');
            setTimeout(() => {
                alertElement.remove();
            }, 150);
        }
    }, 5000);
}
