class ChatBot {
    constructor() {
        this.isOpen = false;
        this.isTyping = false;
        this.messageCount = 0;
        this.apiKey = 'nawabkhan';
        this.baseUrl = `${window.location.protocol}//${window.location.hostname}`;
        this.sessionId = this.generateSessionId();
        this.awaitingPhone = false;
        this.awaitingOTP = false;
        this.lastUserMessage = '';
        this.phoneNumber = '';

        this.initializeElements();
        this.bindEvents();
        this.showWelcomeMessage();
    }

    generateSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    initializeElements() {
        this.chatToggle = document.getElementById('chatToggle');
        this.chatContainer = document.getElementById('chatContainer');
        this.chatOverlay = document.getElementById('chatOverlay');
        this.minimizeChat = document.getElementById('minimizeChat');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.notificationBadge = document.getElementById('notificationBadge');
        this.quickActionBtns = document.querySelectorAll('.quick-action-btn');
        this.quickActionsContainer = document.getElementById('quickActions');
    }

    bindEvents() {
        this.chatToggle.addEventListener('click', () => this.toggleChat());
        this.minimizeChat.addEventListener('click', () => this.closeChat());
        this.chatOverlay.addEventListener('click', () => this.closeChat());

        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.sendBtn.addEventListener('click', () => this.sendMessage());

        this.quickActionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const category = btn.dataset.category;
                this.handleQuickAction(category);
            });
        });

        this.messageInput.addEventListener('input', () => this.autoResizeInput());

        this.chatContainer.addEventListener('click', (e) => e.stopPropagation());
    }

    toggleChat() {
        this.isOpen ? this.closeChat() : this.openChat();
    }

    openChat() {
        this.isOpen = true;
        this.chatContainer.classList.add('active');
        this.chatOverlay.classList.add('active');
        this.chatToggle.classList.add('active');
        this.hideNotificationBadge();
        this.messageInput.focus();
        document.body.style.overflow = 'hidden';
    }

    closeChat() {
        this.isOpen = false;
        this.chatContainer.classList.remove('active');
        this.chatOverlay.classList.remove('active');
        this.chatToggle.classList.remove('active');
        document.body.style.overflow = '';
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        this.hideQuickActions();
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.autoResizeInput();

        this.showTypingIndicator();

        if (this.awaitingPhone) {
            this.awaitingPhone = false;
            this.phoneNumber = message;
            this.sendOTP(message);
            return;
        }

        if (this.awaitingOTP) {
            this.awaitingOTP = false;
            this.verifyOTP(this.phoneNumber, message);
            return;
        }

        this.lastUserMessage = message;
        this.generateBotResponse(message);
    }

    hideQuickActions() {
        if (this.quickActionsContainer) {
            this.quickActionsContainer.style.display = 'none';
        }
    }

    addMessage(content, sender = 'bot', timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message fade-in`;

        const time = timestamp || this.getCurrentTime();
        const avatarIcon = sender === 'bot' ? 'fas fa-robot' : 'fas fa-user';

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    <p class="mb-0">${content}</p>
                </div>
                <small class="message-time">${time}</small>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        this.messageCount++;
    }
    addProductCard(product) {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'product-card fade-in';
        
        // Map the correct field names from backend
        const safeName = product.product_name || product.name || 'Product';
        const words = safeName.split(' ');
        const productName = words.length > 8 ? words.slice(0, 8).join(' ') + '...' : safeName;
        
        // Use product_image field from backend
        const imageUrl = product.product_image || product.image || product.first_image || '';
        
        // Use product_mrp field from backend
        const price = product.product_mrp || product.price || 'Price not available';
        
        // Use product_url field from backend
        const productLink = product.product_url || product.link || '#';

        cardDiv.innerHTML = `
            <div class="card mb-2 shadow-sm border">
                <div class="row g-0">
                    <div class="col-4 product-image">
                        <img src="${imageUrl}" alt="${safeName}" class="img-fluid rounded-start" onerror="this.style.display='none'" />
                    </div>
                    <div class="col-8">
                        <div class="card-body p-2">
                            <p class="card-title mb-1" style="font-size: 0.9rem; font-weight: 600;">${productName}</p>
                            <p class="card-text mb-1 fw-bold text-success">${price}</p>
                            ${product.features?.length
                ? `<ul class="product-features mb-2" style="font-size: 0.8rem; margin: 0; padding-left: 1rem;">${product.features.slice(0, 3).map(f => `<li style="margin-bottom: 2px;">${f}</li>`).join('')}</ul>`
                : ''
            }
            <a href="${productLink}" target="_blank" class="btn btn-sm btn-outline-primary">View Product</a>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.chatMessages.appendChild(cardDiv);
        this.scrollToBottom();
    }

    addProductDetailsCard(productDetails) {
        // Check if productDetails has meaningful content
        if (!productDetails || Object.keys(productDetails).length === 0) {
            return; // Don't show card for empty object
        }
        
        // Check if it has essential product information
        if (!productDetails.product_name && !productDetails.product_id) {
            return; // Don't show card without basic product info
        }
        
        const cardDiv = document.createElement('div');
        cardDiv.className = 'product-details-card fade-in';
        
        const product = productDetails;
        const productName = product.product_name || 'Product Details';
        const price = product.product_mrp || 'Price not available';
        const imageUrl = product.product_image || '';
        const inStock = product.instock || 'Unknown';
        const description = product.meta_desc || '';
        
        // Handle specifications - show top 5 specs and prioritize warranty
        let specificationsHtml = '';
        if (product.product_specification && Array.isArray(product.product_specification)) {
            let specs = [...product.product_specification];
            
            // Look for warranty in specs and prioritize it
            const warrantyIndex = specs.findIndex(spec => 
                spec.fkey && spec.fkey.toLowerCase().includes('warranty')
            );
            
            if (warrantyIndex !== -1) {
                // Move warranty to the front
                const warranty = specs.splice(warrantyIndex, 1)[0];
                specs.unshift(warranty);
            }
            
            // Take only top 5 specifications
            const topSpecs = specs.slice(0, 5);
            
            specificationsHtml = `
                <div class="specifications mb-3">
                    <h6 class="text-primary mb-2">
                        <i class="fas fa-list-check me-1"></i>Key Specifications
                    </h6>
                    <div class="row">
                        ${topSpecs.map(spec => `
                            <div class="col-12 mb-1">
                                <small class="text-muted">${spec.fkey}:</small>
                                <span class="fw-bold ms-1">${spec.fvalue}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        // Handle delivery options
        let deliveryHtml = '';
        if (product.del) {
            deliveryHtml = `
                <div class="delivery-options mb-3">
                    <h6 class="text-success mb-2">
                        <i class="fas fa-truck me-1"></i>Delivery Options
                    </h6>
                    ${product.del.std ? `<p class="mb-1"><i class="fas fa-box me-1 text-info"></i><small>${product.del.std}</small></p>` : ''}
                    ${product.del.t3h ? `<p class="mb-1"><i class="fas fa-bolt me-1 text-warning"></i><small>${product.del.t3h}</small></p>` : ''}
                    ${product.del.stp ? `<p class="mb-1"><i class="fas fa-store me-1 text-primary"></i><small>${product.del.stp}</small></p>` : ''}
                </div>
            `;
        }

        cardDiv.innerHTML = `
            <div class="card mb-3 shadow border product-detail-card">
                <div class="card-header bg-primary text-white py-2">
                    <h6 class="mb-0">
                        <i class="fas fa-info-circle me-2"></i>Product Details
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4 text-center mb-3">
                            <img src="${imageUrl}" alt="${productName}" class="img-fluid rounded shadow-sm" style="max-height: 200px;" onerror="this.style.display='none'" />
                            <div class="mt-2">
                                <span class="badge ${inStock.toLowerCase() === 'yes' ? 'bg-success' : 'bg-warning'} px-3">
                                    <i class="fas fa-${inStock.toLowerCase() === 'yes' ? 'check' : 'clock'} me-1"></i>
                                    ${inStock.toLowerCase() === 'yes' ? 'In Stock' : 'Check Availability'}
                                </span>
                            </div>
                        </div>
                        <div class="col-md-8">
                            <h5 class="card-title text-dark mb-2">${productName}</h5>
                            <h4 class="text-success fw-bold mb-3">₹${price}</h4>
                        </div>
                        <div>
                        ${specificationsHtml}
                        ${deliveryHtml}
                        ${description ? `
                                <div class="description mb-3">
                                    <h6 class="text-secondary mb-2">
                                        <i class="fas fa-file-alt me-1"></i>Description
                                    </h6>
                                    <p class="text-muted small">${description.length > 150 ? description.substring(0, 150) + '...' : description}</p>
                                </div>
                            ` : ''}
                            
                            <div class="action-buttons">
                                <button class="btn btn-primary me-2" onclick="window.open('https://www.lotuselectronics.com/product/${product.uri_slug || ''}/${product.product_id || ''}', '_blank')">
                                    <i class="fas fa-shopping-cart me-1"></i>Buy Now
                                </button>
                                <button class="btn btn-outline-success" onclick="window.open('tel:0731-4265577', '_self')">
                                    <i class="fas fa-phone me-1"></i>Call for Details
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.chatMessages.appendChild(cardDiv);
        this.scrollToBottom();
    }

    addStoreCard(store) {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'store-card fade-in';
        
        // Map the correct field names from backend
        const storeName = store.store_name || store.name || 'Store';
        const address = store.address || 'Address not available';
        const city = store.city || '';
        const state = store.state || '';
        const zipcode = store.zipcode || '';
        const timing = store.timings || store.timing || 'Timing not available'; // Check both timings and timing
        const phone = store.phone || '0731-4265577'; // Default phone number
        
        // Format full address
        const fullAddress = `${address}${city ? ', ' + city : ''}${zipcode ? ' - ' + zipcode : ''}${state ? ', ' + state : ''}`;

        cardDiv.innerHTML = `
            <div class="card mb-2 shadow-sm border">
                <div class="row g-0">
                    <div class="col-2 d-flex align-items-center justify-content-center bg-light">
                        <i class="fas fa-store text-primary" style="font-size: 1.5rem;"></i>
                    </div>
                    <div class="col-10">
                        <div class="card-body p-3">
                            <h6 class="card-title mb-2 text-primary">
                                <i class="fas fa-map-marker-alt me-1"></i>
                                ${storeName}
                            </h6>
                            <p class="card-text mb-2" style="font-size: 0.9rem;">
                                <i class="fas fa-location-dot me-1 text-muted"></i>
                                ${fullAddress}
                            </p>
                            <p class="card-text mb-2" style="font-size: 0.9rem;">
                                <i class="fas fa-clock me-1 text-success"></i>
                                <span class="text-success fw-bold">${timing}</span>
                            </p>
                            <div class="d-flex gap-2">
                                <button class="btn btn-sm btn-outline-primary" onclick="window.open('https://maps.google.com/?q=${encodeURIComponent(storeName + ' ' + fullAddress)}', '_blank')">
                                    <i class="fas fa-directions me-1"></i>Get Directions
                                </button>
                                <button class="btn btn-sm btn-outline-success" onclick="window.open('tel:${phone}', '_self')">
                                    <i class="fas fa-phone me-1"></i>Call Store
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.chatMessages.appendChild(cardDiv);
        this.scrollToBottom();
    }

    addPolicyInfoCard(policyInfo) {
        if (!policyInfo.policy_sections || !Array.isArray(policyInfo.policy_sections)) {
            return;
        }

        const cardDiv = document.createElement('div');
        cardDiv.className = 'policy-card fade-in';
        
        let policySectionsHtml = '';
        policyInfo.policy_sections.forEach((section, index) => {
            const relevanceColor = section.relevance_score >= 0.9 ? 'text-success' : 
                                  section.relevance_score >= 0.8 ? 'text-warning' : 'text-info';
            
            policySectionsHtml += `
                <div class="policy-section mb-3 ${index > 0 ? 'border-top pt-3' : ''}">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="badge bg-secondary">${section.document || 'Policy'}</span>
                        <small class="${relevanceColor}">
                            <i class="fas fa-star me-1"></i>
                            ${Math.round(section.relevance_score * 100)}% relevant
                        </small>
                    </div>
                    <div class="policy-content" style="font-size: 0.9rem; line-height: 1.5;">
                        ${section.content.replace(/\n/g, '<br>')}
                    </div>
                </div>
            `;
        });

        cardDiv.innerHTML = `
            <div class="card mb-2 shadow-sm border-info">
                <div class="row g-0">
                    <div class="col-2 d-flex align-items-center justify-content-center bg-light">
                        <i class="fas fa-shield-alt text-info" style="font-size: 1.5rem;"></i>
                    </div>
                    <div class="col-10">
                        <div class="card-body p-3">
                            <h6 class="card-title mb-3 text-info">
                                <i class="fas fa-file-contract me-1"></i>
                                Policy Information
                                <small class="text-muted">(${policyInfo.total_found || 0} section${policyInfo.total_found !== 1 ? 's' : ''} found)</small>
                            </h6>
                            ${policySectionsHtml}
                            <div class="mt-3 p-2 bg-light rounded">
                                <small class="text-muted">
                                    <i class="fas fa-info-circle me-1"></i>
                                    For complete terms and conditions, please visit our official website or contact customer service.
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.chatMessages.appendChild(cardDiv);
        this.scrollToBottom();
    }

    // addProductCard(product) {
    //     const card = document.createElement('div');
    //     card.className = 'product-card fade-in';

    //     card.innerHTML = `
    //     <a href="${product.link}" target="_blank" class="product-link">
    //         <div class="product-image">
    //             <img src="${product.image}" alt="${product.name}">
    //         </div>
    //         <div class="product-details">
    //             <h6 class="product-name">${product.name}</h6>
    //             <p class="product-price">ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹${product.price}</p>
    //             ${product.features?.length
    //             ? `<ul class="product-features">${product.features.map(f => `<li>${f}</li>`).join('')}</ul>`
    //             : ''
    //         }
    //         </div>
    //     </a>
    // `;

    //     this.chatMessages.appendChild(card);
    //     this.scrollToBottom();
    // }


    processStructuredResponse(responseData) {
        let answer = responseData.answer;
        const products = responseData.products;
        const productDetails = responseData.product_details;
        const stores = responseData.stores;
        const policyInfo = responseData.policy_info;
        const comparison = responseData.comparison;
        const end = responseData.end;

        // If stores are present, clean up the answer to avoid duplication
        if (stores && Array.isArray(stores) && stores.length > 0) {
            // Remove store listing from answer text but keep the intro
            const lines = answer.split('\n');
            const cleanedLines = [];
            let skipMode = false;
            
            for (let line of lines) {
                // Skip lines that contain store details (bullets, addresses, timings)
                if (line.includes('*') || line.includes('📍') || line.includes('🕒') || 
                    line.includes('Store at') || line.includes('AM') || line.includes('PM')) {
                    skipMode = true;
                    continue;
                }
                
                // Keep intro lines and question at the end
                if (!skipMode || line.trim() === '' || line.includes('?') || 
                    line.includes('specific area') || line.includes('looking for')) {
                    cleanedLines.push(line);
                    skipMode = false;
                }
            }
            
            answer = cleanedLines.join('\n').trim();
            
            // If answer becomes too short, provide a generic intro
            if (answer.length < 20) {
                answer = `Great! Here are ${stores.length} Lotus Electronics stores found:`;
            }
        }

        if (answer) this.addMessage(answer, 'bot');
        if (products && Array.isArray(products)) {
            products.forEach(product => this.addProductCard(product));
        }
        if (productDetails && Array.isArray(productDetails)) {
            productDetails.forEach(details => this.addProductDetailsCard(details));
        } else if (productDetails && typeof productDetails === 'object' && Object.keys(productDetails).length > 0) {
            // Handle single product detail object - only if it has content
            this.addProductDetailsCard(productDetails);
        }
        if (stores && Array.isArray(stores)) {
            stores.forEach(store => this.addStoreCard(store));
        }
        
        // Handle policy info with better debugging and nested structure support
        if (policyInfo && typeof policyInfo === 'object') {
            console.log('🔍 Policy info received:', policyInfo);
            
            // Check for nested structure first
            if (policyInfo.search_terms_conditions_response && policyInfo.search_terms_conditions_response.success) {
                console.log('📋 Using nested policy structure');
                this.addPolicyInfoCard(policyInfo.search_terms_conditions_response);
            } else if (policyInfo.success) {
                console.log('📋 Using direct policy structure');
                this.addPolicyInfoCard(policyInfo);
            } else {
                console.log('⚠️ Policy info present but no success field found');
            }
        }
        if (comparison && Array.isArray(comparison)) {
            comparison.forEach(item => {
                let compMsg = `
                <div class="max-w-xl mx-auto p-2">
                  <div class="bg-white shadow rounded-xl p-4 border border-gray-200">
                    <div class="font-bold mb-2 text-gray-800">
                      Comparison: <span class="text-blue-700">${item.name}</span> <span class="text-gray-500">vs</span> <span class="text-green-700">${item.vs_name}</span>
                    </div>
                    <ul class="text-sm text-gray-700 list-disc ml-5 space-y-1 mb-2">
                      ${item.differences.map(diff => `<li>${diff}</li>`).join('')}
                    </ul>
                    <div class="text-xs text-gray-500 mt-2"><em>Would you like to purchase one or need further details?</em></div>
                  </div>
                </div>
                `;
                this.addMessage(compMsg, 'bot');
            });
        }
        if (end) this.addMessage(end, 'bot');
    }

    generateBotResponse(userMessage, retryCount = 0) {
        this.showTypingIndicator();

        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': this.apiKey,
                'Accept': 'application/json'
            },
            mode: 'cors',
            body: JSON.stringify({
                message: userMessage,
                session_id: this.sessionId
            })
        };

        fetch(`${this.baseUrl}/chat`, requestOptions)
            .then(async response => {
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    const statusMessage = {
                        429: 'Too many requests - please wait before trying again',
                        500: 'Server is experiencing high traffic - please try again shortly',
                        502: 'Server temporarily unavailable',
                        503: 'Service temporarily unavailable',
                        504: 'Request timed out - please try again'
                    }[response.status] || `Server error (${response.status})`;
                    
                    throw new Error(errorData.detail || statusMessage);
                }
                return response.json();
            })
            .then(data => {
                this.hideTypingIndicator();
                
                console.log("Response received:", data); // Debug logging

                // Handle the new JSON response format
                if (data.response) {
                    // If response is wrapped, unwrap it
                    if (typeof data.response === 'string') {
                        try {
                            data = JSON.parse(data.response);
                        } catch (e) {
                            console.log("Failed to parse response string:", e);
                            data = { answer: data.response };
                        }
                    } else {
                        data = data.response;
                    }
                }

                // Check for structured response format
                if (data.status === "success" || (data.status === "partial" && data.data)) {
                    this.processStructuredResponse(data.data);
                } else if (data.answer !== undefined) {
                    // Direct response format (answer, products, stores, etc. at top level)
                    this.processStructuredResponse(data);
                } else if (data.status === "error" && data.data) {
                    this.addMessage(data.data.answer || "Sorry, something went wrong.", 'bot');
                } else if (data.status === "error" && data.data) {
                    this.addMessage(data.data.answer || "Sorry, something went wrong.", 'bot');
                } else {
                    // Handle different response formats
                    console.log("Unexpected response format:", data);
                    
                    // Check if it's a simple string response
                    if (typeof data === 'string') {
                        this.addMessage(data, 'bot');
                    } else if (data.response) {
                        this.addMessage(data.response, 'bot');
                    } else if (data.answer) {
                        this.addMessage(data.answer, 'bot');
                    } else if (data.message) {
                        this.addMessage(data.message, 'bot');
                    } else {
                        // Provide contextual response based on user message
                        const userMsg = userMessage.toLowerCase();
                        let responseMsg = "I'm here to help! How can I assist you with Lotus Electronics products today?";
                        
                        if (userMsg.includes('hello') || userMsg.includes('hi') || userMsg.includes('hey')) {
                            responseMsg = "Hello! Welcome to Lotus Electronics! I'm here to help you find the perfect electronics products. What are you looking for today?";
                        } else if (userMsg.includes('help')) {
                            responseMsg = "I'd be happy to help! I can assist you with:\n• Finding products (TVs, smartphones, laptops, etc.)\n• Getting detailed product specifications\n• Locating nearby Lotus stores\n• Checking product availability\n\nWhat would you like to explore?";
                        } else if (userMsg.includes('thanks') || userMsg.includes('thank you')) {
                            responseMsg = "You're welcome! Is there anything else I can help you find in our electronics collection?";
                        }
                        
                        this.addMessage(responseMsg, 'bot');
                    }
                }
            })
            .catch(error => {
                console.error("API error:", error);
                this.hideTypingIndicator();
                
                // Check if this is a retryable error and we haven't exceeded retry limit
                const isRetryableError = error.message.includes('500') || 
                                       error.message.includes('502') || 
                                       error.message.includes('503') || 
                                       error.message.includes('504') ||
                                       error.message.includes('timeout') ||
                                       error.message.includes('Network');
                
                if (isRetryableError && retryCount < 2) {
                    // Show retry message and attempt again after delay
                    this.addMessage("Connection issue detected. Retrying in a moment...", 'bot');
                    setTimeout(() => {
                        this.generateBotResponse(userMessage, retryCount + 1);
                    }, (retryCount + 1) * 2000); // Exponential backoff: 2s, 4s
                    return;
                }
                
                // Provide specific error messages
                let errorMessage = "I apologize, but I'm having trouble. Please try again.";
                
                if (error.message.includes('500')) {
                    errorMessage = "I'm experiencing high traffic right now. Please wait a moment and try again.";
                } else if (error.message.includes('429')) {
                    errorMessage = "Too many requests. Please wait a few seconds before trying again.";
                } else if (error.message.includes('503') || error.message.includes('502')) {
                    errorMessage = "Service temporarily unavailable. Please try again in a moment.";
                } else if (error.message.includes('Network') || error.message.includes('timeout')) {
                    errorMessage = "Network connection issue. Please check your internet and try again.";
                }
                
                this.addMessage(errorMessage, 'bot');
            });
    }

    promptForPhone() {
        this.messageInput.placeholder = 'Enter your phone number...';
        this.messageInput.type = 'tel';
        this.awaitingPhone = true;
    }

    promptForOTP() {
        this.messageInput.placeholder = 'Enter the OTP sent to your phone...';
        this.messageInput.type = 'text';
        this.awaitingOTP = true;
    }

    sendOTP(phone) {
        // First check if user exists
        const formData = new URLSearchParams();
        formData.append('phone', phone);
        fetch(`${this.baseUrl}/auth/check-user`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            // Check if user exists (assume error==0 means exists, or adapt to your API)
            if (data.error && data.error !== "0") {
                this.hideTypingIndicator();
                this.addMessage("This phone number is not registered. Please enter a valid registered phone number.", 'bot');
                this.promptForPhone();
                throw new Error('User not found');
            }
            // Now send the OTP
            const otpFormData = new URLSearchParams();
            otpFormData.append('phone', phone);
            return fetch(`${this.baseUrl}/auth/send-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: otpFormData
            });
        })
        .then(res => res.json())
        .then(data => {
            this.hideTypingIndicator();
            this.addMessage("I've sent an OTP to your phone. Please enter it to continue.", 'bot');
            this.promptForOTP();
        })
        .catch((err) => {
            if (err.message !== 'User not found') {
                this.hideTypingIndicator();
                this.addMessage("Failed to send OTP. Please check your phone number and try again.", 'bot');
                this.promptForPhone();
            }
        });
    }

    verifyOTP(phone, otp) {
        const formData = new URLSearchParams();
        formData.append('phone', phone);
        formData.append('otp', otp);
        formData.append('session_id', this.sessionId);
        fetch(`${this.baseUrl}/auth/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        })
        .then(res => {
            if (!res.ok) throw new Error('Invalid OTP');
            return res.json();
        })
        .then(data => {
            this.hideTypingIndicator();
            this.addMessage("Thank you! You're now logged in. How can I assist you further?", 'bot');
            // Resume the original intent
            if (this.lastUserMessage) {
                setTimeout(() => {
                    this.generateBotResponse(this.lastUserMessage);
                }, 500);
            }
        })
        .catch(() => {
            this.hideTypingIndicator();
            this.addMessage("Invalid OTP. Please try again.", 'bot');
            this.promptForOTP();
        });
    }

    handleQuickAction(category) {
        this.hideQuickActions();
        const categoryMessages = {
            television: "I'm interested in LED TVs. Can you show me your best deals?",
            smartphone: "I'm looking for smartphones. What are your latest models?",
            laptop: "I need a laptop. Can you help me choose the right one?",
            homeappliance: "I'm interested in home appliances. What brands and models do you have?",
            kitchenappliance: "I'm looking for kitchen appliances. What options are available?",
            ac: "I need an air conditioner. Can you show me your AC collection?",
            storelocator: "I want to find a Lotus Electronics store near me. Can you help?"
        };

        const message = categoryMessages[category] || `I'm interested in ${category} products.`;
        this.addMessage(message, 'user');
        this.generateBotResponse(message);
    }

    showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.classList.add('active');
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('active');
    }

    showWelcomeMessage() {
        setTimeout(() => {
            this.showNotificationBadge();
        }, 2000);
    }

    showNotificationBadge() {
        this.notificationBadge.style.display = 'flex';
        this.notificationBadge.textContent = '1';
    }

    hideNotificationBadge() {
        this.notificationBadge.style.display = 'none';
    }

    autoResizeInput() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // External API methods
    addExternalMessage(message, sender = 'bot') {
        this.addMessage(message, sender);
        if (!this.isOpen) {
            this.showNotificationBadge();
        }
    }

    openChatWithMessage(message) {
        this.openChat();
        setTimeout(() => {
            this.addMessage(message, 'bot');
        }, 500);
    }
}

// Initialize chatbot
document.addEventListener('DOMContentLoaded', () => {
    window.chatBot = new ChatBot();
    window.chatBot.openChat();
});

// External API
window.ChatBotAPI = {
    sendMessage: (message, sender = 'bot') => {
        if (window.chatBot) {
            window.chatBot.addExternalMessage(message, sender);
        }
    },
    openChat: () => {
        if (window.chatBot) {
            window.chatBot.openChat();
        }
    },
    closeChat: () => {
        if (window.chatBot) {
            window.chatBot.closeChat();
        }
    },
    openWithMessage: (message) => {
        if (window.chatBot) {
            window.chatBot.openChatWithMessage(message);
        }
    }
};