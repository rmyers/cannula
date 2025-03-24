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
 * Handles API error responses by adding error classes and messages to form elements
 * @param {Object} errorResponse - The error response object from the API
 */
function handleFormErrors(errorResponse) {
  // Check if there are errors to process
  if (!errorResponse || !errorResponse.errors) {
    console.error("Invalid error response format");
    return;
  }

  // Reset any existing errors first (optional)
  clearExistingErrors();

  // Process each form's errors
  Object.keys(errorResponse.errors).forEach((formKey) => {
    const formErrors = errorResponse.errors[formKey];

    // Process each error for this form
    formErrors.forEach((error) => {
      if (!error.field || !error.message) {
        console.warn("Invalid error format:", error);
        return;
      }

      // Find the input element
      // For a field name like "input.password", we need to look for an input with name="input.password"
      // No need to escape the dot since we're looking for the literal string including the dot
      const fieldName = error.field;
      const inputElement = document.querySelector(`[name="${fieldName}"]`);

      if (!inputElement) {
        // Handle missing fields or general form errors by adding to the form itself
        console.warn(`Input element with name "${error.field}" not found. Adding error to form.`);

        // Find the form element
        const formElement = document.querySelector(
          `form[name="${formKey}"], form#${formKey}, form[data-form-id="${formKey}"]`,
        );
        if (!formElement) {
          // If we can't find the form, look for a div with the form's ID
          const formContainer = document.getElementById(formKey);
          if (!formContainer) {
            console.error(`Neither form nor container for "${formKey}" found`);
            return;
          }

          // Add the error to the form container
          addErrorToElement(formContainer, error.message);
          return;
        }

        // Add the error to the form
        addErrorToElement(formElement, error.message);
        return;
      }

      // Find the parent div of the input
      const parentDiv = inputElement.closest("div");
      if (!parentDiv) {
        console.warn(`Parent div for input "${error.field}" not found. Adding error next to input.`);
        // If we can't find a parent div, add the error right after the input
        addErrorToElement(inputElement.parentElement || inputElement, error.message);
        return;
      }

      // Add error to the parent div
      addErrorToElement(parentDiv, error.message);
    });
  });
}

/**
 * Adds an error message to an element
 * @param {HTMLElement} element - The element to add the error to
 * @param {string} message - The error message
 */
function addErrorToElement(element, message) {
  // Add invalid class to the element
  element.classList.add("invalid");

  // Hide helper text if it exists
  const helperSpan = element.querySelector("span.helper");
  if (helperSpan) {
    // Add a data attribute to mark it was hidden by the error handler
    helperSpan.dataset.hiddenByError = "true";
    helperSpan.style.display = "none";
  }

  // Check if an error span already exists to avoid duplicates
  let errorSpan = element.querySelector("span.error");

  if (!errorSpan) {
    // Create error message span only if it doesn't exist yet
    errorSpan = document.createElement("span");
    errorSpan.className = "error";
    element.appendChild(errorSpan);
  }

  // Update the error message
  errorSpan.textContent = message;
}

/**
 * Clear all existing error messages and classes
 */
function clearExistingErrors() {
  // Remove all invalid classes from divs
  document.querySelectorAll("div.invalid").forEach((div) => {
    div.classList.remove("invalid");
  });

  // Remove all error message spans
  document.querySelectorAll("span.error").forEach((span) => {
    span.remove();
  });

  // Restore any hidden helper texts
  document.querySelectorAll('span.helper[data-hidden-by-error="true"]').forEach((helperSpan) => {
    helperSpan.style.display = "";
    delete helperSpan.dataset.hiddenByError;
  });
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
        // Add all the params to the request
        const params = new URLSearchParams(document.location.search);
        for (const [key, value] of params.entries()) {
          evt.detail.parameters[key] = value;
        }
      }

      if (name === "htmx:beforeRequest") {
        clearExistingErrors();
      }

      if (name === "htmx:beforeSwap") {
        const xhr = evt.detail.xhr;

        // Check if this is a JSON response
        if (xhr.getResponseHeader("Content-Type")?.includes("application/json")) {
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

              if (response.extensions && response.extensions.errors) {
                handleFormErrors(response.extensions);
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
window.GraphQLToast = {handleGraphQLResponse, makeToast};
