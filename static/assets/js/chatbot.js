
function toggleChatbot() {
    const chatbotWindow = document.getElementById("chatbotWindow");

    if (chatbotWindow.style.display === "none" || chatbotWindow.style.display === "") {
        chatbotWindow.style.display = "flex";
    } else {
        chatbotWindow.style.display = "none";
    }
}


function closeChatbot() {
    document.getElementById("chatbotWindow").style.display = "none";
}


async function sendMessage() {

    const input = document.getElementById("chatInput");
    const message = input.value.trim();

    if (!message) {
        return;
    }

    const chatMessages = document.getElementById("chatMessages");

    chatMessages.innerHTML += `
        <div class="user-message">
            ${message}
        </div>
    `;

    input.value = "";

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {

        const response = await fetch("/chatbot", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        // Show bot response
        chatMessages.innerHTML += `
            <div class="bot-message">
                ${data.response}
            </div>
        `;

        // Show matching items
        if (data.items && data.items.length > 0) {

            data.items.forEach(item => {

                chatMessages.innerHTML += `
                    <div class="chat-item">

                        <strong>${item.title}</strong>

                        <div>
                            ₹${item.price}
                        </div>

                        <small>
                            ${item.category} • ${item.item_condition}
                        </small>

                    </div>
                `;

            });
        }

    } catch (error) {

        console.error("Chatbot error:", error);

        chatMessages.innerHTML += `
            <div class="bot-message">
                Something went wrong. Please try again.
            </div>
        `;
    }

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// Press Enter to send message
document.addEventListener("DOMContentLoaded", function () {

    const input = document.getElementById("chatInput");

    if (input) {

        input.addEventListener("keydown", function (event) {

            if (event.key === "Enter") {
                event.preventDefault();
                sendMessage();
            }

        });

    }

});
