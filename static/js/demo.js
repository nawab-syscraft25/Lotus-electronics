const landingPage = document.getElementById('landingPage');
const chatOverlay = document.getElementById('chatOverlay');
const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatMessages = document.getElementById('chatMessages');
const typingIndicator = document.getElementById('typingIndicator');
const closeChatBtn = document.getElementById('closeChat');


// Polyfill for UUID v4 if crypto.randomUUID is not available
function generateUUIDv4() {
    if (window.crypto && window.crypto.randomUUID) {
        return window.crypto.randomUUID();
    }
    // fallback
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

let sessionId = generateUUIDv4(); // generate a session id once per page load

// Chat persistence functions
function saveChatToStorage() {
    try {
        // Save the entire chat messages container HTML to preserve all content
        const chatContent = chatMessages.innerHTML;
        
        // Also save individual messages for backward compatibility and easier processing
        const messages = [];
        const messageElements = chatMessages.querySelectorAll('.message');
        
        messageElements.forEach(messageEl => {
            const isUser = messageEl.classList.contains('user');
            const content = messageEl.querySelector('.message-content').innerHTML;
            const time = messageEl.querySelector('.message-time').textContent;
            
            messages.push({
                content: content,
                isUser: isUser,
                time: time
            });
        });
        
        // Save both the complete HTML and individual messages
        localStorage.setItem('lotus-chat-content', chatContent);
        localStorage.setItem('lotus-chat-history', JSON.stringify(messages));
        localStorage.setItem('lotus-chat-session', sessionId);
        console.log('💾 Chat saved to storage:', messages.length, 'messages + complete HTML content');
    } catch (error) {
        console.error('❌ Error saving chat to storage:', error);
    }
}

function loadChatFromStorage() {
    try {
        const savedContent = localStorage.getItem('lotus-chat-content');
        const savedSession = localStorage.getItem('lotus-chat-session');
        
        if (savedContent && savedSession) {
            sessionId = savedSession; // Restore the session ID
            
            // Restore the complete HTML content
            chatMessages.innerHTML = savedContent;
            
            // Re-attach event listeners for any interactive elements that might have been restored
            reattachEventListeners();
            
            scrollToBottom();
            console.log('📥 Chat restored from storage with complete HTML content');
            return true; // Indicate that chat was restored
        }
        
        // Fallback to old method if new content storage is not available
        const savedMessages = localStorage.getItem('lotus-chat-history');
        if (savedMessages && savedSession) {
            const messages = JSON.parse(savedMessages);
            sessionId = savedSession;
            
            // Clear current chat
            chatMessages.innerHTML = '';
            
            // Restore messages using old method
            messages.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${msg.isUser ? 'user' : 'bot'}`;
                
                messageDiv.innerHTML = `
                    <div class="message-content">
                        ${msg.content}
                    </div>
                    <div class="message-time">
                        ${msg.time}
                    </div>
                `;
                
                chatMessages.appendChild(messageDiv);
            });
            
            if (messages.length > 0) {
                scrollToBottom();
                console.log('📥 Chat restored from storage (legacy method):', messages.length, 'messages');
                return true;
            }
        }
        
        return false; // No chat to restore
    } catch (error) {
        console.error('❌ Error loading chat from storage:', error);
        return false;
    }
}

// Function to reattach event listeners to restored content
function reattachEventListeners() {
    try {
        // Reattach carousel navigation events
        const carouselPrevBtns = chatMessages.querySelectorAll('.prev-btn');
        const carouselNextBtns = chatMessages.querySelectorAll('.next-btn');
        
        carouselPrevBtns.forEach(btn => {
            const carousel = btn.parentElement.querySelector('.carousel-container');
            if (carousel) {
                btn.onclick = () => {
                    carousel.scrollBy({ left: -carousel.offsetWidth, behavior: 'smooth' });
                };
            }
        });
        
        carouselNextBtns.forEach(btn => {
            const carousel = btn.parentElement.querySelector('.carousel-container');
            if (carousel) {
                btn.onclick = () => {
                    carousel.scrollBy({ left: carousel.offsetWidth, behavior: 'smooth' });
                };
            }
        });
        
        // Reattach any other interactive elements as needed
        console.log('🔗 Event listeners reattached to restored content');
    } catch (error) {
        console.error('❌ Error reattaching event listeners:', error);
    }
}

function clearChatStorage() {
    try {
        localStorage.removeItem('lotus-chat-content');
        localStorage.removeItem('lotus-chat-history');
        localStorage.removeItem('lotus-chat-session');
        console.log('🗑️ Chat storage cleared');
    } catch (error) {
        console.error('❌ Error clearing chat storage:', error);
    }
}

function getCurrentTime() {
    return new Date().toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function addMessage(content, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;

    messageDiv.innerHTML = `
        <div class="message-content">
            ${content}
        </div>
        <div class="message-time">
            ${getCurrentTime()}
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    
    // Auto-save chat after adding new message
    saveChatToStorage();
}

function showTypingIndicator() {
    typingIndicator.style.display = 'block';
    scrollToBottom();
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function openChat(initialMessage = null) {
    landingPage.style.display = 'none';
    chatOverlay.style.display = 'flex';

    if (initialMessage) {
        addMessage(initialMessage, true);
        sendToBot(initialMessage);
    }

    chatInput.focus();
}

function closeChat() {
    chatOverlay.style.display = 'none';
    landingPage.style.display = 'flex';
    chatMessages.innerHTML = '';
    searchInput.focus();
    sessionId = generateUUIDv4(); // reset session when closing
    clearChatStorage(); // Clear stored chat history when chat is closed
}

function newChat() {
    // Clear current chat messages
    chatMessages.innerHTML = '';
    
    // Generate new session ID
    sessionId = generateUUIDv4();
    
    // Clear chat storage
    clearChatStorage();
    
    // Focus on chat input to start new conversation
    chatInput.focus();
    
    // Add a welcome message for new chat
    addMessage("Hello! I'm your Lotus Electronics assistant. How can I help you today?", false);
    
    console.log('🆕 New chat started with session:', sessionId);
}

async function sendToBot(userMessage) {
    showTypingIndicator();

    try {
    const response = await fetch(`${window.location.protocol}//${window.location.hostname}:8001/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message: userMessage,
                session_id: sessionId
            })
        });

        const data = await response.json();
        hideTypingIndicator();

        // Reset retry count on successful response
        resetRetryCount();


        if (data?.status === "success" && data.data) {
            const botData = data.data;

            // Always show the main answer text if available
            if (botData.answer) {
                addMessage(botData.answer, false);
            }

            // Show comparison table if available
            console.log("🔧 Checking comparison conditions:");
            console.log("🔧 botData.comparison exists:", !!botData.comparison);
            console.log("🔧 botData.products exists:", !!botData.products);
            console.log("🔧 products length:", botData.products?.length);
            console.log("🔧 comparison.products exists:", !!botData.comparison?.products);
            console.log("🔧 comparison.products length:", botData.comparison?.products?.length);
            console.log("🔧 table is array:", Array.isArray(botData.comparison?.table));
            console.log("🔧 table length:", botData.comparison?.table?.length);
            
            // Check if comparison data is available - either in botData.products or botData.comparison.products
            const hasComparisonProducts = (botData.products && botData.products.length > 1) || 
                                        (botData.comparison?.products && botData.comparison.products.length > 1);
            
            // More flexible comparison detection - allow even single product comparisons if table data exists
            const hasValidComparison = botData.comparison && 
                                     Array.isArray(botData.comparison.table) && 
                                     botData.comparison.table.length > 0 &&
                                     ((botData.comparison.products && botData.comparison.products.length > 0) ||
                                      (botData.products && botData.products.length > 0));
            
            if (hasValidComparison) {
                console.log("🔧 Valid comparison detected, rendering table");
                try {
                    // Use products from comparison object if available, otherwise from botData.products
                    const productsToUse = botData.comparison.products || botData.products;
                    
                    // Ensure we have products and table data
                    if (!productsToUse || productsToUse.length === 0) {
                        console.error("🔧 No products found for comparison");
                        addMessage("⚠️ Comparison data is incomplete - no products found.", false);
                        return;
                    }
                    
                    if (!botData.comparison.table || botData.comparison.table.length === 0) {
                        console.error("🔧 No table data found for comparison");
                        addMessage("⚠️ Comparison data is incomplete - no comparison table found.", false);
                        return;
                    }
                    
                    const comparisonWithProducts = {
                        ...botData.comparison,
                        products: productsToUse
                    };
                    
                    console.log("🔧 Rendering comparison with products:", productsToUse.length, "table rows:", botData.comparison.table.length);
                    renderComparisonTable(comparisonWithProducts);
                } catch (comparisonError) {
                    console.error("Error rendering comparison table:", comparisonError);
                    addMessage("⚠️ Product comparison is available but couldn't be displayed properly. Error: " + comparisonError.message, false);
                }
            } else {
                console.log("🔧 Comparison conditions not met, skipping table rendering");
                console.log("🔧 hasComparisonProducts:", hasComparisonProducts);
                console.log("🔧 hasValidComparison:", hasValidComparison);
                
                // Provide helpful feedback if comparison was expected but failed
                if (botData.comparison && (!Array.isArray(botData.comparison.table) || botData.comparison.table.length === 0)) {
                    console.log("🔧 Comparison object exists but table data is missing or invalid");
                }
            }

            // Show products in carousel if available
            if (Array.isArray(botData.products) && botData.products.length > 0) {
                renderProductsCarousel(botData.products);
            }
            // Show store info if available
            if (Array.isArray(botData.stores) && botData.stores.length > 0) {
                botData.stores.forEach(store => {
                    renderStoreCard(store);
                });
            }

            // Show detailed single product card if available
            if (botData.product_details && botData.product_details.product_id) {
                try {
                    renderProductDetailsCard(botData.product_details);
                } catch (detailsError) {
                    console.error("Error rendering product details:", detailsError);
                    addMessage("Product details are available but couldn't be displayed properly.", false);
                }
            }

            // Show follow-up / end message
            if (botData.end) {
                addMessage(botData.end, false);
            }

        } else {
            addMessage("Sorry, I couldn’t process your request. Please try again.", false);
        }
    } catch (error) {
        hideTypingIndicator();
        console.error("Error in sendToBot:", error);
        
        // Handle different types of errors
        let errorMessage = "Sorry, something went wrong. ";
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage += "Please check your internet connection and try again.";
        } else if (error.message.includes('timeout')) {
            errorMessage += "The request timed out. Please try again.";
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage += "Unable to connect to the server. Please try again.";
        } else {
            errorMessage += "Please try again in a moment.";
        }
        
        addMessage(errorMessage, false);
        
        // Show retry button
        showRetryButton(userMessage);
    }
}

// Show retry button for failed requests
function showRetryButton(lastMessage) {
    const retryDiv = document.createElement('div');
    retryDiv.className = 'retry-container';
    retryDiv.innerHTML = `
        <button class="retry-btn" onclick="retryLastMessage('${lastMessage.replace(/'/g, "\\'")}')">
            <i class="fas fa-redo"></i> Retry
        </button>
    `;
    
    const chatBody = document.getElementById('chat-body');
    chatBody.appendChild(retryDiv);
    scrollToBottom();
}

// Global variables for retry functionality
let retryCount = 0;
let maxRetries = 3;

// Retry the last message with exponential backoff
async function retryLastMessage(message) {
    if (retryCount >= maxRetries) {
        addMessage("Maximum retry attempts reached. Please try again later.", false);
        return;
    }
    
    retryCount++;
    
    // Remove existing retry buttons
    const retryContainers = document.querySelectorAll('.retry-container');
    retryContainers.forEach(container => container.remove());
    
    // Calculate delay with exponential backoff (1s, 2s, 4s)
    const delay = Math.pow(2, retryCount - 1) * 1000;
    
    addMessage(`Retrying in ${delay/1000} second${delay > 1000 ? 's' : ''}...`, false);
    
    setTimeout(() => {
        sendToBot(message);
    }, delay);
}

// Reset retry count on successful response
function resetRetryCount() {
    retryCount = 0;
}

// Render product comparison table
function renderComparisonTable(comparison) {
    console.log("🔧 renderComparisonTable called with:", comparison);
    
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'comparison-table-wrapper';

    const heading = document.createElement('h3');
    heading.textContent = 'Product Comparison';
    tableWrapper.appendChild(heading);

    const table = document.createElement('table');
    table.className = 'comparison-table';

    // Table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const featureTh = document.createElement('th');
    featureTh.textContent = 'Feature';
    headerRow.appendChild(featureTh);
    
    // Create mapping for product keys - map table keys to products
    const productKeyMap = new Map();
    comparison.products.forEach((product, index) => {
        const fullName = product.product_name || product.product_id;
        
        // Find the corresponding key in the table data
        if (comparison.table && comparison.table.length > 0) {
            const sampleRow = comparison.table[0];
            const tableKeys = Object.keys(sampleRow).filter(key => key !== 'feature');
            
            // Try multiple matching strategies
            let matchedKey = null;
            
            // Strategy 1: Exact match
            matchedKey = tableKeys.find(key => key === fullName);
            
            // Strategy 2: Table key is prefix of full name
            if (!matchedKey) {
                matchedKey = tableKeys.find(key => fullName.startsWith(key));
            }
            
            // Strategy 3: Full name is prefix of table key (less common)
            if (!matchedKey) {
                matchedKey = tableKeys.find(key => key.startsWith(fullName));
            }
            
            // Strategy 4: Contains product ID
            if (!matchedKey && product.product_id) {
                matchedKey = tableKeys.find(key => key.includes(product.product_id));
            }
            
            // Strategy 5: Fuzzy matching - find key with most words in common
            if (!matchedKey) {
                const fullNameWords = fullName.toLowerCase().split(/\s+|,/);
                let bestMatch = null;
                let bestScore = 0;
                
                tableKeys.forEach(key => {
                    const keyWords = key.toLowerCase().split(/\s+|,/);
                    const commonWords = fullNameWords.filter(word => 
                        keyWords.some(keyWord => keyWord.includes(word) || word.includes(keyWord))
                    );
                    const score = commonWords.length / Math.max(fullNameWords.length, keyWords.length);
                    
                    if (score > bestScore && score > 0.3) { // At least 30% similarity
                        bestScore = score;
                        bestMatch = key;
                    }
                });
                
                if (bestMatch) {
                    matchedKey = bestMatch;
                    console.log(`🔧 Fuzzy match found: "${fullName}" -> "${bestMatch}" (score: ${bestScore.toFixed(2)})`);
                }
            }
            
            // Strategy 6: Fallback - use table key by position
            if (!matchedKey && index < tableKeys.length) {
                matchedKey = tableKeys[index];
                console.log(`🔧 Position-based fallback: product ${index} -> key "${matchedKey}"`);
            }
            
            productKeyMap.set(product, matchedKey);
            console.log(`🔧 Final mapping: "${fullName.substring(0, 50)}..." -> table key: "${matchedKey}"`);
        }
    });
    
    // Add product names as columns
    comparison.products.forEach((product, index) => {
        const th = document.createElement('th');
        const productName = product.product_name || product.product_id;
        const shortName = productName.length > 40 ? 
            productName.substring(0, 40) + '...' : 
            productName;
        th.textContent = shortName;
        th.title = productName; // Full name in tooltip
        headerRow.appendChild(th);
        console.log(`🔧 Header ${index}: ${shortName}`);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Table body
    const tbody = document.createElement('tbody');
    comparison.table.forEach((row, rowIndex) => {
        console.log(`🔧 Processing row ${rowIndex}:`, row);
        const tr = document.createElement('tr');
        const featureTd = document.createElement('td');
        featureTd.textContent = row.feature;
        tr.appendChild(featureTd);
        
        comparison.products.forEach((product, colIndex) => {
            const td = document.createElement('td');
            const tableKey = productKeyMap.get(product);
            const value = tableKey ? (row[tableKey] || '-') : '-';
            td.textContent = value;
            tr.appendChild(td);
            console.log(`🔧 Row ${rowIndex}, Col ${colIndex}: tableKey="${tableKey}" value="${value}"`);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    tableWrapper.appendChild(table);
    chatMessages.appendChild(tableWrapper);
    scrollToBottom();
    
    console.log("🔧 Comparison table rendered successfully");
}

function renderProductsCarousel(products) {
    const carouselWrapper = document.createElement('div');
    carouselWrapper.className = "carousel-wrapper";

    const carousel = document.createElement('div');
    carousel.className = "carousel-container";

    products.forEach(product => {
        const card = document.createElement('div');
        card.className = "product-card";

        card.innerHTML = `
            <a href="${product.product_url}" target="_blank">
                <img src="${product.product_image}" alt="${product.product_name}" class="product-img"/>
            </a>
            <div class="product-info">
                <div class="product-name">${product.product_name}</div>
                <div class="product-price">${product.product_mrp}</div>
                <div class="product-features">
                    ${product.features.map(f => `<span class="feature">${f}</span>`).join(" ")}
                </div>
            </div>
        `;

        carousel.appendChild(card);
    });

    // Navigation buttons
    const prevBtn = document.createElement('button');
    prevBtn.className = "carousel-btn prev-btn";
    prevBtn.innerHTML = "&#10094;";
    prevBtn.onclick = () => {
        carousel.scrollBy({ left: -carousel.offsetWidth, behavior: 'smooth' });
    };

    const nextBtn = document.createElement('button');
    nextBtn.className = "carousel-btn next-btn";
    nextBtn.innerHTML = "&#10095;";
    nextBtn.onclick = () => {
        carousel.scrollBy({ left: carousel.offsetWidth, behavior: 'smooth' });
    };

    carouselWrapper.appendChild(prevBtn);
    carouselWrapper.appendChild(carousel);
    carouselWrapper.appendChild(nextBtn);

    chatMessages.appendChild(carouselWrapper);
    scrollToBottom();

    // 🔥 Auto-slide every 3 seconds
    setInterval(() => {
        carousel.scrollBy({ left: carousel.offsetWidth, behavior: 'smooth' });
        // if reached end, reset to start
        if (carousel.scrollLeft + carousel.offsetWidth >= carousel.scrollWidth) {
            setTimeout(() => carousel.scrollTo({ left: 0, behavior: 'smooth' }), 1000);
        }
    }, 3000);
}


// Render detailed product card
// Render detailed product card
function renderProductDetailsCard(product) {
    const card = document.createElement('div');
    card.className = "product-details-card";

    // Handle specifications array properly
    let specificationsHtml = '';
    if (product.specifications && Array.isArray(product.specifications)) {
        specificationsHtml = product.specifications.map(spec => {
            if (typeof spec === 'object') {
                // Handle specification objects like {"Processor": "Ultra 9"}
                const key = Object.keys(spec)[0];
                const value = spec[key];
                return `<li><strong>${key}:</strong> ${value}</li>`;
            } else {
                // Handle simple string specifications
                return `<li>✔ ${spec}</li>`;
            }
        }).join("");
    } else if (product.features && Array.isArray(product.features)) {
        // Fallback to features if specifications not available
        specificationsHtml = product.features.map(f => `<li>✔ ${f}</li>`).join("");
    }

    card.innerHTML = `
        <div class="details-card-content">
            <div class="details-left">
                <img src="${product.product_image}" alt="${product.product_name}" class="details-img"/>
                
            </div>
            <div class="details-right">
                <h3 class="details-name">${product.product_name}</h3>
                <p class="details-price"><strong>${product.product_mrp}</strong></p>
                <div class="details-actions">
                    <a href="${product.product_url}" target="_blank" class="details-btn">View Product</a>
                    <button class="add-to-cart-btn">Add to Cart</button>
                </div>
            </div>
        </div>
        ${specificationsHtml ? `
        <div class="details-specifications">
            <h4>Specifications:</h4>
            <ul class="details-features">
                ${specificationsHtml}
            </ul>
        </div>` : ''}
    `;

    chatMessages.appendChild(card);
    scrollToBottom();
}

// Render store card
function renderStoreCard(store) {
    const card = document.createElement('div');
    card.className = "store-card";

    const encodedAddress = encodeURIComponent(`Lotus Electronics ${store.address}`);

    card.innerHTML = `
        <h3 class="store-name">${store.name || store.store_name || 'Lotus Electronics Store'}</h3>
        <p class="store-address">${store.address}</p>
        <p class="store-timings"><strong>Timings:</strong> ${store.timings}</p>
        <a 
            href="https://www.google.com/maps/search/?api=1&query=${encodedAddress}" 
            target="_blank" 
            class="direction-btn">
            📍 Get Directions
        </a>
    `;

    chatMessages.appendChild(card);
    scrollToBottom();
}

// Event Listeners
searchForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const message = searchInput.value.trim();
    if (message) {
        openChat(message);
        searchInput.value = '';
    }
});

chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (message) {
        addMessage(message, true);
        chatInput.value = '';
        sendToBot(message);
    }
});

closeChatBtn.addEventListener('click', function () {
    closeChat();
});

// Add event listener for new chat button
const newChatBtn = document.getElementById('newChatBtn');
if (newChatBtn) {
    newChatBtn.addEventListener('click', function () {
        newChat();
    });
}

// Add event listeners for voice controls
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && chatOverlay.style.display === 'flex') {
        closeChat();
    }
});

// Initialize speech recognition when page loads - COMMENTED OUT FOR NEXT PHASE
document.addEventListener('DOMContentLoaded', function() {
    // Restore chat history from storage on page load
    const chatRestored = loadChatFromStorage();
    if (chatRestored) {
        // If chat was restored, show the chat overlay instead of landing page
        chatOverlay.style.display = 'flex';
        landingPage.style.display = 'none';
        chatInput.focus();
    } else {
        // No chat to restore, show landing page
        searchInput.focus();
    }

});

