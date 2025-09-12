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
        const savedMessages = localStorage.getItem('lotus-chat-history');
        const savedSession = localStorage.getItem('lotus-chat-session');
        
        if (savedMessages && savedSession) {
            const messages = JSON.parse(savedMessages);
            sessionId = savedSession; // Restore the session ID
            
            // Clear current chat
            chatMessages.innerHTML = '';
            
            // Restore messages
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
                console.log('📥 Chat restored from storage:', messages.length, 'messages');
                return true; // Indicate that chat was restored
            }
        }
        return false; // No chat to restore
    } catch (error) {
        console.error('❌ Error loading chat from storage:', error);
        return false;
    }
}

function clearChatStorage() {
    try {
        localStorage.removeItem('lotus-chat-history');
        localStorage.removeItem('lotus-chat-session');
        console.log('🗑️ Chat storage cleared');
    } catch (error) {
        console.error('❌ Error clearing chat storage:', error);
    }
}

// Speech recognition and synthesis variables - COMMENTED OUT FOR NEXT PHASE
// let recognition = null;
// let isListening = false;
// let speechSynthesis = window.speechSynthesis;
// let currentUtterance = null;
// let isMuted = false; // Add mute state tracking
// let isSpeaking = false; // Add speaking state tracking
// let autoSpeak = true; // Voice assistant mode - auto speak bot responses
// let lastClickTime = 0; // Debounce clicking
// let lastSpokenMessage = ''; // Track last spoken message to avoid duplicates
// let speechQueue = []; // Queue for speech messages
// let selectedVoice = null; // Store the selected voice to keep it consistent

// Initialize and select a consistent voice - COMMENTED OUT FOR NEXT PHASE
/*
function initializeVoice() {
    const voices = speechSynthesis.getVoices();
    console.log('🔊 Initializing voice from', voices.length, 'available voices');
    
    if (voices.length > 0 && !selectedVoice) {
        // Try to find Microsoft Zira (English US female voice) first
        selectedVoice = voices.find(voice => 
            voice.name.toLowerCase().includes('zira')
        );
        
        // If no Zira, try other female voices
        if (!selectedVoice) {
            selectedVoice = voices.find(voice => 
                voice.name.toLowerCase().includes('female') || 
                voice.name.toLowerCase().includes('hazel') ||
                voice.name.toLowerCase().includes('sarah')
            );
        }
        
        // If no female voice, try any English voice
        if (!selectedVoice) {
            selectedVoice = voices.find(voice => 
                voice.lang.includes('en') || voice.lang.includes('EN')
            );
        }
        
        // If still no voice, use the first available voice
        if (!selectedVoice && voices.length > 0) {
            selectedVoice = voices[0];
        }
        
        if (selectedVoice) {
            console.log('🔊 Selected consistent voice:', selectedVoice.name, selectedVoice.lang);
        }
    }
}
*/

// Initialize speech recognition - COMMENTED OUT FOR NEXT PHASE
/*
function initializeSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onstart = function() {
            isListening = true;
            updateMicButton();
            
            // When mic starts, mute the speaker to avoid feedback
            if (!isMuted) {
                console.log('🎤 Microphone started - auto-muting speaker');
                toggleMute();
            }
            
            console.log('🎤 Speech recognition started');
        };
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            console.log('🗣️ Recognized:', transcript);
            
            // Add the recognized text to chat
            addMessage(transcript, true);
            sendToBot(transcript);
        };
        
        recognition.onerror = function(event) {
            console.error('🚫 Speech recognition error:', event.error);
            isListening = false;
            updateMicButton();
            
            // When mic has error, unmute the speaker
            if (isMuted) {
                console.log('🎤 Microphone error - auto-unmuting speaker');
                setTimeout(() => {
                    toggleMute();
                }, 200);
            }
            
            if (event.error === 'not-allowed') {
                addMessage("⚠️ Microphone access denied. Please allow microphone access to use voice chat.", false);
            } else if (event.error === 'no-speech') {
                addMessage("🔇 No speech detected. Please try again.", false);
            }
        };
        
        recognition.onend = function() {
            isListening = false;
            updateMicButton();
            
            // When mic stops, unmute the speaker
            if (isMuted) {
                console.log('🎤 Microphone stopped - auto-unmuting speaker');
                setTimeout(() => {
                    toggleMute(); // Small delay to avoid conflicts
                }, 200);
            }
            
            console.log('🎤 Speech recognition ended');
        };
    } else {
        console.warn('Speech recognition not supported in this browser');
    }
}
*/

// Text-to-speech function - COMMENTED OUT FOR NEXT PHASE
/*
function speakText(text) {
    console.log('🔊 speakText called with:', text);
    console.log('🔊 isMuted:', isMuted);
    console.log('🔊 isSpeaking:', isSpeaking);
    console.log('🔊 speechSynthesis available:', !!speechSynthesis);
    
    // Don't speak if muted or already speaking
    if (isMuted) {
        console.log('🔇 Speech blocked - speaker is muted');
        return;
    }
    
    if (isSpeaking) {
        console.log('🔇 Speech blocked - already speaking');
        return;
    }
    
    // Clean text for better speech
    const cleanText = text.replace(/[📱💰🏷️✔️📦📍🎯🔍]/g, '').replace(/₹/g, 'rupees ').trim();
    console.log('🔊 Clean text:', cleanText);
    
    if (!cleanText) {
        console.log('🔇 No text to speak');
        return;
    }
    
    // Set speaking flag
    isSpeaking = true;
    
    // Stop any ongoing speech with a small delay to avoid interruption
    if (speechSynthesis.speaking) {
        console.log('🔊 Stopping current speech');
        speechSynthesis.cancel();
        // Wait a moment before starting new speech
        setTimeout(() => startSpeech(cleanText), 100);
    } else {
        startSpeech(cleanText);
    }
}
*/

// Ensure consistent voice is set - COMMENTED OUT FOR NEXT PHASE
/*
function ensureVoiceSet(utterance) {
    if (!selectedVoice) {
        initializeVoice();
    }
    
    if (selectedVoice) {
        utterance.voice = selectedVoice;
        console.log('🔊 Voice ensured:', selectedVoice.name);
    } else {
        console.warn('🔇 No voice available to set');
    }
}

function startSpeech(text) {
    console.log('🔊 Starting speech for:', text);
    
    // Create utterance
    currentUtterance = new SpeechSynthesisUtterance(text);
    currentUtterance.rate = 0.9;
    currentUtterance.pitch = 1;
    currentUtterance.volume = 1;
    
    // Ensure consistent voice is set
    ensureVoiceSet(currentUtterance);
    
    // Set up event handlers
    currentUtterance.onstart = function() {
        console.log('🔊 Speech started successfully');
        isSpeaking = true;
        updateSpeakerButton(true);
    };
    
    currentUtterance.onend = function() {
        console.log('🔇 Speech finished');
        isSpeaking = false;
        updateSpeakerButton(false);
        
        // Process next item in queue if available - only if not muted
        if (speechQueue.length > 0 && !isMuted) {
            setTimeout(() => processVoiceQueue(), 500);
        } else if (isMuted) {
            console.log('🔇 Queue processing stopped - speaker is muted');
            speechQueue = []; // Clear queue if muted
        }
    };
    
    currentUtterance.onerror = function(event) {
        console.error('🔇 Speech error:', event.error, event);
        isSpeaking = false;
        updateSpeakerButton(false);
        
        // Try again with a simpler approach if interrupted - BUT ONLY IF NOT MUTED
        if (event.error === 'interrupted' && !isMuted) {
            console.log('🔊 Retrying speech after interruption...');
            setTimeout(() => {
                // Double-check mute state before retry
                if (isMuted) {
                    console.log('🔇 Retry cancelled - speaker is muted');
                    return;
                }
                
                const retryUtterance = new SpeechSynthesisUtterance(text);
                retryUtterance.rate = 1;
                retryUtterance.pitch = 1;
                retryUtterance.volume = 1;
                
                // Ensure consistent voice for retry
                ensureVoiceSet(retryUtterance);
                
                retryUtterance.onend = function() {
                    isSpeaking = false;
                    updateSpeakerButton(false);
                    // Process queue after retry - only if not muted
                    if (speechQueue.length > 0 && !isMuted) {
                        setTimeout(() => processVoiceQueue(), 500);
                    }
                };
                
                retryUtterance.onerror = function(retryEvent) {
                    console.error('🔇 Retry speech error:', retryEvent.error);
                    isSpeaking = false;
                    updateSpeakerButton(false);
                    // Process next item in queue if available - only if not muted
                    if (speechQueue.length > 0 && !isMuted) {
                        setTimeout(() => processVoiceQueue(), 500);
                    }
                };
                
                speechSynthesis.speak(retryUtterance);
            }, 500);
        } else {
            console.log('🔇 No retry - either not interrupted or speaker is muted');
            // Process next item in queue if available - only if not muted
            if (speechQueue.length > 0 && !isMuted) {
                setTimeout(() => processVoiceQueue(), 500);
            }
        }
    };
    
    // Start speaking with a small delay to avoid interruption
    console.log('🔊 Starting speech synthesis...');
    setTimeout(() => {
        try {
            speechSynthesis.speak(currentUtterance);
            console.log('🔊 speechSynthesis.speak() called successfully');
        } catch (error) {
            console.error('🔇 Error calling speechSynthesis.speak():', error);
        }
    }, 50);
}
*/

// Start/stop speech recognition - COMMENTED OUT FOR NEXT PHASE
/*
function toggleSpeechRecognition() {
    // Debounce rapid clicks
    const now = Date.now();
    if (now - lastClickTime < 500) {
        console.log('🎤 Click debounced');
        return;
    }
    lastClickTime = now;
    
    if (!recognition) {
        addMessage("⚠️ Speech recognition is not supported in your browser.", false);
        return;
    }
    
    console.log('🎤 toggleSpeechRecognition called, isListening:', isListening);
    
    if (isListening) {
        console.log('🎤 Stopping speech recognition');
        recognition.stop();
        // isListening will be set to false in the onend event
    } else {
        console.log('🎤 Starting speech recognition');
        try {
            recognition.start();
            // isListening will be set to true in the onstart event
        } catch (error) {
            console.error('🎤 Error starting recognition:', error);
            isListening = false;
            updateMicButton();
        }
    }
}
*/

// Update microphone button appearance - COMMENTED OUT FOR NEXT PHASE
/*
function updateMicButton() {
    const micBtn = document.getElementById('micButton');
    if (micBtn) {
        if (isListening) {
            micBtn.classList.add('listening');
            micBtn.innerHTML = '<i class="fas fa-stop"></i>';
            micBtn.title = 'Stop listening';
        } else {
            micBtn.classList.remove('listening');
            micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            micBtn.title = 'Start voice input';
        }
    }
}

// Update speaker button appearance
function updateSpeakerButton(isSpeaking) {
    const speakerBtn = document.getElementById('speakerButton');
    if (speakerBtn) {
        if (isMuted) {
            speakerBtn.classList.add('muted');
            speakerBtn.classList.remove('speaking');
            speakerBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
            speakerBtn.title = 'Speaker OFF - Click to turn ON';
        } else if (isSpeaking) {
            speakerBtn.classList.add('speaking');
            speakerBtn.classList.remove('muted');
            speakerBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
            speakerBtn.title = 'Speaking... Click to turn OFF';
        } else {
            speakerBtn.classList.remove('speaking', 'muted');
            speakerBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
            speakerBtn.title = 'Speaker ON - Click to turn OFF';
        }
    }
}

// Stop text-to-speech
function stopSpeaking() {
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
    }
    isSpeaking = false;
    updateSpeakerButton(false);
}

// Toggle mute/unmute functionality
function toggleMute() {
    isMuted = !isMuted;
    
    if (isMuted) {
        // Mute: Stop ALL speech activities
        console.log('🔇 MUTING: Stopping all speech activities');
        
        // Cancel any current speech
        if (speechSynthesis.speaking) {
            speechSynthesis.cancel();
        }
        
        // Clear the speech queue completely
        speechQueue = [];
        
        // Reset speaking state
        isSpeaking = false;
        
        // Disable auto-speak
        autoSpeak = false;
        
        console.log('🔇 Voice Assistant FULLY muted - all speech stopped, queue cleared');
    } else {
        // Unmute: Enable auto-speak only
        autoSpeak = true;
        console.log('🔊 Voice Assistant unmuted - auto-speak enabled');
    }
    
    updateSpeakerButton(false);
}

// Toggle text-to-speech (for speaker button clicks)
function toggleTextToSpeech() {
    // Debounce rapid clicks
    const now = Date.now();
    if (now - lastClickTime < 300) {
        console.log('🔊 Click debounced');
        return;
    }
    lastClickTime = now;
    
    console.log('🔊 toggleTextToSpeech called');
    console.log('🔊 Current state - isMuted:', isMuted, 'isSpeaking:', isSpeaking);
    
    // Simple toggle: If muted, unmute. If unmuted, mute.
    if (isMuted) {
        // Unmute the speaker
        console.log('🔊 Unmuting speaker');
        toggleMute();
    } else {
        // Mute the speaker
        console.log('� Muting speaker');
        toggleMute();
    }
}

// Process voice queue to avoid multiple simultaneous speech
function processVoiceQueue() {
    // Don't process queue if muted
    if (isMuted) {
        console.log('🔇 Queue processing blocked - speaker is muted');
        speechQueue = []; // Clear queue when muted
        return;
    }
    
    if (speechQueue.length > 0 && !isSpeaking && !isMuted) {
        const nextMessage = speechQueue.shift(); // Get and remove first message
        console.log('🎤 Processing voice queue:', nextMessage.substring(0, 50) + '...');
        speakText(nextMessage);
        
        // Process next message after current one finishes
        const checkComplete = setInterval(() => {
            if (!isSpeaking || isMuted) {
                clearInterval(checkComplete);
                if (speechQueue.length > 0 && !isMuted) {
                    setTimeout(() => processVoiceQueue(), 500); // Small gap between messages
                }
            }
        }, 100);
    }
}
*/

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
    
    // Voice Assistant Mode: Auto-speak bot messages (with duplicate detection) - COMMENTED OUT FOR NEXT PHASE
    /*
    if (!isUser && content && autoSpeak && !isMuted && speechSynthesis) {
        // Clean content for comparison
        const cleanContent = content.replace(/[📱💰🏷️✔️📦📍🎯🔍]/g, '').replace(/₹/g, 'rupees ').trim();
        
        // Only speak if it's different from the last spoken message
        if (cleanContent !== lastSpokenMessage) {
            console.log('🎤 Voice Assistant: Auto-speaking new bot response');
            lastSpokenMessage = cleanContent;
            
            // Add to speech queue instead of speaking immediately
            speechQueue.push(cleanContent);
            
            // Process queue if not already speaking
            if (!isSpeaking) {
                setTimeout(() => {
                    processVoiceQueue();
                }, 800); // Small delay to let the message appear first
            }
        } else {
            console.log('🔇 Voice Assistant: Skipping duplicate message');
        }
    }
    */
    
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

    } catch (error) {
        hideTypingIndicator();
        addMessage("⚠ Connection error. Please try again later.", false);
        console.error("Chat API Error:", error);
    }
}

// Render product carousel
// function renderProductsCarousel(products) {
//     const carouselWrapper = document.createElement('div');
//     carouselWrapper.className = "carousel-wrapper";

//     const carousel = document.createElement('div');
//     carousel.className = "carousel-container";

//     products.forEach(product => {
//         const card = document.createElement('div');
//         card.className = "product-card";

//         card.innerHTML = `
//             <a href="${product.product_url}" target="_blank">
//                 <img src="${product.product_image}" alt="${product.product_name}" class="product-img"/>
//             </a>
//             <div class="product-info">
//                 <div class="product-name">${product.product_name}</div>
//                 <div class="product-price">${product.product_mrp}</div>
//                 <div class="product-features">
//                     ${product.features.map(f => `<span class="feature">${f}</span>`).join(" ")}
//                 </div>
//             </div>
//         `;

//         carousel.appendChild(card);
//     });

//     // Add navigation buttons
//     const prevBtn = document.createElement('button');
//     prevBtn.className = "carousel-btn prev-btn";
//     prevBtn.innerHTML = "&#10094;"; // left arrow
//     prevBtn.onclick = () => {
//         carousel.scrollBy({
//             left: -250,
//             behavior: 'smooth'
//         });
//     };

//     const nextBtn = document.createElement('button');
//     nextBtn.className = "carousel-btn next-btn";
//     nextBtn.innerHTML = "&#10095;"; // right arrow
//     nextBtn.onclick = () => {
//         carousel.scrollBy({
//             left: 250,
//             behavior: 'smooth'
//         });
//     };

//     carouselWrapper.appendChild(prevBtn);
//     carouselWrapper.appendChild(carousel);
//     carouselWrapper.appendChild(nextBtn);

//     chatMessages.appendChild(carouselWrapper);
//     scrollToBottom();
// }

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
    
    // Speech and voice functionality commented out for next phase
    /*
    initializeSpeechRecognition();
    
    // Initialize voice selection
    initializeVoice();
    
    // Load voices for text-to-speech and initialize when they're loaded
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = function() {
            console.log('🔊 Voices loaded:', speechSynthesis.getVoices().length);
            // Initialize voice selection when voices are loaded
            initializeVoice();
        };
    }
    
    // Add event listeners for voice control buttons
    const micButton = document.getElementById('micButton');
    const speakerButton = document.getElementById('speakerButton');
    
    console.log('🔊 Setting up voice controls');
    console.log('🔊 micButton found:', !!micButton);
    console.log('🔊 speakerButton found:', !!speakerButton);
    
    if (micButton) {
        micButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('🎤 Mic button clicked');
            toggleSpeechRecognition();
        });
    }
    
    if (speakerButton) {
        speakerButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('🔊 Speaker button clicked');
            toggleTextToSpeech();
        });
    }
    */
});

// searchInput.focus(); // Commented out - focus is now handled in DOMContentLoaded based on chat restore
