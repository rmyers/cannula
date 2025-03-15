// graphql-error-toast.js

/**
 * Creates and displays toast notifications for GraphQL errors or success messages
 * @param {Object} response - The GraphQL response object with data, errors, and extensions properties
 * @param {number} [duration=4000] - How long the toast should stay visible (ms)
 * @returns {Object} - The data portion of the response
 */
function handleGraphQLResponse(response, duration = 4000) {
  // Check if there are errors to display
  if (response.errors && response.errors.length > 0) {
    // Display each error as a separate toast
    response.errors.forEach((error) => {
      makeToast("error", error.message || "An error occurred", duration);
    });
  } else if (response.extensions && response.extensions.successMessage) {
    // Display success message if provided in extensions
    makeToast("success", response.extensions.successMessage, duration);
  }

  // Return the data part of the response
  return response.data;
}

/**
 * Creates and displays a toast notification
 * @param {string} type - Either "success" or "error"
 * @param {string} message - The message to display
 * @param {number} [duration=4000] - How long the toast should stay visible (ms)
 */
function makeToast(type, message, duration = 60000) {
  // Create an element and make it into a popover
  const toast = document.createElement("article");
  toast.popover = "manual";
  toast.classList.add("toast", "newest", "rounded");

  // Add appropriate class based on type
  if (type === "success") {
    toast.classList.add("success");
  } else if (type === "error") {
    toast.classList.add("error");
  } else {
    return;
  }

  // Add icon based on type
  const icon = document.createElement("i");
  icon.classList.add("toast-icon");

  if (type === "success") {
    icon.innerHTML = `check`;
  } else {
    icon.innerHTML = "error";
  }

  toast.appendChild(icon);

  // Add text message
  const text = document.createElement("span");
  text.textContent = message;
  toast.appendChild(text);

  // Add close button
  const closeBtn = document.createElement("button");
  closeBtn.classList.add("transparent", "circle");

  closeBtn.innerHTML = `<i>close</i>`;

  closeBtn.addEventListener("click", () => {
    toast.hidePopover();
    toast.remove();
  });

  toast.appendChild(closeBtn);

  // Add to the DOM
  document.body.appendChild(toast);

  // Show the popover
  toast.showPopover();

  // Move existing toasts up before showing this one
  moveToastsUp();

  // Remove the toast after specified duration
  setTimeout(() => {
    // Check if toast still exists in the DOM
    if (document.body.contains(toast)) {
      toast.hidePopover();
      toast.remove();
    }
  }, duration);
}

/**
 * Moves existing toasts up to make room for a new one
 */
function moveToastsUp() {
  const toasts = document.querySelectorAll(".toast");
  const spaceBetweenToasts = 10; // Margin between toasts in pixels
  let cumulativeHeight = 0;

  // Convert NodeList to Array and reverse to start from the bottom
  // This way we process toasts from bottom to top
  Array.from(toasts)
    .reverse()
    .forEach((toast, index) => {
      if (toast.classList.contains("newest")) {
        // Position the newest toast at the base position
        toast.style.bottom = "20px";
        toast.style.right = "20px";
        toast.classList.remove("newest");

        // Start cumulative height with this toast's height
        cumulativeHeight = toast.scrollHeight + spaceBetweenToasts;
      } else {
        // Position this toast above the previous ones
        toast.style.bottom = `${20 + cumulativeHeight}px`;
        toast.style.right = "20px";

        // Add this toast's height to the cumulative height
        cumulativeHeight += toast.scrollHeight + spaceBetweenToasts;
      }
    });
}

// Add necessary CSS
function injectStyles() {
  if (document.getElementById("graphql-toast-styles")) return;

  const styleElement = document.createElement("style");
  styleElement.id = "graphql-toast-styles";
  styleElement.textContent = `
      .toast {
        position: fixed;
        bottom: 20px;
        right: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
        max-width: 500px;
        z-index: 9999;
        transition: transform 0.3s ease, opacity 0.3s ease;
      }

      .toast-icon {
        margin-right: 10px;
      }

      .toast.success {
        border: 1px solid #10B981;
      }

      .toast.error {
        border: 1px solid #EF4444;
      }

      :popover-open {
        position: absolute;
        inset: unset;
        right: 10px;
        bottom: 10px;
      }

      /* Responsive adjustments for mobile devices */
      @media (max-width: 600px) {
        .toast {
          right: 10px;
          bottom: 10px;
          min-width: auto;
          max-width: none;
          width: calc(100% - 20px);
        }
      }
    `;

  document.head.appendChild(styleElement);
}

/**
 * Add necessary HTMX extension for GraphQL response handling
 */
function addHtmxExtension() {
  // Only add if HTMX is available
  if (typeof htmx === "undefined") {
    console.warn("HTMX not found, GraphQL extension not loaded");
    return;
  }

  // Register the HTMX extension
  htmx.defineExtension("graphql-toast", {
    onEvent: function (name, evt) {
      // Handle JSON responses for HTMX requests
      if (name === "htmx:configRequest") {
        evt.detail.headers["Accept"] = "application/json";
      }

      if (name === "htmx:beforeSwap") {
        const xhr = evt.detail.xhr;

        // Check if this is a JSON response
        if (
          xhr.getResponseHeader("Content-Type")?.includes("application/json")
        ) {
          try {
            // Parse JSON response
            const response = JSON.parse(xhr.responseText);

            // Check if this looks like a GraphQL response (has data or errors)
            if (response && (response.data !== undefined || response.errors)) {
              // Handle the GraphQL response notifications
              handleGraphQLResponse(response);

              // Check if there's HTML in the extensions
              if (response.extensions && response.extensions.html) {
                // Use the HTML from extensions for the swap
                evt.detail.serverResponse = response.extensions.html;
              } else if (!response.data && response.errors) {
                // If there's an error but no HTML or data, prevent the swap
                evt.detail.shouldSwap = false;
                return true;
              }
            }
          } catch (e) {
            console.error("Error processing JSON response:", e);
          }
        }
      }
    },
  });
}

// Auto-initialize when the DOM is ready
function initialize() {
  // Inject styles
  injectStyles();

  // Add HTMX extension if HTMX is available
  if (document.readyState !== "loading") {
    addHtmxExtension();
  } else {
    document.addEventListener("DOMContentLoaded", addHtmxExtension);
  }
}

// Execute initialization when the script loads
initialize();

// Export public API
window.GraphQLToast = {
  handleGraphQLResponse,
  makeToast,
};
