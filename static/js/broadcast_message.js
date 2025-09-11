// Broadcast Message Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Broadcast Message Page');
    
    const messageTextarea = document.getElementById('message');
    const charCount = document.getElementById('charCount');
    const messagePreview = document.getElementById('messagePreview');
    const broadcastForm = document.getElementById('broadcastForm');
    const sendButton = document.getElementById('sendButton');
    const resultDisplay = document.getElementById('resultDisplay');

    if (!messageTextarea || !broadcastForm) {
        console.log('Form elements not found');
        return;
    }

    // Character counter
    messageTextarea.addEventListener('input', function() {
        const length = this.value.length;
        charCount.textContent = length;
        
        // Change color based on usage
        if (length > 3500) {
            charCount.style.color = '#dc3545';
        } else if (length > 3000) {
            charCount.style.color = '#fd7e14';
        } else {
            charCount.style.color = '#6c757d';
        }
        
        // Update preview
        updatePreview();
    });

    function updatePreview() {
        const text = messageTextarea.value.trim();
        if (text) {
            // Simple HTML rendering (be careful with user input in real apps)
            messagePreview.innerHTML = text.replace(/\n/g, '<br>');
        } else {
            messagePreview.innerHTML = '<em class="text-muted">Xabar matni avtomatik ko\'rsatiladi...</em>';
        }
    }

    // Form submission
    broadcastForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const messageText = messageTextarea.value.trim();
        
        if (!messageText) {
            showAlert('Xabar matnini kiriting', 'danger');
            return;
        }
        
        // Confirm before sending
        const conversationsCount = document.querySelector('.stat-content h3').textContent;
        if (!confirm(`Rostdan ham ${conversationsCount} ta mijozga xabar yubormoqchimisiz?`)) {
            return;
        }
        
        console.log('Starting broadcast submission');
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Yuborilmoqda...';
        
        const formData = new FormData(this);
        
        fetch(window.location.href, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data);
            showResult(data);
            
            if (data.success) {
                // Clear form on success
                messageTextarea.value = '';
                updatePreview();
                charCount.textContent = '0';
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            showAlert('Tarmoq xatoligi yuz berdi', 'danger');
        })
        .finally(() => {
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-broadcast-tower me-2"></i>Barcha Mijozlarga Xabar Yuborish';
        });
    });

    function showResult(data) {
        const isSuccess = data.success;
        const alertClass = isSuccess ? 'alert-success' : 'alert-danger';
        const iconClass = isSuccess ? 'fa-check-circle' : 'fa-exclamation-triangle';
        
        let html = `
            <div class="alert ${alertClass} alert-dismissible fade show">
                <i class="fas ${iconClass} me-2"></i>
                <strong>${isSuccess ? 'Muvaffaqiyat!' : 'Xatolik!'}</strong>
                <div class="mt-2">${data.message || data.error}</div>
        `;
        
        // Add statistics if available
        if (data.stats) {
            html += `
                <div class="result-stats mt-3 pt-3 border-top">
                    <div class="result-stat">
                        <div class="number text-success">${data.stats.successful}</div>
                        <div class="label">Muvaffaqiyatli</div>
                    </div>
                    <div class="result-stat">
                        <div class="number text-danger">${data.stats.failed}</div>
                        <div class="label">Xatolik</div>
                    </div>
                    <div class="result-stat">
                        <div class="number text-primary">${data.stats.total}</div>
                        <div class="label">Jami</div>
                    </div>
                </div>
            `;
        }
        
        html += `
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        resultDisplay.innerHTML = html;
        resultDisplay.style.display = 'block';
        
        // Scroll to result
        resultDisplay.scrollIntoView({ behavior: 'smooth' });
    }

    function showAlert(message, type) {
        const alertClass = `alert-${type}`;
        const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle';
        
        const alert = document.createElement('div');
        alert.className = `alert ${alertClass} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="fas ${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of card body
        const cardBody = document.querySelector('.card-body');
        cardBody.insertBefore(alert, cardBody.firstChild);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    // Initialize preview
    updatePreview();
});