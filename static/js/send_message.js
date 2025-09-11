// Send Message Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Send Message Page');
    const conversationItems = document.querySelectorAll('.conversation-item');
    console.log('Found conversation items:', conversationItems.length);
    const selectedUser = document.getElementById('selectedUser');
    const messageText = document.getElementById('messageText');
    const sendButton = document.getElementById('sendButton');
    const conversationId = document.getElementById('conversationId');
    const platform = document.getElementById('platform');
    const platformUserId = document.getElementById('platformUserId');
    const recentMessages = document.getElementById('recentMessages');

    conversationItems.forEach((item, index) => {
        console.log(`Adding click listener to item ${index}:`, item);
        console.log('Item data attributes:', {
            conversationId: item.dataset.conversationId,
            platform: item.dataset.platform,
            userId: item.dataset.userId,
            username: item.dataset.username
        });
        item.addEventListener('click', function() {
            console.log('Conversation item clicked!', this);
            // Remove active class from all items
            conversationItems.forEach(i => i.classList.remove('active'));
            // Add active class to clicked item
            this.classList.add('active');

            // Get conversation data
            const convId = this.dataset.conversationId;
            const platformType = this.dataset.platform;
            const userId = this.dataset.userId; // data-user-id
            const username = this.dataset.username;

            // Update form fields
            conversationId.value = convId;
            platform.value = platformType;
            platformUserId.value = userId;

            // Update selected user display
            selectedUser.innerHTML = `
                <i class="fab fa-${platformType} me-1"></i>
                <strong>@${username}</strong> (${platformType.toUpperCase()})
                <br><small class="text-muted">ID: ${userId}</small>
            `;
            selectedUser.className = 'alert alert-info';

            // Enable form elements
            messageText.disabled = false;
            sendButton.disabled = false;

            // Load recent messages
            loadRecentMessages(convId);
        });
    });

    function loadRecentMessages(convId) {
        recentMessages.innerHTML = '<p class="text-muted">Yuklanmoqda...</p>';
        
        fetch(`/conversation/${convId}/messages`)
            .then(response => response.json())
            .then(data => {
                if (data.messages && data.messages.length > 0) {
                    const messagesHtml = data.messages.slice(-5).map(msg => `
                        <div class="border-bottom pb-2 mb-2">
                            <div class="d-flex justify-content-between">
                                <strong class="small">${msg.is_from_user ? 'Mijoz' : 'Bot'}</strong>
                                <small class="text-muted">${new Date(msg.created_at).toLocaleString('uz-UZ')}</small>
                            </div>
                            <p class="small mb-0">${msg.content}</p>
                        </div>
                    `).join('');
                    recentMessages.innerHTML = messagesHtml;
                } else {
                    recentMessages.innerHTML = '<p class="text-muted">Xabarlar yo\'q</p>';
                }
            })
            .catch(error => {
                recentMessages.innerHTML = '<p class="text-danger">Xabarlarni yuklab bo\'lmadi</p>';
            });
    }

    // Form submission
    document.getElementById('messageForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        console.log('Form submission started');
        console.log('Conversation ID:', conversationId.value);
        console.log('Platform:', platform.value);
        console.log('Platform User ID:', platformUserId.value);
        console.log('Message:', messageText.value);
        
        const formData = new FormData(this);
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Yuborilmoqda...';

        console.log('Sending POST request to:', window.location.href);
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
            if (data.success) {
                // Clear form
                messageText.value = '';
                // Show success message
                showMessage('Xabar muvaffaqiyatli yuborildi!', 'success');
                // Reload recent messages
                if (conversationId.value) {
                    loadRecentMessages(conversationId.value);
                }
            } else {
                showMessage(data.error || 'Xabar yuborishda xatolik yuz berdi', 'error');
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            showMessage('Tarmoq xatoligi', 'error');
        })
        .finally(() => {
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane me-1"></i>Xabar Yuborish';
        });
    });

    function showMessage(text, type) {
        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle';
        
        const alert = document.createElement('div');
        alert.className = `alert ${alertClass} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="fas ${iconClass} me-1"></i>
            ${text}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.position-fixed') || document.body;
        container.appendChild(alert);
        
        setTimeout(() => alert.remove(), 5000);
    }
});