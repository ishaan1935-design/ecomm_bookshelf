////console.log("Sanity check!");
// ============================================================
// 1. ROBUST FETCH HELPER WITH EXPONENTIAL BACKOFF RETRY
// ============================================================
async function fetchWithRetry(url, options = {}, retries = 3, baseDelay = 1000) {
  for (let attempt = 1; attempt <= retries; attempt++) {

      const response = await fetch(url, {
        ...options,
        credentials: 'same-origin', // ✅ Critical: sends CSRF cookie
      });
      // Retry on server errors (5xx) and rate limiting (429)
      if (response.status >= 500 || response.status === 429) {
        if (attempt === retries) {
          throw new Error(`Server error ${response.status} after ${retries} attempts`);
        }
        const delay = baseDelay * Math.pow(2, attempt - 1);
        console.warn(`Attempt ${attempt} failed (${response.status}). Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      // Don't retry on 4xx client errors (bad request, forbidden, etc.)
      return response;

      // Network-level failures (offline, DNS, etc.)
      if (attempt === retries) {
        throw new Error(`Network error after ${retries} attempts: ${err.message}`);
      }
      const delay = baseDelay * Math.pow(2, attempt - 1);
      console.warn(`Network error on attempt ${attempt}. Retrying in ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));

  }
}
// ============================================================
// 2. SAFE JSON PARSER (handles HTML error pages)
// ============================================================
async function safeJson(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    const text = await response.text();
    throw new Error(
      `Expected JSON but got ${contentType}. ` +
      `Server returned: ${text.substring(0, 200)}... ` +
      `Check that your Django view returns JsonResponse.`
    );
  }
  return response.json();
}

// ============================================================
// 3. MAIN APPLICATION INITIALIZATION
// ============================================================
(async function initCheckout(event) {
  const submitBtn = document.querySelector('#submitBtn');
  const payButton = document.querySelector('#payButton'); // your Stripe button

if (!navigator.onLine) {
    alert("You appear to be offline. Please check your connection.");
    return;
  }
  // --- Disable button until everything is ready ---
  submitBtn.disabled = true;
  submitBtn.textContent = 'Loading...';

  try {
    // Step A: Fetch Stripe public key with retry
    const configResponse = await fetchWithRetry('/config/');
    if (!configResponse.ok) {
      throw new Error(`Config fetch failed: ${configResponse.status}`);
    }
    const configData = await safeJson(configResponse);

    if (!configData.publicKey || typeof configData.publicKey !== 'string') {
      throw new Error('Invalid or missing Stripe publicKey in /config/ response.');
    }

    // Step B: Initialize Stripe.js with error handling
   if (typeof Stripe === 'undefined' || !window.stripeInstance) {
      await initStripe();
    }

    // ... input validation and CSRF extraction ...

    // Generate a unique idempotency key for this specific checkout attempt
    const idempotencyKey = crypto.randomUUID();
    const stripe = Stripe(configData.publicKey);

    // Step C: Now the button is safe to enable
    submitBtn.disabled = false;
    submitBtn.textContent = 'Pay with Stripe';
    console.log('✅ Stripe initialized successfully.');

    // ============================================================
    // 4. ATTACH EVENT LISTENER AFTER EVERYTHING IS READY
    // ============================================================
    submitBtn.addEventListener('click', async () => {
      // Prevent double-clicks
      if (submitBtn.disabled) return;
      submitBtn.disabled = true;
      submitBtn.textContent = 'Processing...';

      try {
        // --- Read form values ---
        const address = document.getElementById('address')?.value?.trim();
        const city = document.getElementById('city')?.value?.trim();
        const state = document.getElementById('state')?.value?.trim();
        const zipcode = document.getElementById('zipcode')?.value?.trim();

        // --- Validate inputs ---
        if (!address || !city || !state || !zipcode) {
          throw new Error('Please fill in all shipping fields.');
        }

        // --- Get CSRF token safely ---
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput) {
          throw new Error('CSRF token not found. Ensure {% csrf_token %} is in your form.');
        }
        const csrftoken = csrfInput.value;

        // --- Create Stripe checkout session with retry ---
        const sessionResponse = await fetchWithRetry('/create-checkout-session/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'Idempotency-Key': idempotencyKey // Prevents duplicate sessions on retry
          },
          body: JSON.stringify({ address, city, state, zipcode }),
        });

        if (!sessionResponse.ok) {
          // Try to extract a meaningful error from the server
          let serverMsg = `Server responded with ${sessionResponse.status}`;
          try {
            const errData = await safeJson(sessionResponse);
            if (errData.error) serverMsg = errData.error;
          } catch (_) { /* ignore parse errors */ }
          throw new Error(serverMsg);
        }

        const sessionData = await safeJson(sessionResponse);

        if (sessionData.error) {
          throw new Error(sessionData.error);
        }
        if (!sessionData.sessionId) {
          throw new Error('Session ID missing from server response.');
        }

        // --- Redirect to Stripe Checkout ---
        // This is where most intermittent failures happen — Stripe.js
        // may fail to load, or the redirect may be blocked.
        const result = await stripe.redirectToCheckout({
          sessionId: sessionData.sessionId,
        });
        if (result?.error) {
          throw new Error(`Stripe redirect failed: ${result.error.message}`);
        }

      } catch (err) {
        console.error('❌ Checkout error:', err);

        // User-friendly message
        const userMessage = err.message.includes('Stripe.js')
          ? 'Payment system failed to load. Please refresh the page and try again.'
          : err.message.includes('CSRF')
          ? 'Security token expired. Please refresh the page and try again.'
          : 'Something went wrong with your order. Please try again.';

        alert(userMessage);

        // Re-enable button so user can retry
        submitBtn.disabled = false;
        submitBtn.textContent = 'Pay with Stripe';
      }
    });

  } catch (initErr) {
    console.error('❌ Failed to initialize checkout:', initErr);
    alert(
      'Unable to initialize payment system. ' +
      'Please check your internet connection and refresh the page.'
    );
    submitBtn.disabled = false;
    submitBtn.textContent = 'Retry';
  }
})();

async function initStripe() {
 const configResponse = await fetchWithRetry('/config/');
 const configData = await safeJson(configResponse);
  // Dynamically load Stripe.js if it failed on initial page load
 if (typeof Stripe === 'undefined') {
 await new Promise((resolve, reject) => {
 const script = document.createElement('script');
 script.src = 'https://js.stripe.com/v3/';
 script.onload = resolve;
script.onerror = () => reject(new Error('Failed to load Stripe.js'));
document.head.appendChild(script); }); }
window.stripeInstance = Stripe(configData.publicKey); }
// 4. Attempt initial background load
initStripe().catch(console.warn);
//fetch("/config/")
//  .then(result => result.json())
//  .then(data => {
//    // Stripe.js लाइब्रेरी जो हमने HTML में ऐड की है, उसका इस्तेमाल
//    const stripe = Stripe(data.publicKey);
//
//    document.querySelector("#submitBtn").addEventListener("click", () => {
//      const address = document.getElementById("address").value;
//      const city = document.getElementById("city").value;
//      const state = document.getElementById("state").value;
//      const zipcode = document.getElementById("zipcode").value;
//
//      // सीधा HTML पेज से CSRF Token लेना (Foolproof method)
//      const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
//
//      fetch("/create-checkout-session/", {
//        method: "POST",
//        headers: {
//            "Content-Type": "application/json",
//            "X-CSRFToken": csrftoken, // <-- यहाँ सीधा टोकन पास हो रहा है
//        },
//        body: JSON.stringify({ address, city, state, zipcode }),
//      })
//      .then(response => {
//        // अगर Django 500/403 Error Page (HTML) भेजता है, तो उसे यहीं पकड़ लेंगे
//        if (!response.ok) {
//           throw new Error("Server Error: JSON की जगह HTML आ रहा है। कृपया अपना views.py चेक करें।");
//        }
//        return response.json();
//      })
//      .then(data => {
//        if (data.error) {
//          alert(data.error);
//          return;
//        }
//        if(!data.sessionId) {
//          alert("Session ID missing!");
//          return;
//        }
//        // Redirect to Stripe
//        return stripe.redirectToCheckout({ sessionId: data.sessionId });
//      })
//      .catch(err => {
//        console.error("Error:", err);
//        alert("Something went wrong! Check the browser console.");
//      });
//    });
//  })
//  .catch(err => {
//    console.error("Config fetch error:", err);
//  });